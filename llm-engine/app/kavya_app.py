from fastapi import FastAPI, HTTPException
from langserve import add_routes
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from ServiceManager import ServiceManager
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.chains import create_sql_query_chain
from langchain.chains import SequentialChain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.llm import LLMChain
from langchain.chains.base import Chain
from langchain.llms.base import LLM
import gnupg
import argparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_sql_query_chain
from langchain.chat_models import ChatOpenAI
import redis
from datetime import datetime

SENSITIVE_PATH = "sensitive/openai.txt"

service_manager = ServiceManager()


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


def run_chain(question):
    # Initialize the LLMManager and database
    db = service_manager.get_db()
    llm = service_manager.get_llm()

    # Step 1: Define the SQL generation chain
    sql_generation_chain = create_sql_query_chain(llm=llm, db=db)
    
    # Step 2: Initialize the guidance chain
   # guidance_chain = GuidancePromptChain(llm=llm)

    # Step 3: Initialize the SQL execution chain
   # sql_execution_chain = SQLExecutionChain(db=db, llm=llm, guidance_chain=guidance_chain)
#
    # Step 4: Combine chains into a SequentialChain
    # final_chain = SequentialChain(
    #     chains=[sql_generation_chain, sql_execution_chain],
    #     input_variables=["question"],
    #     output_variables=["response", "error", "guidance_response"],
    # )
    final_chain = sql_generation_chain
    # Run the chain
    result = final_chain.invoke({"question": question})
    return result

def handle_query(question):
    try:
        result = run_chain(question)
        return result
    except Exception as e:
        print(e)
        return None

def main():
    parser = argparse.ArgumentParser(description="Select question.")
    parser.add_argument(
        "number",
        type=int,
        default=0
    )
    questions = [
        "Get median and mean household income aggregated for each year.",
        "For each area in New York, give count of each crime type.",
        "Give me number of employees who are male",
        "Retrieve all records from the economic_income_and_benefits table where the mean_household_income is more than 100,000 and the crime classification (Crime_Class) is 'Felony'."
    ]
    args = parser.parse_args()
    print(handle_query(questions[args.number]))
    
if __name__ == "__main__":
    main()
