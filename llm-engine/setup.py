from setuptools import setup, find_packages

setup(
    name="llm_engine",
    version="0.1",
    packages=find_packages(),
        install_requires=[
        "langchain",
        "openai"
    ],
)