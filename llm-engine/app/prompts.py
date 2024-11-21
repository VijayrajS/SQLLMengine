from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

## Prompts to create SQL query
# This is the first prompt with all table schema, 3 rows of every table information
CREATE_SQL_QUERY_MESSAGE = "You are a MySQL expert. Given an input question, create a syntactically correct SQL query to run. Unless otherwise specified, do not return more than {top_k} rows.\n\nHere is the relevant table info: {table_info}."
# For upcoming chat, where table info is already present in the history
CONTINUATION_PROMPT = "Generate ONLY the SQL query based on user's question and history. If the question is unclear, try your best to create SQL query."
RESPONSE_FORMAT = " IMPORTANT: Respond ONLY with the complete SQL query, without any additional text or explanation."
# Failure message when LLM is unable to generate the SQL query
FAILURE_MESSAGE_FORMAT = " If you could not generate a SQL query, give the reason in at most 50 words."

# Chat prompt template for a new chat
INITIAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CREATE_SQL_QUERY_MESSAGE + RESPONSE_FORMAT + FAILURE_MESSAGE_FORMAT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

# Chat prompt tenplate for a continuation chat
CONTINUATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CONTINUATION_PROMPT + RESPONSE_FORMAT + FAILURE_MESSAGE_FORMAT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])
