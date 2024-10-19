from fastapi import FastAPI, HTTPException
from langserve import add_routes
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from db import DatabaseConnection
from llm import LLMConnection
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain.chains import create_sql_query_chain

from db import DatabaseConnection
from llm import LLMConnection

import gnupg

# GPG_BINARY_PATH = "/opt/homebrew/bin/gpg"
SENSITIVE_PATH = "sensitive/openai.txt"

# gpg = gnupg.GPG(binary=GPG_BINARY_PATH)

app = FastAPI()
llm = None
db = None

db_conn = DatabaseConnection()
db = db_conn.db
llm_conn = LLMConnection()
llm = llm_conn.llm
    
@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

# Edit this to add the chain you want to add
# add_routes(app, NotImplemented)

def pre_start():
    db_conn = DatabaseConnection()
    db = db_conn.db
    llm_conn = LLMConnection()
    llm = llm_conn.llm
    return llm, db
    
    
def run_chain(question):
    # Setup LangChain tools
    print(db)
    execute_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm, db)
    
    # Combine the write and execute steps
    chain = write_query | execute_query
    
    # Invoke the chain and capture the response
    response = chain.invoke({"question": question})
    
    # Capture the query generated from the question (you can extract this from the write_query tool)
    generated_query = write_query.llm_chain.run(question)
    
    # Return both the generated query and the response
    return {
        "query": generated_query,
        "response": response
    }


# Define the request body model using Pydantic
class QueryRequest(BaseModel):
    question: str
    
# Define the POST request handler for sending the prompt
@app.post("/query")
async def handle_query(query_request: QueryRequest):
    # Extract the question from the request body
    question = query_request.question

    if not question:
        raise HTTPException(status_code=400, detail="No question provided")

    # Invoke the chain with the question
    try:
        result = run_chain(question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    llm, db = pre_start()
    print(db)
    uvicorn.run(app, host="0.0.0.0", port=8000)
