import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Contrag API")

# Mount static frontend
app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/")
def root():
    return FileResponse("web/index.html")
