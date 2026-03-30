import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import file_manager
import diff_engine
import glossary_engine

app = FastAPI(title="Contrag API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Files ────────────────────────────────────────────────────────────────────

@app.get("/api/files")
def list_files():
    return file_manager.list_files()

@app.post("/api/files/upload")
async def upload_file(file: UploadFile, background_tasks: BackgroundTasks):
    content = await file.read()
    path = file_manager.save_file(file.filename, content)
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from unstructured.partition.auto import partition
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS

        elements = partition(filename=path)
        full_text = "\n".join([str(e) for e in elements if str(e).strip()])
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n1.", "\n2.", "\nWHEREAS", "\nARTICLE", "\nSECTION", "\n\n", "\n", ". ", " "],
            chunk_size=800, chunk_overlap=100,
        )
        chunks = splitter.create_documents([full_text], metadatas=[{"source": file.filename}])
        store_path = "faiss_index"
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        if os.path.exists(store_path):
            db = FAISS.load_local(store_path, embeddings, allow_dangerous_deserialization=True)
            db.add_documents(chunks)
        else:
            db = FAISS.from_documents(chunks, embeddings)
        db.save_local(store_path)

        chunk_texts = [c.page_content for c in chunks]
        background_tasks.add_task(
            glossary_engine.extract_and_update, path, file.filename, chunk_texts
        )
    except Exception as e:
        file_manager.remove_file(file.filename)
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "filename": file.filename}

@app.delete("/api/files/{filename}")
def delete_file(filename: str):
    file_manager.remove_file(filename)
    return {"ok": True}

# ── Diff ─────────────────────────────────────────────────────────────────────

@app.get("/api/diff")
def get_diff(a: str, b: str):
    path_a = file_manager.get_file_path(a)
    path_b = file_manager.get_file_path(b)
    if not os.path.exists(path_a):
        raise HTTPException(404, f"{a} not found")
    if not os.path.exists(path_b):
        raise HTTPException(404, f"{b} not found")
    hunks = diff_engine.diff_contracts(path_a, path_b, a, b)
    return {"hunks": hunks}

# ── Glossary ──────────────────────────────────────────────────────────────────

@app.get("/api/glossary")
def get_glossary(q: str = ""):
    g = glossary_engine.load_glossary()
    if q:
        q_lower = q.lower()
        g = {k: v for k, v in g.items() if q_lower in k}
    return g

# ── Chat (SSE) ────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(body: dict):
    question = body.get("question", "")
    if not question.strip():
        raise HTTPException(400, "Question is required")

    def generate():
        try:
            from chain import ask_stream
            for chunk in ask_stream(question):
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
        except FileNotFoundError as e:
            yield f"data: ERROR:{str(e)}\n\n"
        except Exception as e:
            yield f"data: ERROR:{str(e)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ── Static frontend ───────────────────────────────────────────────────────────

app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/")
def root():
    return FileResponse("web/index.html")
