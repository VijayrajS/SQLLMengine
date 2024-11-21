from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from ServiceManager import ServiceManager
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.base import Chain
import gnupg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables.base import RunnableLambda
from constants import *
from prompts import *

# GPG_BINARY_PATH = "/opt/homebrew/bin/gpg"
SENSITIVE_PATH = "sensitive/openai.txt"

# gpg = gnupg.GPG(binary=GPG_BINARY_PATH)

app = FastAPI()

# Initialize the service manager
service_manager = ServiceManager()
redis_client = service_manager.get_redis()
redis_client = redis_client.redis

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


class ChatMessage(BaseModel):
    session_id: str
    message: str
    message_type: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    sql_query: Optional[str]
    query_result: Optional[str]
    history: List[dict]


class GuidancePromptChain(Chain):
    """
    A separate chain to generate user-friendly guidance in case of failures.
    """
    def __init__(self, llm, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm

    @property
    def input_keys(self):
        return ["sql_query", "error_message"]

    @property
    def output_keys(self):
        return ["guidance_response"]

    def _call(self, inputs):
        sql_query = inputs["sql_query"]
        error_message = inputs["error_message"]

        # Chat Prompt Template for guidance
        prompt = ChatPromptTemplate.from_messages(
            [{"role": "system", "content": "You are an assistant providing clear guidance for database-related issues."},
             {"role": "user", "content": (
                f"The query '{sql_query}' failed with the error: '{error_message}'. "
                "Please provide user-friendly guidance including:"
                "\n1. Checking for typos in the table name."
                "\n2. Verifying if the table exists in the database and if they have access to it."
                "\n3. Consulting a database administrator for missing tables or access issues."
            )}]
        )

        guidance_response = self.llm.invoke(prompt, sql_query=sql_query, error_message=error_message)
        return {"guidance_response": guidance_response}


class SQLExecutionChain(Chain):
    """
    Chain to handle SQL execution and feedback.
    """
    def __init__(self, db, llm, guidance_chain, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.llm = llm
        self.guidance_chain = guidance_chain
        self.query_tool = QuerySQLDataBaseTool(db=self.db)

    @property
    def input_keys(self):
        return ["sql_query", "original_question"]

    @property
    def output_keys(self):
        return ["response", "error", "guidance_response"]

    def _call(self, inputs):
        print("entered sql execution chain")
        sql_query = inputs["sql_query"]
        original_question = inputs["original_question"]
        error_message = ""

        # Try executing the query up to 3 times
        for attempt in range(3):
            try:
                response = self.query_tool.invoke({"query": sql_query})
                print("did not fail - response")
                print(response)
                return {"response": response, "error": None, "guidance_response": None}
            except Exception as e:
                error_message = str(e)
                print(f"Attempt {attempt + 1}: Error encountered: {error_message}")

                # Update SQL query with error feedback
                feedback_prompt = ChatPromptTemplate.from_messages(
                    [{"role": "system", "content": "You are a SQL query refinement assistant."},
                     {"role": "user", "content": (
                        f"The query '{sql_query}' failed with the error: '{error_message}'. "
                        f"Refine the SQL query for the following question: '{original_question}'."
                    )}]
                )
                sql_query = self.llm.invoke(prompt=feedback_prompt, sql_query=sql_query, error_message=error_message, original_question=original_question)

        # If all attempts fail, use the guidance chain
        guidance_result = self.guidance_chain.run({"sql_query": sql_query, "error_message": error_message})
        print("guidance_result")
        print(type(guidance_result))
        print(guidance_result)
        return {"response": None, "error": error_message, "guidance_response": guidance_result["guidance_response"]}

def run_sql_chain(question: str, history: List[dict], session_id: str, memory: ConversationBufferMemory):
    """Run the SQL generation chain with conversation history"""
    # Initialize the LLMManager and database
    db = service_manager.get_db()
    llm = service_manager.get_llm()
    
    # TODO implement just the relavant tables information if needed
    # this might totally remove the below separation format
    table_info = db.get_table_info()
 
    # Prepare messages for the prompt
    messages = []
    if not history:
        # For initial prompt (no history)
        initial_prompt_value = INITIAL_PROMPT.invoke({
            "table_info": table_info,
            "top_k": TOP_K_ROWS  
        })
        continuation_prompt_value = CONTINUATION_PROMPT.invoke({
            "question": question,
            "history": []
        })
        messages.extend(initial_prompt_value.messages)
        messages.extend(continuation_prompt_value.messages)
    else:
        # For continuation prompt (with history)
        continuation_prompt_value = CONTINUATION_PROMPT.invoke({
            "question": question,
            "history": history
        })
        messages.extend(continuation_prompt_value.messages)

    # Ensure all messages are of type BaseMessage with correct types
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            msg_type = msg.get("type", "human")  # Default to "human" if type is missing
            content = msg.get("content", "")

            if msg_type == "system":
                formatted_messages.append(SystemMessage(content=content))
            elif msg_type == "human":
                formatted_messages.append(HumanMessage(content=content))
        elif isinstance(msg, BaseMessage):
            # If already a BaseMessage, add directly
            formatted_messages.append(msg)
        else:
            raise ValueError(f"Unexpected message format: {msg}")

    # Create the SQL generation chain
    sql_generation_chain = (
        RunnableLambda(lambda x: x)  # Pass messages directly
        | llm
    )

    # Invoke the chain
    result = sql_generation_chain.invoke(formatted_messages)

    # update redis and history
    for msg in messages:
        print(len(messages))
        # Check message type
        message_type = ""
        message = ""
        if isinstance(msg, SystemMessage):
            message_type="system",
            message = msg.content
        elif isinstance(msg, HumanMessage):
            message_type="human",
            message = msg.content
        elif isinstance(msg, AIMessage):
            message_type="ai",
            message = msg.content
        elif isinstance(msg, MessagesPlaceholder):
            continue
        if message_type and message:
           update_chat_memory_and_redis_history(session_id, message, 
                                                message_type, memory)

    memory = update_chat_memory_and_redis_history(session_id, result.content, 
                                                  "ai", memory)
    return result, memory
    

# Define the request body model using Pydantic
class ChatRequest(BaseModel):
    session_id: int
    message: str
    message_type: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    sql_query: Optional[str]
    sql_valid: bool
    query_result: Optional[str]

def get_message_history(session_id: str) -> ConversationBufferMemory:
    """Retrieve chat history for a session from Redis cache"""
    print("inside getting message history")
    memory = ConversationBufferMemory(
        memory_key="history",
        return_messages=True
    )
    print("created memory object")
    cached_messages = redis_client.lrange(f"chat:{session_id}", 0, -1)
    print("cached_messages fetched")
    if cached_messages:
        print("cached messages exist")
        for msg in cached_messages:
            msg = json.loads(msg)
            print("printing msg", msg)
            if msg['type'] == 'human':
                memory.chat_memory.add_message(HumanMessage(content=msg['content']))
            elif msg['type'] == 'ai':
                memory.chat_memory.add_message(AIMessage(content=msg['content']))
            elif msg['type'] == 'system':
                memory.chat_memory.add_message(SystemMessage(content=msg['content']))
    print("memory fetched")
    return memory


def update_chat_memory_and_redis_history(session_id: str, message_content:str, message_type:str, 
                                         memory: ConversationBufferMemory) -> ConversationBufferMemory:
    """Save updated chat history to Redis cache and memory object"""
    # Update cache
    message = {
        "type": message_type,
        "content": message_content
    }
    # Convert the message to a JSON string
    message_json = json.dumps(message)
    # Append the message to the list associated with the session ID
    # rpush takes care if the session_id does not exist
    redis_client.rpush(f"chat:{session_id}", message_json)
    # Update the TTL for the session ID
    redis_client.expire(session_id, CHAT_HISTORY_TTL)
    print(f"Message appended to session {session_id} and TTL updated to {CHAT_HISTORY_TTL} seconds")

    # Update conversation buffer memory
    if message_type == 'human':
        memory.chat_memory.add_message(HumanMessage(content=message_content))
    elif message_type == 'ai':
        memory.chat_memory.add_message(AIMessage(content=message_content))
    elif message_type == 'system':
        memory.chat_memory.add_message(SystemMessage(content=message_content))
    print(f"Updated memory with latest message")
    return memory


# Define the POST request handler for sending the prompt
# remove chat response
# @app.post("/query", response_model=ChatResponse)
@app.post("/query")
async def handle_query(request: Request):
    json_data = await request.json()
    chat_request = ChatRequest(
        session_id=json_data["session_id"],
        message=json_data["question"],
        message_type=json_data["message_type"]
    )
    if not chat_request.message:
        raise HTTPException(status_code=400, detail="No question provided")
    
    memory = get_message_history(chat_request.session_id)
    print("got memory")
    print(memory)
    # Invoke the chain with the question
    try:
        result, memory = run_sql_chain(
            chat_request.message,
            memory.load_memory_variables({})["history"],
            chat_request.session_id,
            memory
        )
        return result
    except Exception as e:
        print(e)
        print("chain failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
