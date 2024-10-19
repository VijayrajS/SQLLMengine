"""
Module to connect with LLM.
"""
import os
from langchain_openai import ChatOpenAI
from util import read_gpg_encrypted_file

OPEN_AI_SENSITIVE_PATH = "sensitive/openai.txt"
class LLMConnection():
    """
    Initialize OPEN AI LLM connection with file_path where key is stored.
    """
    def __init__(self, file_path = OPEN_AI_SENSITIVE_PATH):
        self.set_key(file_path)
        self.llm = ChatOpenAI(model="gpt-3.5-turbo")
        
    def set_key(self, file_path):
        self.open_ai_key = read_gpg_encrypted_file(file_path)
        os.environ["OPENAI_API_KEY"] = self.open_ai_key
