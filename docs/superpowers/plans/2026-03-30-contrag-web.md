# Contrag Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit UI with a production-grade dark web application (FastAPI backend + vanilla HTML/CSS/JS frontend) with 4 tabs: Files, Chat, Diff, Glossary — plus a full-screen Lady Justice scales loading overlay.

**Architecture:** FastAPI serves both the REST/SSE API and the static frontend from `web/`. No Node.js or build step needed. All existing Python modules (chain.py, ingest.py, diff_engine.py, glossary_engine.py, file_manager.py) are imported by the backend unchanged. Chat streams via Server-Sent Events. Frontend is vanilla ES-module JS with CSS custom properties.

**Tech Stack:** FastAPI, uvicorn, python-multipart, vanilla HTML5/CSS3/JS ES modules, EB Garamond + Lato (Google Fonts)

**Run command:** `uvicorn backend.main:app --reload --port 8000`

---

## Design System

| Token | Value | Purpose |
|---|---|---|
| `--bg` | `#0f1117` | Page background |
| `--surface` | `#1a1a27` | Cards, panels |
| `--surface-2` | `#22223a` | Elevated elements |
| `--border` | `rgba(255,255,255,0.08)` | Dividers |
| `--gold` | `#c8a850` | Brand accent (Lady Justice) |
| `--gold-dim` | `rgba(200,168,80,0.15)` | Gold tint backgrounds |
| `--text` | `#e8e6df` | Primary text |
| `--text-muted` | `#8a8990` | Secondary text |
| `--green` | `#4a9e4a` | Diff additions |
| `--green-bg` | `#1a3a1a` | Diff addition background |
| `--red` | `#9e4a4a` | Diff removals |
| `--red-bg` | `#3a1a1a` | Diff removal background |
| `--radius` | `8px` | Border radius |
| `--font-head` | `EB Garamond, serif` | Headings |
| `--font-body` | `Lato, sans-serif` | Body text |

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `backend/__init__.py` | Create | Package marker |
| `backend/main.py` | Create | FastAPI app: static files + all API routes |
| `web/index.html` | Create | SPA shell: layout skeleton, tab structure |
| `web/css/design-system.css` | Create | CSS custom properties (tokens above) |
| `web/css/app.css` | Create | Layout, sidebar, tab panels, components |
| `web/css/loader.css` | Create | Full-screen Lady Justice loader overlay |
| `web/js/api.js` | Create | fetch wrappers + SSE helper |
| `web/js/loader.js` | Create | show/hide Lady Justice loader |
| `web/js/tabs/files.js` | Create | Files tab: upload, list, delete |
| `web/js/tabs/chat.js` | Create | Chat tab: SSE streaming, message history |
| `web/js/tabs/diff.js` | Create | Diff tab: contract selector, diff renderer |
| `web/js/tabs/glossary.js` | Create | Glossary tab: search, term cards, sources |
| `web/js/app.js` | Create | Tab routing, init |
| `requirements.txt` | Modify | Add fastapi, uvicorn, python-multipart |

---

## Task 1: Install Dependencies + Backend Skeleton

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/main.py` (skeleton)
- Modify: `requirements.txt`

- [ ] **Step 1: Install FastAPI dependencies**

```bash
cd D:/Workspace/contrag && pip install fastapi uvicorn python-multipart 2>&1 | tail -3
```

Expected: `Successfully installed ...` or `already satisfied`

- [ ] **Step 2: Create `backend/__init__.py`**

```python
```
(empty file)

- [ ] **Step 3: Create `backend/main.py` skeleton**

```python
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
```

- [ ] **Step 4: Verify backend starts**

```bash
cd D:/Workspace/contrag && python -c "from backend.main import app; print('Backend OK')"
```

Expected: `Backend OK`

- [ ] **Step 5: Update requirements.txt**

```
unstructured[pdf]
python-docx
faiss-cpu
langchain
langchain-community
langchain-ollama
langchain-core
langchain-text-splitters
sentence-transformers
streamlit
pytest
fastapi
uvicorn[standard]
python-multipart
```

- [ ] **Step 6: Commit**

```bash
cd D:/Workspace/contrag && git add backend/ requirements.txt && git commit -m "feat: add FastAPI backend skeleton"
```

---

## Task 2: Backend API Routes — Files + Diff + Glossary

**Files:**
- Modify: `backend/main.py` (add routes)

Replace `backend/main.py` with:

```python
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import file_manager
import diff_engine
import glossary_engine
import ingest as ingest_module

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
    # FAISS ingest runs synchronously (fast); glossary runs in background
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
        q = q.lower()
        g = {k: v for k, v in g.items() if q in k}
    return g

# ── Static frontend ───────────────────────────────────────────────────────────

app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/")
def root():
    return FileResponse("web/index.html")
```

- [ ] **Step 1: Write the full `backend/main.py` as above**

- [ ] **Step 2: Verify routes import cleanly**

```bash
cd D:/Workspace/contrag && python -c "from backend.main import app; routes = [r.path for r in app.routes]; print(routes)"
```

Expected output includes: `'/api/files'`, `'/api/diff'`, `'/api/glossary'`, `'/'`

- [ ] **Step 3: Commit**

```bash
cd D:/Workspace/contrag && git add backend/main.py && git commit -m "feat: add file/diff/glossary API routes"
```

---

## Task 3: Backend SSE Chat Endpoint

**Files:**
- Modify: `backend/main.py` (add chat route before the static mount)

Insert this import and route **before** `app.mount(...)` line in `backend/main.py`:

```python
# Add these imports at the top of backend/main.py:
from fastapi.responses import StreamingResponse
import asyncio

# Add this route before app.mount:
@app.post("/api/chat")
async def chat(body: dict):
    question = body.get("question", "")
    if not question.strip():
        raise HTTPException(400, "Question is required")

    def generate():
        try:
            from chain import ask_stream
            for chunk in ask_stream(question):
                # SSE format: "data: <payload>\n\n"
                escaped = chunk.replace("\n", "\\n")
                yield f"data: {escaped}\n\n"
        except FileNotFoundError as e:
            yield f"data: ERROR:{str(e)}\n\n"
        except Exception as e:
            yield f"data: ERROR:{str(e)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 1: Add the imports and chat route to `backend/main.py`**

The final imports section of `backend/main.py` should include:
```python
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
import asyncio
```

And the `/api/chat` route must appear **before** `app.mount(...)`.

- [ ] **Step 2: Verify chat route exists**

```bash
cd D:/Workspace/contrag && python -c "
from backend.main import app
routes = [r.path for r in app.routes]
assert '/api/chat' in routes, f'Missing /api/chat, got: {routes}'
print('Chat route OK')
"
```

Expected: `Chat route OK`

- [ ] **Step 3: Commit**

```bash
cd D:/Workspace/contrag && git add backend/main.py && git commit -m "feat: add SSE streaming chat endpoint"
```

---

## Task 4: HTML Shell + Design System CSS + Loader

**Files:**
- Create: `web/index.html`
- Create: `web/css/design-system.css`
- Create: `web/css/loader.css`
- Create: `web/css/app.css`

- [ ] **Step 1: Create `web/css/design-system.css`**

```css
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&family=Lato:wght@300;400;700&display=swap');

:root {
  --bg:          #0f1117;
  --surface:     #1a1a27;
  --surface-2:   #22223a;
  --border:      rgba(255,255,255,0.08);
  --border-gold: rgba(200,168,80,0.3);
  --gold:        #c8a850;
  --gold-dim:    rgba(200,168,80,0.12);
  --gold-glow:   rgba(200,168,80,0.25);
  --text:        #e8e6df;
  --text-muted:  #8a8990;
  --text-dim:    #5a5960;
  --green:       #4a9e4a;
  --green-bg:    #1a3a1a;
  --red:         #9e4a4a;
  --red-bg:      #3a1a1a;
  --blue:        #5e6ad2;
  --radius:      8px;
  --radius-lg:   14px;
  --font-head:   'EB Garamond', Georgia, serif;
  --font-body:   'Lato', system-ui, sans-serif;
  --transition:  150ms cubic-bezier(0.16,1,0.3,1);
  --shadow:      0 4px 24px rgba(0,0,0,0.4);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { font-size: 16px; color-scheme: dark; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 0.95rem;
  line-height: 1.6;
  min-height: 100dvh;
  overflow-x: hidden;
}

h1,h2,h3,h4 { font-family: var(--font-head); font-weight: 600; line-height: 1.2; }

button {
  font-family: var(--font-body);
  cursor: pointer;
  border: none;
  outline: none;
  transition: var(--transition);
}
button:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }

input, textarea {
  font-family: var(--font-body);
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.6rem 0.9rem;
  font-size: 0.9rem;
  outline: none;
  transition: border-color var(--transition);
}
input:focus, textarea:focus { border-color: var(--gold); }

select {
  font-family: var(--font-body);
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.6rem 0.9rem;
  font-size: 0.9rem;
  cursor: pointer;
  outline: none;
}
select:focus { border-color: var(--gold); }

scrollbar-width: thin;
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

- [ ] **Step 2: Create `web/css/loader.css`**

```css
/* ── Lady Justice Loader ────────────────────────────────────────────── */
#justice-loader {
  position: fixed;
  inset: 0;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2rem;
  z-index: 9999;
  transition: opacity 0.4s ease, visibility 0.4s ease;
}
#justice-loader.hidden {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
}

.justice-brand {
  font-family: var(--font-head);
  font-size: 2.4rem;
  font-weight: 600;
  color: var(--gold);
  letter-spacing: 0.08em;
}

.justice-scales {
  width: 140px;
  height: 140px;
}

/* Pillar and base: static */
.scales-static { /* no animation */ }

/* Beam rocks on pivot at center */
@keyframes beam-rock {
  0%   { transform: rotate(-20deg); }
  50%  { transform: rotate(20deg); }
  100% { transform: rotate(-20deg); }
}
/* Left pan drops when left is heavy */
@keyframes pan-drop-left {
  0%   { transform: translateY(0); }
  50%  { transform: translateY(14px); }
  100% { transform: translateY(0); }
}
/* Right pan rises when left is heavy */
@keyframes pan-rise-right {
  0%   { transform: translateY(0); }
  50%  { transform: translateY(-14px); }
  100% { transform: translateY(0); }
}

.beam-group {
  transform-origin: 70px 42px;
  animation: beam-rock 1.8s ease-in-out infinite;
}
.pan-left  { animation: pan-drop-left  1.8s ease-in-out infinite; }
.pan-right { animation: pan-rise-right 1.8s ease-in-out infinite; }

.justice-label {
  font-family: var(--font-body);
  font-size: 0.8rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text-muted);
}
```

- [ ] **Step 3: Create `web/css/app.css`**

```css
/* ── Layout ─────────────────────────────────────────────────────────── */
#app {
  display: flex;
  height: 100dvh;
  overflow: hidden;
}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
#sidebar {
  width: 220px;
  min-width: 220px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 1.5rem 0;
}

.sidebar-brand {
  padding: 0 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1rem;
}
.sidebar-brand h1 {
  font-size: 1.7rem;
  color: var(--gold);
  letter-spacing: 0.06em;
}
.sidebar-brand span {
  font-family: var(--font-body);
  font-size: 0.72rem;
  color: var(--text-dim);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  display: block;
  margin-top: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 1.25rem;
  color: var(--text-muted);
  font-size: 0.88rem;
  font-weight: 400;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: color var(--transition), background var(--transition), border-color var(--transition);
  background: none;
  width: 100%;
  text-align: left;
}
.nav-item:hover { color: var(--text); background: var(--gold-dim); }
.nav-item.active {
  color: var(--gold);
  border-left-color: var(--gold);
  background: var(--gold-dim);
  font-weight: 700;
}
.nav-item svg { width: 18px; height: 18px; flex-shrink: 0; }

/* ── Main content ────────────────────────────────────────────────────── */
#main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-panel {
  display: none;
  flex: 1;
  overflow-y: auto;
  padding: 2rem 2.5rem;
}
.tab-panel.active { display: flex; flex-direction: column; gap: 1.5rem; }

.panel-title {
  font-size: 1.5rem;
  color: var(--text);
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}

/* ── Cards ───────────────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.1rem;
  border-radius: var(--radius);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  transition: var(--transition);
}
.btn-primary {
  background: var(--gold);
  color: #0f1117;
}
.btn-primary:hover { background: #dbb85c; transform: translateY(-1px); box-shadow: 0 4px 12px var(--gold-glow); }
.btn-primary:active { transform: translateY(0); }

.btn-ghost {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
}
.btn-ghost:hover { color: var(--text); border-color: var(--text-muted); }

.btn-danger {
  background: transparent;
  color: var(--red);
  border: 1px solid rgba(158,74,74,0.3);
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
}
.btn-danger:hover { background: var(--red-bg); }

/* ── File uploader ───────────────────────────────────────────────────── */
.upload-zone {
  border: 2px dashed var(--border-gold);
  border-radius: var(--radius-lg);
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: background var(--transition), border-color var(--transition);
  position: relative;
}
.upload-zone:hover, .upload-zone.dragover {
  background: var(--gold-dim);
  border-color: var(--gold);
}
.upload-zone input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}
.upload-zone-icon { font-size: 2rem; margin-bottom: 0.5rem; display: block; }
.upload-zone p { color: var(--text-muted); font-size: 0.85rem; }
.upload-zone strong { color: var(--gold); }

/* ── File list ───────────────────────────────────────────────────────── */
.file-list { display: flex; flex-direction: column; gap: 0.5rem; }
.file-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  transition: border-color var(--transition);
}
.file-row:hover { border-color: var(--border-gold); }
.file-icon { color: var(--gold); flex-shrink: 0; }
.file-name { flex: 1; font-weight: 700; font-size: 0.88rem; }
.file-meta { color: var(--text-muted); font-size: 0.78rem; white-space: nowrap; }

/* ── Chat ────────────────────────────────────────────────────────────── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding-bottom: 1rem;
  min-height: 0;
}
.message { display: flex; gap: 0.75rem; max-width: 80%; }
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message.assistant { align-self: flex-start; }
.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  flex-shrink: 0;
}
.message.user .msg-avatar { background: var(--gold); color: #0f1117; font-weight: 700; }
.message.assistant .msg-avatar { background: var(--surface-2); color: var(--gold); border: 1px solid var(--border-gold); }
.msg-bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 0.75rem 1rem;
  font-size: 0.88rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}
.message.user .msg-bubble { background: var(--surface-2); border-color: var(--border-gold); }
.chat-input-row {
  display: flex;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.chat-input-row input { flex: 1; }

/* ── Diff ────────────────────────────────────────────────────────────── */
.diff-selectors { display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; }
.diff-selectors label { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.8rem; color: var(--text-muted); flex: 1; min-width: 160px; }
.diff-selectors select { width: 100%; }
.diff-stats { font-size: 0.8rem; color: var(--text-muted); padding: 0.5rem 0; }
.diff-stats .add { color: var(--green); }
.diff-stats .rem { color: var(--red); }

.diff-viewer {
  font-family: 'Courier New', monospace;
  font-size: 0.82rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  overflow-x: auto;
}
.diff-line {
  display: flex;
  gap: 0;
  min-width: 0;
  line-height: 1.5;
}
.diff-line.added   { background: var(--green-bg); }
.diff-line.removed { background: var(--red-bg); }
.diff-line.context { background: var(--surface); }
.diff-line.ellipsis { background: var(--surface); color: var(--text-dim); padding: 2px 8px; font-size: 0.78rem; }
.diff-gutter {
  width: 40px;
  min-width: 40px;
  text-align: right;
  padding: 1px 6px;
  color: var(--text-dim);
  user-select: none;
  border-right: 1px solid var(--border);
}
.diff-prefix {
  width: 24px;
  min-width: 24px;
  text-align: center;
  padding: 1px 0;
  user-select: none;
}
.diff-line.added   .diff-prefix { color: var(--green); }
.diff-line.removed .diff-prefix { color: var(--red); }
.diff-line.context .diff-prefix { color: var(--text-dim); }
.diff-text { padding: 1px 8px; white-space: pre; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.diff-line.added   .diff-text { color: #8ecf8e; }
.diff-line.removed .diff-text { color: #cf8e8e; }
.diff-line.context .diff-text { color: var(--text-muted); }

/* ── Glossary ────────────────────────────────────────────────────────── */
.glossary-search { width: 100%; max-width: 440px; }
.glossary-count { font-size: 0.8rem; color: var(--text-muted); }
.glossary-grid { display: flex; flex-direction: column; gap: 0.75rem; }

.term-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.term-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1.1rem;
  cursor: pointer;
  transition: background var(--transition);
  user-select: none;
}
.term-header:hover { background: var(--gold-dim); }
.term-header h3 { font-size: 1.05rem; color: var(--gold); font-family: var(--font-head); }
.term-chevron {
  color: var(--text-muted);
  transition: transform var(--transition);
  width: 16px;
  height: 16px;
}
.term-card.open .term-chevron { transform: rotate(180deg); }
.term-body {
  display: none;
  padding: 0 1.1rem 1.1rem;
  border-top: 1px solid var(--border);
  flex-direction: column;
  gap: 0.75rem;
}
.term-card.open .term-body { display: flex; }
.term-field label { font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-dim); display: block; margin-bottom: 0.2rem; }
.term-field p { font-size: 0.88rem; line-height: 1.6; }

.source-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: var(--surface-2);
  border: 1px solid var(--border-gold);
  border-radius: 20px;
  padding: 0.25rem 0.7rem;
  font-size: 0.75rem;
  color: var(--gold);
  cursor: pointer;
  transition: background var(--transition);
  margin: 0.2rem 0.2rem 0 0;
}
.source-chip:hover { background: var(--gold-dim); }
.source-popover {
  background: var(--surface-2);
  border: 1px solid var(--border-gold);
  border-radius: var(--radius);
  padding: 0.8rem 1rem;
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  line-height: 1.6;
  margin-top: 0.5rem;
  white-space: pre-wrap;
  display: none;
}
.source-popover.visible { display: block; }
mark.term-hl { background: rgba(200,168,80,0.25); border-radius: 2px; color: var(--gold); }

/* ── Toast ───────────────────────────────────────────────────────────── */
#toast-container {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 8888;
}
.toast {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.65rem 1rem;
  font-size: 0.85rem;
  box-shadow: var(--shadow);
  animation: toast-in 0.2s ease forwards;
  max-width: 320px;
}
.toast.success { border-color: var(--green); color: #8ecf8e; }
.toast.error   { border-color: var(--red);   color: #cf8e8e; }
@keyframes toast-in { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform: none; } }

/* ── Empty state ─────────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  color: var(--text-muted);
  padding: 3rem 1rem;
  font-size: 0.9rem;
}
.empty-state p { margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-dim); }
```

- [ ] **Step 4: Create `web/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Contrag</title>
  <link rel="stylesheet" href="/web/css/design-system.css">
  <link rel="stylesheet" href="/web/css/loader.css">
  <link rel="stylesheet" href="/web/css/app.css">
</head>
<body>

<!-- ── Lady Justice Loader ─────────────────────────────────────────── -->
<div id="justice-loader" aria-label="Loading" role="status">
  <div class="justice-brand">Contrag</div>
  <svg class="justice-scales" viewBox="0 0 140 150" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <!-- Pillar (static) -->
    <rect x="66" y="40" width="8" height="96" fill="#b0a080" rx="2"/>
    <!-- Base (static) -->
    <rect x="34" y="132" width="72" height="9" fill="#b0a080" rx="3"/>
    <!-- Top ornament (static) -->
    <circle cx="70" cy="36" r="6" fill="#c8a850"/>
    <!-- Animated beam group (pivots at center top) -->
    <g class="beam-group">
      <!-- Beam bar -->
      <line x1="10" y1="42" x2="130" y2="42" stroke="#c8a850" stroke-width="3.5" stroke-linecap="round"/>
      <!-- Left chain -->
      <line x1="20" y1="42" x2="20" y2="70" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="4 3"/>
      <!-- Right chain -->
      <line x1="120" y1="42" x2="120" y2="70" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="4 3"/>
      <!-- Left pan -->
      <g class="pan-left">
        <ellipse cx="20" cy="74" rx="19" ry="6" fill="#c8a850" opacity="0.9"/>
      </g>
      <!-- Right pan -->
      <g class="pan-right">
        <ellipse cx="120" cy="74" rx="19" ry="6" fill="#c8a850" opacity="0.9"/>
      </g>
    </g>
  </svg>
  <div class="justice-label" id="loader-label">Initialising&hellip;</div>
</div>

<!-- ── App Shell ───────────────────────────────────────────────────── -->
<div id="app" style="display:none">

  <!-- Sidebar Navigation -->
  <nav id="sidebar" aria-label="Main navigation">
    <div class="sidebar-brand">
      <h1>Contrag</h1>
      <span>Contract Intelligence</span>
    </div>
    <button class="nav-item active" data-tab="files">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      Files
    </button>
    <button class="nav-item" data-tab="chat">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      Chat
    </button>
    <button class="nav-item" data-tab="diff">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      Diff
    </button>
    <button class="nav-item" data-tab="glossary">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      Glossary
    </button>
  </nav>

  <!-- Tab Panels -->
  <main id="main">
    <div id="tab-files" class="tab-panel active" role="tabpanel" aria-label="Files">
      <h2 class="panel-title">Contract Files</h2>
      <div id="files-content"></div>
    </div>
    <div id="tab-chat" class="tab-panel" role="tabpanel" aria-label="Chat">
      <h2 class="panel-title">Contract Q&amp;A</h2>
      <div class="chat-messages" id="chat-messages"></div>
      <div class="chat-input-row">
        <input type="text" id="chat-input" placeholder="Ask about your contracts…" autocomplete="off">
        <button class="btn btn-primary" id="chat-send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          Send
        </button>
      </div>
    </div>
    <div id="tab-diff" class="tab-panel" role="tabpanel" aria-label="Diff">
      <h2 class="panel-title">Contract Diff</h2>
      <div id="diff-content"></div>
    </div>
    <div id="tab-glossary" class="tab-panel" role="tabpanel" aria-label="Glossary">
      <h2 class="panel-title">Legal Glossary</h2>
      <div id="glossary-content"></div>
    </div>
  </main>
</div>

<!-- Toast container -->
<div id="toast-container" aria-live="polite"></div>

<script type="module" src="/web/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Verify all files exist**

```bash
cd D:/Workspace/contrag && ls web/css/ && ls web/
```

Expected: `design-system.css`, `loader.css`, `app.css` in `web/css/`; `index.html` in `web/`

- [ ] **Step 6: Commit**

```bash
cd D:/Workspace/contrag && git add web/ && git commit -m "feat: add HTML shell, design system CSS, Lady Justice loader"
```

---

## Task 5: Frontend JS — API Client + Loader + App Router

**Files:**
- Create: `web/js/api.js`
- Create: `web/js/loader.js`
- Create: `web/js/app.js`

- [ ] **Step 1: Create `web/js/api.js`**

```js
const BASE = "";  // same origin

export async function getFiles() {
  const r = await fetch(`${BASE}/api/files`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function uploadFile(file, onProgress) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${BASE}/api/files/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteFile(filename) {
  const r = await fetch(`${BASE}/api/files/${encodeURIComponent(filename)}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getDiff(a, b) {
  const r = await fetch(`${BASE}/api/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getGlossary(q = "") {
  const url = q ? `${BASE}/api/glossary?q=${encodeURIComponent(q)}` : `${BASE}/api/glossary`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/**
 * Streams chat via SSE. Calls onChunk(text) for each token.
 * Calls onDone() when stream ends.
 */
export function streamChat(question, onChunk, onDone, onError) {
  fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then(async (r) => {
    if (!r.ok) { onError(await r.text()); return; }
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") { onDone(); return; }
        if (payload.startsWith("ERROR:")) { onError(payload.slice(6)); return; }
        // unescape newlines
        onChunk(payload.replace(/\\n/g, "\n"));
      }
    }
    onDone();
  }).catch(onError);
}
```

- [ ] **Step 2: Create `web/js/loader.js`**

```js
const loader = document.getElementById("justice-loader");
const label  = document.getElementById("loader-label");
const app    = document.getElementById("app");

export function showLoader(text = "Analysing\u2026") {
  label.textContent = text;
  loader.classList.remove("hidden");
}

export function hideLoader() {
  loader.classList.add("hidden");
  if (app.style.display === "none") {
    app.style.display = "flex";
  }
}
```

- [ ] **Step 3: Create `web/js/app.js`**

```js
import { hideLoader } from "./loader.js";
import { initFiles }   from "./tabs/files.js";
import { initChat }    from "./tabs/chat.js";
import { initDiff }    from "./tabs/diff.js";
import { initGlossary } from "./tabs/glossary.js";

// ── Tab routing ──────────────────────────────────────────────────────
const navItems = document.querySelectorAll(".nav-item[data-tab]");
const panels   = document.querySelectorAll(".tab-panel");

function switchTab(name) {
  navItems.forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  panels.forEach(p => p.classList.toggle("active", p.id === `tab-${name}`));
}

navItems.forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ── Toast ────────────────────────────────────────────────────────────
export function toast(msg, type = "info", ms = 4000) {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

// ── Init ─────────────────────────────────────────────────────────────
(async () => {
  try {
    await initFiles(toast);
    initChat(toast);
    initDiff(toast);
    await initGlossary(toast);
  } catch(e) {
    console.error("Init error:", e);
  } finally {
    hideLoader();
  }
})();
```

- [ ] **Step 4: Verify JS files exist**

```bash
ls D:/Workspace/contrag/web/js/
```

Expected: `api.js`, `loader.js`, `app.js`

- [ ] **Step 5: Commit**

```bash
cd D:/Workspace/contrag && git add web/js/api.js web/js/loader.js web/js/app.js && git commit -m "feat: add API client, loader, app router JS"
```

---

## Task 6: Files Tab JS

**Files:**
- Create: `web/js/tabs/files.js`

- [ ] **Step 1: Create `web/js/tabs/files.js`**

```js
import { getFiles, uploadFile, deleteFile } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

function fileIcon() {
  return `<svg class="file-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
}

function renderFiles(files) {
  const el = document.getElementById("files-content");
  if (!files.length) {
    el.innerHTML = `<div class="empty-state">⚖️<p>No contracts uploaded yet.</p></div>`;
    return;
  }
  el.innerHTML = `<div class="file-list">${files.map(f => `
    <div class="file-row" data-name="${f.name}">
      ${fileIcon()}
      <span class="file-name">${f.name}</span>
      <span class="file-meta">${f.size_kb} KB &middot; ${f.uploaded_at.slice(0,10)}</span>
      <button class="btn btn-danger del-btn" data-name="${f.name}" aria-label="Delete ${f.name}">Remove</button>
    </div>`).join("")}
  </div>`;

  el.querySelectorAll(".del-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm(`Remove ${btn.dataset.name}?`)) return;
      try {
        await deleteFile(btn.dataset.name);
        _toast(`${btn.dataset.name} removed.`, "success");
        refresh();
      } catch(e) { _toast(String(e), "error"); }
    });
  });
}

async function refresh() {
  const files = await getFiles();
  renderFiles(files);
}

function buildUploadZone(container) {
  const zone = document.createElement("div");
  zone.className = "upload-zone card";
  zone.innerHTML = `
    <span class="upload-zone-icon" aria-hidden="true">⚖</span>
    <p><strong>Click to upload</strong> or drag &amp; drop</p>
    <p>PDF, DOCX, TXT</p>
    <input type="file" accept=".pdf,.docx,.txt" multiple aria-label="Upload contracts">
  `;
  const input = zone.querySelector("input");

  async function handleFiles(files) {
    for (const file of files) {
      showLoader(`Ingesting ${file.name}…`);
      try {
        await uploadFile(file);
        _toast(`${file.name} ingested.`, "success");
      } catch(e) {
        _toast(`Failed: ${e.message || e}`, "error");
      }
    }
    hideLoader();
    await refresh();
  }

  input.addEventListener("change", () => handleFiles(Array.from(input.files)));
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    handleFiles(Array.from(e.dataTransfer.files));
  });

  container.prepend(zone);
}

export async function initFiles(toast) {
  _toast = toast;
  const container = document.getElementById("files-content");
  buildUploadZone(container);
  const files = await getFiles();
  renderFiles(files);
}
```

- [ ] **Step 2: Verify file created**

```bash
ls D:/Workspace/contrag/web/js/tabs/
```

Expected: `files.js`

- [ ] **Step 3: Commit**

```bash
cd D:/Workspace/contrag && git add web/js/tabs/files.js && git commit -m "feat: add files tab JS with drag-drop upload"
```

---

## Task 7: Chat Tab JS

**Files:**
- Create: `web/js/tabs/chat.js`

- [ ] **Step 1: Create `web/js/tabs/chat.js`**

```js
import { streamChat } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;
const messages = [];

function scrollToBottom() {
  const el = document.getElementById("chat-messages");
  el.scrollTop = el.scrollHeight;
}

function renderMessage(role, content, streaming = false) {
  const el = document.getElementById("chat-messages");
  const id = `msg-${Date.now()}`;
  const avatar = role === "user" ? "U" : "⚖";
  el.insertAdjacentHTML("beforeend", `
    <div class="message ${role}" id="${id}">
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-bubble">${content}${streaming ? '<span class="cursor">▌</span>' : ""}</div>
    </div>
  `);
  scrollToBottom();
  return id;
}

function updateMessage(id, content, streaming = false) {
  const bubble = document.querySelector(`#${id} .msg-bubble`);
  if (!bubble) return;
  bubble.innerHTML = content + (streaming ? '<span class="cursor">▌</span>' : "");
  scrollToBottom();
}

export function initChat(toast) {
  _toast = toast;
  const input   = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

  function sendMessage() {
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    input.disabled = true;
    sendBtn.disabled = true;

    renderMessage("user", question);
    messages.push({ role: "user", content: question });

    showLoader("Thinking\u2026");
    const replyId = renderMessage("assistant", "", true);

    let fullAnswer = "";

    streamChat(
      question,
      (chunk) => {
        if (fullAnswer === "" && replyId) hideLoader();
        fullAnswer += chunk;
        updateMessage(replyId, fullAnswer, true);
      },
      () => {
        updateMessage(replyId, fullAnswer, false);
        messages.push({ role: "assistant", content: fullAnswer });
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        hideLoader();
      },
      (err) => {
        hideLoader();
        updateMessage(replyId, `Error: ${err}`, false);
        input.disabled = false;
        sendBtn.disabled = false;
      }
    );
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) sendMessage(); });
}
```

- [ ] **Step 2: Commit**

```bash
cd D:/Workspace/contrag && git add web/js/tabs/chat.js && git commit -m "feat: add chat tab JS with SSE streaming"
```

---

## Task 8: Diff Tab JS

**Files:**
- Create: `web/js/tabs/diff.js`

- [ ] **Step 1: Create `web/js/tabs/diff.js`**

```js
import { getFiles, getDiff } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

function buildSelectors(files) {
  const names = files.map(f => f.name);
  if (names.length < 2) {
    return `<div class="empty-state">⚖️<p>Upload at least 2 contracts to compare.</p></div>`;
  }
  const opts = names.map(n => `<option value="${n}">${n}</option>`).join("");
  const opts2 = names.slice(1).map(n => `<option value="${n}">${n}</option>`).join("") +
                `<option value="${names[0]}">${names[0]}</option>`;
  return `
    <div class="card">
      <div class="diff-selectors">
        <label>Base contract<select id="diff-a">${opts}</select></label>
        <label>Compare contract<select id="diff-b">${opts2}</select></label>
        <button class="btn btn-primary" id="diff-btn">Compare</button>
      </div>
    </div>
    <div id="diff-result"></div>
  `;
}

const CTX = 3;

function renderDiff(hunks) {
  if (!hunks.length) return `<div class="empty-state">⚖️<p>The contracts are identical.</p></div>`;

  const added   = hunks.filter(h => h.type === "added").length;
  const removed = hunks.filter(h => h.type === "removed").length;

  let html = `<div class="diff-stats">
    <span class="add">+${added} additions</span> &nbsp; <span class="rem">−${removed} removals</span>
  </div><div class="diff-viewer">`;

  let ctxBuf = [];
  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      ctxBuf.forEach(h => { html += hunkHtml(h); });
    } else {
      ctxBuf.slice(0, CTX).forEach(h => { html += hunkHtml(h); });
      html += `<div class="diff-line ellipsis"><span style="padding:0 8px">…</span></div>`;
      ctxBuf.slice(-CTX).forEach(h => { html += hunkHtml(h); });
    }
    ctxBuf = [];
  }

  for (const h of hunks) {
    if (h.type === "context") { ctxBuf.push(h); }
    else { flushCtx(); html += hunkHtml(h); }
  }
  flushCtx();

  html += `</div>`;
  return html;
}

function esc(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function hunkHtml(h) {
  const prefix = h.type === "added" ? "+" : h.type === "removed" ? "−" : " ";
  const la = h.line_a ?? "";
  const lb = h.line_b ?? "";
  return `<div class="diff-line ${h.type}">
    <span class="diff-gutter">${la}</span>
    <span class="diff-gutter">${lb}</span>
    <span class="diff-prefix">${prefix}</span>
    <span class="diff-text">${esc(h.text)}</span>
  </div>`;
}

export async function initDiff(toast) {
  _toast = toast;
  const container = document.getElementById("diff-content");

  async function render() {
    const files = await getFiles();
    container.innerHTML = buildSelectors(files);

    const btn = document.getElementById("diff-btn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      const a = document.getElementById("diff-a").value;
      const b = document.getElementById("diff-b").value;
      if (a === b) { _toast("Select two different contracts.", "error"); return; }
      showLoader("Comparing contracts\u2026");
      try {
        const { hunks } = await getDiff(a, b);
        document.getElementById("diff-result").innerHTML = renderDiff(hunks);
      } catch(e) { _toast(String(e), "error"); }
      finally { hideLoader(); }
    });
  }

  await render();

  // Refresh when switching to diff tab
  document.querySelector('[data-tab="diff"]').addEventListener("click", render);
}
```

- [ ] **Step 2: Commit**

```bash
cd D:/Workspace/contrag && git add web/js/tabs/diff.js && git commit -m "feat: add diff tab JS with context-collapsing renderer"
```

---

## Task 9: Glossary Tab JS

**Files:**
- Create: `web/js/tabs/glossary.js`

- [ ] **Step 1: Create `web/js/tabs/glossary.js`**

```js
import { getGlossary } from "../api.js";

let _toast;

function renderGlossary(glossary) {
  const el = document.getElementById("glossary-content");
  const terms = Object.keys(glossary).sort();
  if (!terms.length) {
    el.innerHTML = `<div class="empty-state">⚖️<p>No glossary terms yet. Ingest a contract first.</p></div>`;
    return;
  }
  el.innerHTML = `
    <input class="glossary-search" type="text" id="glossary-search" placeholder="Search terms (e.g. indemnity, force majeure…)" autocomplete="off">
    <div class="glossary-count" id="glossary-count">${terms.length} term(s)</div>
    <div class="glossary-grid" id="glossary-grid"></div>
  `;
  renderTerms(terms, glossary);

  document.getElementById("glossary-search").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    const filtered = q ? terms.filter(t => t.includes(q)) : terms;
    document.getElementById("glossary-count").textContent = `${filtered.length} term(s)`;
    renderTerms(filtered, glossary);
  });
}

function renderTerms(terms, glossary) {
  const grid = document.getElementById("glossary-grid");
  grid.innerHTML = terms.map(term => termCard(term, glossary[term])).join("");
  grid.querySelectorAll(".term-header").forEach(h => {
    h.addEventListener("click", () => {
      h.closest(".term-card").classList.toggle("open");
    });
  });
  grid.querySelectorAll(".source-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const pop = chip.nextElementSibling;
      pop.classList.toggle("visible");
    });
  });
}

function hl(text, term) {
  const re = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), "gi");
  return text.replace(re, m => `<mark class="term-hl">${m}</mark>`);
}

function termCard(term, entry) {
  const sources = (entry.sources || []).map((src, i) => {
    const highlighted = hl(src.chunk || "", term);
    return `<span class="source-chip" role="button" tabindex="0" aria-expanded="false">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        ${src.file} · §${src.chunk_index + 1}
      </span>
      <div class="source-popover" role="region" aria-label="Source excerpt">${highlighted}</div>`;
  }).join("");

  return `
    <div class="term-card" data-term="${term}">
      <div class="term-header" role="button" tabindex="0" aria-expanded="false">
        <h3>${term.charAt(0).toUpperCase() + term.slice(1)}</h3>
        <svg class="term-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="term-body">
        <div class="term-field"><label>Legal definition</label><p>${entry.legal}</p></div>
        <div class="term-field"><label>Plain English</label><p>${entry.layman}</p></div>
        <div class="term-field"><label>Example</label><p><em>${entry.example}</em></p></div>
        <div class="term-field"><label>Sources</label>${sources || "<p style='color:var(--text-dim);font-size:0.8rem'>No sources available.</p>"}</div>
      </div>
    </div>
  `;
}

export async function initGlossary(toast) {
  _toast = toast;
  const glossary = await getGlossary();
  renderGlossary(glossary);

  document.querySelector('[data-tab="glossary"]').addEventListener("click", async () => {
    const g = await getGlossary();
    renderGlossary(g);
  });
}
```

- [ ] **Step 2: Commit**

```bash
cd D:/Workspace/contrag && git add web/js/tabs/glossary.js && git commit -m "feat: add glossary tab JS with search and source popovers"
```

---

## Task 10: Final Verification + Push

- [ ] **Step 1: Verify all web files exist**

```bash
cd D:/Workspace/contrag && find web/ -type f | sort
```

Expected:
```
web/css/app.css
web/css/design-system.css
web/css/loader.css
web/index.html
web/js/api.js
web/js/app.js
web/js/loader.js
web/js/tabs/chat.js
web/js/tabs/diff.js
web/js/tabs/files.js
web/js/tabs/glossary.js
```

- [ ] **Step 2: Verify backend starts cleanly**

```bash
cd D:/Workspace/contrag && python -c "from backend.main import app; print([r.path for r in app.routes])"
```

Expected: list includes `/api/files`, `/api/chat`, `/api/diff`, `/api/glossary`, `/`

- [ ] **Step 3: Run all tests**

```bash
cd D:/Workspace/contrag && python -m pytest tests/ -v
```

Expected: 9 PASSED

- [ ] **Step 4: Push**

```bash
cd D:/Workspace/contrag && git push origin master
```

---

## Self-Review

- ✅ Lady Justice full-screen loader on initial load + during async operations
- ✅ Sidebar navigation (4 items: Files, Chat, Diff, Glossary)
- ✅ Files tab: upload zone with drag+drop, file list with remove
- ✅ Chat tab: SSE streaming with live token rendering
- ✅ Diff tab: side-by-side contract selector, git-style colored diff
- ✅ Glossary tab: search, accordion term cards, clickable source chips with excerpts
- ✅ Zero Node.js dependency — pure vanilla HTML/CSS/JS
- ✅ Design system: dark theme (#0f1117), gold accent (#c8a850), EB Garamond headings
- ✅ FastAPI serves both API and static files
