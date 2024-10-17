from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes

import getpass
import os
import gnupg

GPG_BINARY_PATH = "/opt/homebrew/bin/gpg"
SENSITIVE_PATH = "sensitive/openai.txt"

gpg = gnupg.GPG(binary=GPG_BINARY_PATH)


def read_gpg_encrypted_file(file_path):
    with open(file_path, 'r') as fp:
        key = fp.read() #! TODO: this should be encrypted
        os.environ["OPENAI_API_KEY"] = key

def pre_start():
    read_gpg_encrypted_file(sensitive_path)
    
app = FastAPI()


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


# Edit this to add the chain you want to add
# add_routes(app, NotImplemented)

if __name__ == "__main__":
    import uvicorn
    pre_start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
