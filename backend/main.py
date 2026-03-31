import sys, os, re, json as _json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from langchain_ollama import ChatOllama

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

# ── Diff Risk Analysis ────────────────────────────────────────────────────────

_RISK_SYSTEM = (
    "You are a legal risk analyst. Review the contract changes below and classify "
    "each change block.\n\n"
    "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON.\n\n"
    "Format:\n"
    '{{"summary": "<2-3 sentence executive summary>", '
    '"changes": [{{"index": 0, "risk": "<level>", "explanation": "<brief reason>"}}]}}\n\n'
    "Risk levels:\n"
    "  risk_increase — adds obligations, tightens deadlines, removes protections\n"
    "  risk_decrease — removes obligations, extends timelines, adds protections\n"
    "  neutral       — formatting, typos, clarifications, no material impact\n"
)

def _group_change_blocks(hunks: list) -> list:
    """Group consecutive non-context hunks into change blocks."""
    blocks, buf = [], []
    for h in hunks:
        if h["type"] == "context":
            if buf:
                blocks.append(buf)
                buf = []
        else:
            buf.append(h)
    if buf:
        blocks.append(buf)
    return blocks

def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
    return _json.loads(text.strip())

@app.post("/api/diff/risk")
def diff_risk(body: dict):
    hunks = body.get("hunks")
    if not hunks:
        raise HTTPException(400, "hunks is required")
    name_a = body.get("name_a", "Base")
    name_b = body.get("name_b", "Compare")

    blocks = _group_change_blocks(hunks)

    if not blocks:
        return {"summary": "The contracts are identical.", "changes": []}

    changes_text = ""
    for i, block in enumerate(blocks):
        removed_lines = [h["text"] for h in block if h["type"] == "removed"]
        added_lines   = [h["text"] for h in block if h["type"] == "added"]
        changes_text += f"[Change {i}]\n"
        if removed_lines:
            changes_text += f"  REMOVED: {' '.join(removed_lines)}\n"
        if added_lines:
            changes_text += f"  ADDED:   {' '.join(added_lines)}\n"
        changes_text += "\n"

    prompt = (
        f'{_RISK_SYSTEM}\n'
        f'Changes between "{name_a}" (base) and "{name_b}" (compare):\n\n'
        f'{changes_text}'
    )

    llm = ChatOllama(model="llama3.2", temperature=0)
    result = llm.invoke(prompt)
    try:
        data = _extract_json(result.content)
    except Exception:
        raise HTTPException(500, f"LLM returned invalid JSON: {result.content[:200]}")

    if "summary" not in data or "changes" not in data:
        raise HTTPException(500, "LLM response missing required fields")

    return data

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
    sources = body.get("sources") or None  # [] treated as None → full index
    if sources is not None and not isinstance(sources, list):
        raise HTTPException(400, "sources must be a list of filenames")

    def generate():
        try:
            from chain import ask_stream
            for chunk in ask_stream(question, sources=sources):
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
        except FileNotFoundError as e:
            yield f"data: ERROR:{str(e)}\n\n"
        except Exception as e:
            yield f"data: ERROR:{str(e)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/chat/context")
async def get_context(body: dict):
    question = body.get("question", "")
    if not question.strip():
        raise HTTPException(400, "Question is required")
    sources = body.get("sources") or None
    if sources is not None and not isinstance(sources, list):
        raise HTTPException(400, "sources must be a list of filenames")
    from retriever import get_retriever
    retriever = get_retriever(sources=sources)
    docs = retriever.invoke(question)
    return [{"source": d.metadata.get("source", "unknown"), "text": d.page_content} for d in docs]

# ── Static frontend ───────────────────────────────────────────────────────────

app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/")
def root():
    return FileResponse("web/index.html")
