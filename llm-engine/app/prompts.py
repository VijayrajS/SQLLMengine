from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# Prompts to create SQL query by passing table_info
CREATE_SQL_QUERY_MESSAGE = "You are a MySQL expert. Given an input question, create a syntactically correct SQL query to run. Unless otherwise specificed, do not return more than {top_k} rows.\n\nHere is the relevant table info: {table_info}."
CONTINUATION_PROMPT = "You are a helpful MySQL expert. Generate ONLY the SQL query based on user's question and history."
RESPONSE_FORMAT = " IMPORTANT: Respond ONLY with the complete SQL query, without any additional text or explanation."
FAILURE_MESSAGE_FORMAT = " If you could not generate a SQL query, give the reason in at most 50 words."
INITIAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CREATE_SQL_QUERY_MESSAGE + RESPONSE_FORMAT + FAILURE_MESSAGE_FORMAT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

CONTINUATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CONTINUATION_PROMPT + RESPONSE_FORMAT + FAILURE_MESSAGE_FORMAT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])
