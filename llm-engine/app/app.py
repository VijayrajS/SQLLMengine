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

# ServiceManager class to handle llm and db connections
class ServiceManager:
    def __init__(self):
        self.db = None
        self.llm = None
        self.initialize_services()

    def initialize_services(self):
        # Initialize database connection
        db_conn = DatabaseConnection()
        self.db = db_conn.db

        # Initialize LLM connection
        llm_conn = LLMConnection()
        self.llm = llm_conn.llm

    def get_db(self):
        if not self.db:
            raise HTTPException(status_code=500, detail="Database connection not initialized.")
        return self.db

    def get_llm(self):
        if not self.llm:
            raise HTTPException(status_code=500, detail="LLM connection not initialized.")
        return self.llm

# Initialize the service manager
service_manager = ServiceManager()

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

# Edit this to add the chain you want to add
# add_routes(app, NotImplemented)
    

def run_chain(question):
    db = service_manager.get_db()
    llm = service_manager.get_llm()
    
    # Generate SQL query from the question
    write_query = create_sql_query_chain(llm, db)
    
    # Execute the generated SQL query
    execute_query = QuerySQLDataBaseTool(db=db)
    error_message = ""
    for attempt in range(3):  # Attempt up to 3 times to get a valid query
        sql_query = write_query.invoke({"question": question})
        try:
            response = execute_query.invoke({"query": sql_query})
           # return {"sql_query": sql_query, "response":  response}
        except Exception as e:
            error_message = str(e)
            print(f"Attempt {attempt + 1}: Error encountered: {error_message}")
            
            # Provide feedback to the LLM to refine the query
            feedback_prompt = (
                f"The query '{sql_query}' failed with the error: '{error_message}'. "
                f"Please provide a corrected SQL query for the following question: '{question}'"
            )
            question = feedback_prompt  # Update question with feedback prompt
    
    #return {"sql_query": sql_query, "response": response, "error":error_message}

    # If all attempts fail, ask LLM to provide user guidance
    guidance_prompt = (
        f"The query '{sql_query}' failed with the error: '{error_message}'. "
        "It appears that the specified table does not exist in the database. "
        "Please provide a response that explains this to the user and suggests potential solutions, such as:"
        "\n1. Checking for typos in the table name."
        "\n2. Verifying if the table exists in the database and if they have access to it."
        "\n3. Creating the table if it is missing or consulting with a database administrator if unsure."
    )
    guidance_response = llm.invoke({"question": guidance_prompt})
    print(guidance_response)
    # Render the final JSON response with guidance if all attempts fail
    # return {
    #         "error": "Failed to generate a valid SQL query after multiple attempts.",
    #         "sql_query": sql_query,
    #         "response": guidance_response
    #         }
    return {"sql_query": sql_query, "response": response, "error":error_message, "guidance_response": guidance_response}
    # return JSONResponse(
    #     status_code=500,
    #     content={
    #         "error": "Failed to generate a valid SQL query after multiple attempts.",
    #         "sql_query": sql_query,
    #         "response": guidance_response
    #     })




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
    uvicorn.run(app, host="0.0.0.0", port=8000)
