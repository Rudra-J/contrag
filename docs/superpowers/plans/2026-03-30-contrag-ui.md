# Contrag UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit UI for the Contrag RAG system with 4 tabs: File Manager, RAG Chat, Contract Diff, and an auto-updating Legal Glossary.

**Architecture:** All backend logic (file management, diff, glossary extraction) lives in dedicated modules; Streamlit UI components live under `ui/`; persistent state (glossary, file metadata) lives in `data/` as JSON; uploaded contracts live in `uploads/`. The existing `chain.py`, `ingest.py`, and `retriever.py` are unchanged except for one small addition to `ingest.py` to trigger glossary extraction post-ingest.

**Tech Stack:** Streamlit, difflib (stdlib), langchain_ollama (ChatOllama llama3.2), unstructured, FAISS, HuggingFace embeddings, Python json (stdlib)

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `app.py` | Create | Streamlit entry point; tab routing; global CSS |
| `file_manager.py` | Create | Upload files to `uploads/`, remove, list, maintain `data/files_meta.json` |
| `diff_engine.py` | Create | Extract plain text from a contract, compute unified diff between two |
| `glossary_engine.py` | Create | Extract legal terms from text via Ollama, persist to `data/glossary.json` |
| `ui/__init__.py` | Create | Empty package marker |
| `ui/justice_loader.py` | Create | Returns HTML/CSS string for Lady Justice scales loading animation |
| `ui/tab_files.py` | Create | Tab 1: file tree, upload, remove |
| `ui/tab_chat.py` | Create | Tab 2: RAG chatbot + inline upload |
| `ui/tab_diff.py` | Create | Tab 3: pick two contracts, show colored unified diff |
| `ui/tab_glossary.py` | Create | Tab 4: render glossary dict with clickable sources |
| `data/glossary.json` | Create | Persistent glossary `{term: {legal, layman, example, sources: [{file, chunk}]}}` |
| `data/files_meta.json` | Create | `[{name, path, uploaded_at, size_kb}]` |
| `uploads/` | Create | Uploaded contract files |
| `ingest.py` | Modify | After FAISS save, call `glossary_engine.extract_and_update()` on the file |
| `requirements.txt` | Modify | Add `langchain-text-splitters` (already indirect), no new deps needed |

---

## Task 1: Project Scaffold

**Files:**
- Create: `uploads/.gitkeep`
- Create: `data/.gitkeep`
- Create: `data/glossary.json`
- Create: `data/files_meta.json`
- Create: `ui/__init__.py`

- [ ] **Step 1: Create directories and seed files**

```bash
cd D:/Workspace/contrag
mkdir -p uploads data ui
touch uploads/.gitkeep
echo "[]" > data/files_meta.json
echo "{}" > data/glossary.json
touch ui/__init__.py
```

- [ ] **Step 2: Verify structure**

```bash
find . -not -path "./.git/*" -not -path "./venv/*" -not -path "./faiss_index/*" | sort
```

Expected output includes: `./data/files_meta.json`, `./data/glossary.json`, `./ui/__init__.py`, `./uploads/.gitkeep`

- [ ] **Step 3: Commit**

```bash
git add uploads/.gitkeep data/ ui/__init__.py
git commit -m "chore: scaffold directories for UI, data, uploads"
```

---

## Task 2: File Manager Backend

**Files:**
- Create: `file_manager.py`
- Create: `tests/test_file_manager.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_file_manager.py`:

```python
import os, json, pytest, shutil
from pathlib import Path

# Patch paths before import
import file_manager
file_manager.UPLOAD_DIR = "tests/tmp_uploads"
file_manager.META_PATH = "tests/tmp_meta.json"

def setup_function():
    os.makedirs("tests/tmp_uploads", exist_ok=True)
    with open("tests/tmp_meta.json", "w") as f:
        json.dump([], f)

def teardown_function():
    shutil.rmtree("tests/tmp_uploads", ignore_errors=True)
    if os.path.exists("tests/tmp_meta.json"):
        os.remove("tests/tmp_meta.json")

def test_save_file_creates_file_and_meta():
    dummy = b"PDF content"
    path = file_manager.save_file("contract_a.pdf", dummy)
    assert os.path.exists(path)
    meta = file_manager.list_files()
    assert len(meta) == 1
    assert meta[0]["name"] == "contract_a.pdf"

def test_remove_file_deletes_file_and_meta():
    file_manager.save_file("contract_b.pdf", b"content")
    file_manager.remove_file("contract_b.pdf")
    assert not os.path.exists(os.path.join("tests/tmp_uploads", "contract_b.pdf"))
    assert len(file_manager.list_files()) == 0

def test_list_files_returns_metadata():
    file_manager.save_file("c.pdf", b"x")
    files = file_manager.list_files()
    assert "uploaded_at" in files[0]
    assert "size_kb" in files[0]
    assert "path" in files[0]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:/Workspace/contrag && python -m pytest tests/test_file_manager.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `file_manager` doesn't exist yet.

- [ ] **Step 3: Implement `file_manager.py`**

```python
import os, json, shutil
from datetime import datetime

UPLOAD_DIR = "uploads"
META_PATH = "data/files_meta.json"

def _load_meta():
    if not os.path.exists(META_PATH):
        return []
    with open(META_PATH) as f:
        return json.load(f)

def _save_meta(meta):
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

def save_file(filename: str, content: bytes) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    meta = _load_meta()
    meta = [m for m in meta if m["name"] != filename]  # replace if exists
    meta.append({
        "name": filename,
        "path": path,
        "uploaded_at": datetime.now().isoformat(),
        "size_kb": round(len(content) / 1024, 2)
    })
    _save_meta(meta)
    return path

def remove_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    meta = _load_meta()
    _save_meta([m for m in meta if m["name"] != filename])

def list_files():
    return _load_meta()

def get_file_path(filename: str) -> str:
    return os.path.join(UPLOAD_DIR, filename)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd D:/Workspace/contrag && python -m pytest tests/test_file_manager.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add file_manager.py tests/test_file_manager.py
git commit -m "feat: add file manager backend with upload/remove/list"
```

---

## Task 3: Diff Engine

**Files:**
- Create: `diff_engine.py`
- Create: `tests/test_diff_engine.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_diff_engine.py`:

```python
import diff_engine

def test_extract_text_from_txt(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello\nWorld\n")
    lines = diff_engine.extract_lines(str(f))
    assert lines == ["Hello\n", "World\n"]

def test_compute_diff_returns_hunks():
    a = ["line1\n", "line2\n", "line3\n"]
    b = ["line1\n", "line2 modified\n", "line3\n"]
    hunks = diff_engine.compute_diff(a, b, "a.pdf", "b.pdf")
    assert any(h["type"] == "removed" for h in hunks)
    assert any(h["type"] == "added" for h in hunks)

def test_compute_diff_context_lines():
    a = ["line1\n", "line2\n", "line3\n"]
    b = ["line1\n", "line2\n", "line3\n"]
    hunks = diff_engine.compute_diff(a, b, "a.pdf", "b.pdf")
    assert all(h["type"] == "context" for h in hunks) or hunks == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:/Workspace/contrag && python -m pytest tests/test_diff_engine.py -v
```

Expected: `ModuleNotFoundError` for `diff_engine`

- [ ] **Step 3: Implement `diff_engine.py`**

```python
import difflib
from unstructured.partition.auto import partition

def extract_lines(file_path: str) -> list[str]:
    """Extract text lines from a contract file (PDF, DOCX, TXT)."""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    elements = partition(filename=file_path)
    text = "\n".join(str(e) for e in elements if str(e).strip())
    return [line + "\n" for line in text.splitlines()]

def compute_diff(lines_a: list[str], lines_b: list[str], name_a: str, name_b: str) -> list[dict]:
    """
    Returns list of hunk dicts: {type: 'added'|'removed'|'context', text: str, line_a: int, line_b: int}
    """
    hunks = []
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k, line in enumerate(lines_a[i1:i2]):
                hunks.append({"type": "context", "text": line.rstrip("\n"), "line_a": i1+k+1, "line_b": j1+k+1})
        elif tag in ("replace", "delete"):
            for k, line in enumerate(lines_a[i1:i2]):
                hunks.append({"type": "removed", "text": line.rstrip("\n"), "line_a": i1+k+1, "line_b": None})
        if tag in ("replace", "insert"):
            for k, line in enumerate(lines_b[j1:j2]):
                hunks.append({"type": "added", "text": line.rstrip("\n"), "line_a": None, "line_b": j1+k+1})
    return hunks

def diff_contracts(path_a: str, path_b: str, name_a: str, name_b: str) -> list[dict]:
    lines_a = extract_lines(path_a)
    lines_b = extract_lines(path_b)
    return compute_diff(lines_a, lines_b, name_a, name_b)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd D:/Workspace/contrag && python -m pytest tests/test_diff_engine.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add diff_engine.py tests/test_diff_engine.py
git commit -m "feat: add diff engine with line extraction and unified diff"
```

---

## Task 4: Glossary Engine

**Files:**
- Create: `glossary_engine.py`
- Create: `tests/test_glossary_engine.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_glossary_engine.py`:

```python
import json, os, pytest
import glossary_engine

glossary_engine.GLOSSARY_PATH = "tests/tmp_glossary.json"

def setup_function():
    with open("tests/tmp_glossary.json", "w") as f:
        json.dump({}, f)

def teardown_function():
    if os.path.exists("tests/tmp_glossary.json"):
        os.remove("tests/tmp_glossary.json")

def test_load_glossary_empty():
    g = glossary_engine.load_glossary()
    assert g == {}

def test_save_and_load_term():
    entry = {
        "legal": "Force majeure refers to...",
        "layman": "An act of God clause...",
        "example": "If a hurricane destroys...",
        "sources": [{"file": "contract_a.pdf", "chunk": "Force majeure events include...", "chunk_index": 3}]
    }
    glossary_engine.save_term("force majeure", entry)
    g = glossary_engine.load_glossary()
    assert "force majeure" in g
    assert g["force majeure"]["legal"] == "Force majeure refers to..."

def test_merge_source_does_not_duplicate():
    entry = {
        "legal": "Indemnity means...",
        "layman": "Protection from loss...",
        "example": "Company A agrees to cover...",
        "sources": [{"file": "a.pdf", "chunk": "indemnify and hold harmless", "chunk_index": 1}]
    }
    glossary_engine.save_term("indemnity", entry)
    # Save same term again with same source — should not duplicate
    glossary_engine.save_term("indemnity", entry)
    g = glossary_engine.load_glossary()
    assert len(g["indemnity"]["sources"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd D:/Workspace/contrag && python -m pytest tests/test_glossary_engine.py -v
```

Expected: `ModuleNotFoundError` for `glossary_engine`

- [ ] **Step 3: Implement `glossary_engine.py`**

```python
import json, os, re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

GLOSSARY_PATH = "data/glossary.json"
OLLAMA_MODEL = "llama3.2"

EXTRACT_PROMPT = ChatPromptTemplate.from_template("""
You are a legal expert. Given the following contract text, identify ALL distinct legal terms or legal phrases.
For each term return a JSON array. Each element must have exactly these keys:
- "term": the legal term (lowercase)
- "legal": one-sentence definition in precise legal language
- "layman": one-sentence plain English explanation
- "example": one concrete layman example sentence showing the term in use
- "chunk": the exact short excerpt (max 30 words) from the text where this term appears

Return ONLY a valid JSON array, no markdown, no explanation.

CONTRACT TEXT:
{text}
""")

def load_glossary() -> dict:
    if not os.path.exists(GLOSSARY_PATH):
        return {}
    with open(GLOSSARY_PATH) as f:
        return json.load(f)

def save_term(term: str, entry: dict):
    glossary = load_glossary()
    term = term.lower().strip()
    if term in glossary:
        existing_files = {s["file"] for s in glossary[term]["sources"]}
        for src in entry["sources"]:
            if src["file"] not in existing_files:
                glossary[term]["sources"].append(src)
    else:
        glossary[term] = entry
    with open(GLOSSARY_PATH, "w") as f:
        json.dump(glossary, f, indent=2)

def extract_and_update(file_path: str, file_name: str, chunks: list[str]):
    """
    Called after ingestion. Sends each chunk to Ollama to extract legal terms.
    chunks: list of plain-text chunk strings extracted during ingest
    """
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)
    chain = EXTRACT_PROMPT | llm | StrOutputParser()

    for chunk_index, chunk_text in enumerate(chunks):
        if len(chunk_text.strip()) < 50:
            continue
        try:
            raw = chain.invoke({"text": chunk_text})
            # Strip markdown code fences if present
            raw = re.sub(r"```json|```", "", raw).strip()
            terms = json.loads(raw)
            if not isinstance(terms, list):
                continue
            for item in terms:
                if not all(k in item for k in ("term", "legal", "layman", "example", "chunk")):
                    continue
                entry = {
                    "legal": item["legal"],
                    "layman": item["layman"],
                    "example": item["example"],
                    "sources": [{
                        "file": file_name,
                        "chunk": item["chunk"],
                        "chunk_index": chunk_index
                    }]
                }
                save_term(item["term"], entry)
        except (json.JSONDecodeError, KeyError):
            continue  # Skip malformed LLM output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd D:/Workspace/contrag && python -m pytest tests/test_glossary_engine.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add glossary_engine.py tests/test_glossary_engine.py
git commit -m "feat: add glossary engine with Ollama extraction and JSON persistence"
```

---

## Task 5: Wire Glossary Into Ingest

**Files:**
- Modify: `ingest.py`

- [ ] **Step 1: Read current `ingest.py`**

The current file ends after `db.save_local(store_path)`. We will add a call to `glossary_engine.extract_and_update()` passing the chunks' page_content and the file name.

- [ ] **Step 2: Modify `ingest.py`**

Replace the full file content with:

```python
from unstructured.partition.auto import partition
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os
import glossary_engine

CLAUSE_MARKERS = [
    "\n1.", "\n2.", "\n3.", "\nWHEREAS", "\nIN WITNESS",
    "\nARTICLE", "\nSECTION", "\nSCHEDULE"
]

EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

def ingest(file_path: str, store_path: str = "faiss_index"):
    elements = partition(filename=file_path)
    full_text = "\n".join([str(e) for e in elements if str(e).strip()])

    splitter = RecursiveCharacterTextSplitter(
        separators=CLAUSE_MARKERS + ["\n\n", "\n", ". ", " "],
        chunk_size=800,
        chunk_overlap=100,
    )
    chunks = splitter.create_documents(
        [full_text],
        metadatas=[{"source": os.path.basename(file_path)}]
    )

    if os.path.exists(store_path):
        db = FAISS.load_local(store_path, EMBEDDINGS,
                              allow_dangerous_deserialization=True)
        db.add_documents(chunks)
    else:
        db = FAISS.from_documents(chunks, EMBEDDINGS)

    db.save_local(store_path)
    print(f"Ingested {len(chunks)} chunks from {os.path.basename(file_path)}")

    # Auto-update glossary from newly ingested chunks
    chunk_texts = [c.page_content for c in chunks]
    file_name = os.path.basename(file_path)
    glossary_engine.extract_and_update(file_path, file_name, chunk_texts)
```

- [ ] **Step 3: Verify import works**

```bash
cd D:/Workspace/contrag && python -c "import ingest; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ingest.py
git commit -m "feat: trigger glossary extraction after ingest"
```

---

## Task 6: Lady Justice Loading Animation

**Files:**
- Create: `ui/justice_loader.py`

- [ ] **Step 1: Create `ui/justice_loader.py`**

```python
def get_justice_loader_html() -> str:
    """
    Returns an HTML/CSS string rendering Lady Justice with scales tipping side to side.
    Embed with st.markdown(get_justice_loader_html(), unsafe_allow_html=True)
    """
    return """
<style>
.justice-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    font-family: serif;
}
.justice-label {
    margin-top: 1rem;
    font-size: 0.9rem;
    color: #888;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.scales-svg {
    width: 120px;
    height: 120px;
}
/* The beam rocks on a pivot */
@keyframes rock {
    0%   { transform: rotate(-18deg); }
    50%  { transform: rotate(18deg); }
    100% { transform: rotate(-18deg); }
}
/* Left pan drops then rises */
@keyframes pan-left {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(12px); }
    100% { transform: translateY(0px); }
}
/* Right pan rises then drops */
@keyframes pan-right {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(-12px); }
    100% { transform: translateY(0px); }
}
.beam {
    transform-origin: 60px 38px;
    animation: rock 1.6s ease-in-out infinite;
}
.pan-left-group {
    animation: pan-left 1.6s ease-in-out infinite;
}
.pan-right-group {
    animation: pan-right 1.6s ease-in-out infinite;
}
</style>
<div class="justice-container">
  <svg class="scales-svg" viewBox="0 0 120 130" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- Pillar -->
    <rect x="57" y="36" width="6" height="80" fill="#b0a080" rx="2"/>
    <!-- Base -->
    <rect x="30" y="114" width="60" height="8" fill="#b0a080" rx="3"/>
    <!-- Top ornament -->
    <circle cx="60" cy="32" r="5" fill="#c8a850"/>
    <!-- Beam (rocks) -->
    <g class="beam">
      <line x1="12" y1="38" x2="108" y2="38" stroke="#c8a850" stroke-width="3" stroke-linecap="round"/>
      <!-- Left chain -->
      <line x1="20" y1="38" x2="20" y2="62" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="3 2"/>
      <!-- Right chain -->
      <line x1="100" y1="38" x2="100" y2="62" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="3 2"/>
      <!-- Left pan (animates independently) -->
      <g class="pan-left-group">
        <ellipse cx="20" cy="66" rx="16" ry="5" fill="#c8a850" opacity="0.85"/>
      </g>
      <!-- Right pan (animates independently) -->
      <g class="pan-right-group">
        <ellipse cx="100" cy="66" rx="16" ry="5" fill="#c8a850" opacity="0.85"/>
      </g>
    </g>
  </svg>
  <div class="justice-label">Analysing&hellip;</div>
</div>
"""
```

- [ ] **Step 2: Verify import**

```bash
cd D:/Workspace/contrag && python -c "from ui.justice_loader import get_justice_loader_html; print(len(get_justice_loader_html()), 'chars')"
```

Expected: prints a number > 100

- [ ] **Step 3: Commit**

```bash
git add ui/justice_loader.py
git commit -m "feat: add Lady Justice scales loading animation"
```

---

## Task 7: Tab 1 — File Manager UI

**Files:**
- Create: `ui/tab_files.py`

- [ ] **Step 1: Create `ui/tab_files.py`**

```python
import streamlit as st
import file_manager
import ingest

def render():
    st.subheader("Contract Files")

    # Upload section
    st.markdown("#### Upload Contracts")
    uploaded = st.file_uploader(
        "Upload PDF or DOCX contracts",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="files_tab_uploader"
    )
    if uploaded:
        for f in uploaded:
            with st.spinner(f"Ingesting {f.name}..."):
                path = file_manager.save_file(f.name, f.read())
                try:
                    ingest.ingest(path)
                    st.success(f"{f.name} ingested successfully.")
                except Exception as e:
                    st.error(f"Failed to ingest {f.name}: {e}")
        st.rerun()

    # File tree
    st.markdown("#### Uploaded Files")
    files = file_manager.list_files()
    if not files:
        st.info("No contracts uploaded yet.")
        return

    for meta in files:
        col1, col2, col3 = st.columns([5, 2, 1])
        col1.markdown(f"📄 **{meta['name']}**")
        col2.caption(f"{meta['size_kb']} KB · {meta['uploaded_at'][:10]}")
        if col3.button("🗑", key=f"del_{meta['name']}", help=f"Remove {meta['name']}"):
            file_manager.remove_file(meta["name"])
            st.rerun()
```

- [ ] **Step 2: Verify import**

```bash
cd D:/Workspace/contrag && python -c "from ui.tab_files import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/tab_files.py
git commit -m "feat: add file manager tab UI"
```

---

## Task 8: Tab 2 — RAG Chat UI

**Files:**
- Create: `ui/tab_chat.py`

- [ ] **Step 1: Create `ui/tab_chat.py`**

```python
import streamlit as st
import file_manager
import ingest
from chain import ask_stream
from ui.justice_loader import get_justice_loader_html

def render():
    st.subheader("Contract Q&A")

    # Inline upload
    with st.expander("Upload a contract to chat about", expanded=False):
        f = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf","docx","txt"], key="chat_uploader")
        if f:
            with st.spinner(f"Ingesting {f.name}..."):
                path = file_manager.save_file(f.name, f.read())
                try:
                    ingest.ingest(path)
                    st.success(f"{f.name} ready.")
                except Exception as e:
                    st.error(str(e))

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Ask about your contracts…")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            loader_placeholder = st.empty()
            loader_placeholder.markdown(get_justice_loader_html(), unsafe_allow_html=True)
            answer_placeholder = st.empty()
            full_answer = ""
            try:
                loader_placeholder.empty()
                for chunk in ask_stream(question):
                    full_answer += chunk
                    answer_placeholder.markdown(full_answer + "▌")
                answer_placeholder.markdown(full_answer)
            except FileNotFoundError:
                loader_placeholder.empty()
                answer_placeholder.warning("No contracts ingested yet. Upload a contract first.")
                full_answer = "No contracts ingested yet."

        st.session_state.messages.append({"role": "assistant", "content": full_answer})
```

- [ ] **Step 2: Verify import**

```bash
cd D:/Workspace/contrag && python -c "from ui.tab_chat import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/tab_chat.py
git commit -m "feat: add RAG chat tab with streaming and Lady Justice loader"
```

---

## Task 9: Tab 3 — Contract Diff UI

**Files:**
- Create: `ui/tab_diff.py`

- [ ] **Step 1: Create `ui/tab_diff.py`**

```python
import streamlit as st
import file_manager
import diff_engine
from ui.justice_loader import get_justice_loader_html

_CONTEXT_LINES = 3  # unchanged lines to show around each change

def _render_diff(hunks: list[dict]):
    """Render diff hunks as styled HTML blocks."""
    # Group hunks; collapse long context runs
    lines_html = []
    context_buffer = []

    def flush_context():
        if len(context_buffer) <= _CONTEXT_LINES * 2:
            for h in context_buffer:
                lines_html.append(_hunk_html(h))
        else:
            for h in context_buffer[:_CONTEXT_LINES]:
                lines_html.append(_hunk_html(h))
            lines_html.append(
                '<div style="color:#888;padding:2px 8px;font-family:monospace;font-size:0.8rem">…</div>'
            )
            for h in context_buffer[-_CONTEXT_LINES:]:
                lines_html.append(_hunk_html(h))
        context_buffer.clear()

    for h in hunks:
        if h["type"] == "context":
            context_buffer.append(h)
        else:
            flush_context()
            lines_html.append(_hunk_html(h))

    flush_context()

    html = (
        '<div style="font-family:monospace;font-size:0.85rem;border:1px solid #333;'
        'border-radius:6px;overflow:hidden;background:#1e1e1e">'
        + "".join(lines_html)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

def _hunk_html(h: dict) -> str:
    text = h["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    line_a = h["line_a"] or ""
    line_b = h["line_b"] or ""
    if h["type"] == "added":
        bg, prefix, color = "#1a3a1a", "+", "#6dbf67"
    elif h["type"] == "removed":
        bg, prefix, color = "#3a1a1a", "−", "#bf6767"
    else:
        bg, prefix, color = "transparent", " ", "#888"
    return (
        f'<div style="background:{bg};padding:1px 8px;display:flex;gap:8px">'
        f'<span style="color:#555;min-width:36px;text-align:right;user-select:none">{line_a}</span>'
        f'<span style="color:#555;min-width:36px;text-align:right;user-select:none">{line_b}</span>'
        f'<span style="color:{color};white-space:pre-wrap">{prefix} {text}</span>'
        f'</div>'
    )

def render():
    st.subheader("Contract Diff")
    files = file_manager.list_files()
    names = [m["name"] for m in files]

    if len(names) < 2:
        st.info("Upload at least 2 contracts to compare.")
        return

    col1, col2 = st.columns(2)
    a = col1.selectbox("Base contract", names, key="diff_a")
    b = col2.selectbox("Compare contract", [n for n in names if n != a], key="diff_b")

    if st.button("Compare", type="primary"):
        loader = st.empty()
        loader.markdown(get_justice_loader_html(), unsafe_allow_html=True)
        path_a = file_manager.get_file_path(a)
        path_b = file_manager.get_file_path(b)
        try:
            hunks = diff_engine.diff_contracts(path_a, path_b, a, b)
            loader.empty()
            added = sum(1 for h in hunks if h["type"] == "added")
            removed = sum(1 for h in hunks if h["type"] == "removed")
            st.caption(f"+{added} additions · −{removed} removals")
            _render_diff(hunks)
        except Exception as e:
            loader.empty()
            st.error(str(e))
```

- [ ] **Step 2: Verify import**

```bash
cd D:/Workspace/contrag && python -c "from ui.tab_diff import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/tab_diff.py
git commit -m "feat: add contract diff tab with git-style colored diff"
```

---

## Task 10: Tab 4 — Glossary UI

**Files:**
- Create: `ui/tab_glossary.py`

- [ ] **Step 1: Create `ui/tab_glossary.py`**

```python
import streamlit as st
import glossary_engine

def render():
    st.subheader("Legal Glossary")
    glossary = glossary_engine.load_glossary()

    if not glossary:
        st.info("No glossary terms yet. Upload and ingest a contract to auto-populate.")
        return

    # Search / filter
    search = st.text_input("Search terms", placeholder="e.g. indemnity, force majeure…")
    terms = sorted(glossary.keys())
    if search:
        terms = [t for t in terms if search.lower() in t]

    if not terms:
        st.warning("No matching terms found.")
        return

    st.caption(f"{len(terms)} term(s) found")

    for term in terms:
        entry = glossary[term]
        with st.expander(f"**{term.title()}**", expanded=False):
            st.markdown(f"**Legal definition:** {entry['legal']}")
            st.markdown(f"**Plain English:** {entry['layman']}")
            st.markdown(f"**Example:** _{entry['example']}_")

            st.markdown("**Sources:**")
            for src in entry.get("sources", []):
                file_name = src["file"]
                chunk_text = src.get("chunk", "")
                chunk_index = src.get("chunk_index", 0)
                # Clickable source — expands to show the exact excerpt
                with st.expander(f"📄 {file_name} · chunk #{chunk_index}", expanded=False):
                    # Highlight the term within the chunk
                    highlighted = chunk_text.replace(
                        term,
                        f'<mark style="background:#c8a85044;border-radius:3px">{term}</mark>'
                    )
                    st.markdown(
                        f'<div style="background:#1e1e1e;padding:10px;border-radius:6px;'
                        f'font-family:monospace;font-size:0.85rem;line-height:1.5">{highlighted}</div>',
                        unsafe_allow_html=True
                    )
```

- [ ] **Step 2: Verify import**

```bash
cd D:/Workspace/contrag && python -c "from ui.tab_glossary import render; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/tab_glossary.py
git commit -m "feat: add glossary tab with clickable source excerpts"
```

---

## Task 11: Main App Entry Point

**Files:**
- Create: `app.py`

- [ ] **Step 1: Create `app.py`**

```python
import streamlit as st

st.set_page_config(
    page_title="Contrag",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Global dark theme overrides
st.markdown("""
<style>
/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #333;
}
.stTabs [data-baseweb="tab"] {
    padding: 8px 20px;
    font-weight: 500;
    border-radius: 6px 6px 0 0;
}
/* Subtle brand header */
.contrag-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0.5rem 0 1.5rem 0;
    border-bottom: 1px solid #333;
    margin-bottom: 1.5rem;
}
.contrag-title {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    font-family: serif;
}
.contrag-subtitle {
    font-size: 0.85rem;
    color: #888;
    margin-top: 2px;
}
</style>
<div class="contrag-header">
  <span style="font-size:2rem">⚖️</span>
  <div>
    <div class="contrag-title">Contrag</div>
    <div class="contrag-subtitle">Contract Intelligence — RAG · Diff · Glossary</div>
  </div>
</div>
""", unsafe_allow_html=True)

from ui import tab_files, tab_chat, tab_diff, tab_glossary

tab1, tab2, tab3, tab4 = st.tabs(["📁 Files", "💬 Chat", "🔀 Diff", "📖 Glossary"])

with tab1:
    tab_files.render()

with tab2:
    tab_chat.render()

with tab3:
    tab_diff.render()

with tab4:
    tab_glossary.render()
```

- [ ] **Step 2: Verify app starts without import errors**

```bash
cd D:/Workspace/contrag && python -c "
import sys
# Patch streamlit to avoid full server startup
import unittest.mock as mock
with mock.patch('streamlit.set_page_config'), \
     mock.patch('streamlit.markdown'), \
     mock.patch('streamlit.tabs', return_value=[mock.MagicMock()]*4):
    import app
print('Import OK')
"
```

Expected: `Import OK`

- [ ] **Step 3: Run the app manually to verify UI loads**

```bash
cd D:/Workspace/contrag && streamlit run app.py
```

Open `http://localhost:8501` and verify:
- Header with ⚖️ logo appears
- 4 tabs are visible: Files, Chat, Diff, Glossary
- Files tab shows upload widget

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add main Streamlit app with 4-tab layout"
```

---

## Task 12: Push and Final Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd D:/Workspace/contrag && python -m pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 2: Update requirements.txt**

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
```

- [ ] **Step 3: Commit requirements**

```bash
git add requirements.txt
git commit -m "chore: add pytest and langchain-core to requirements"
```

- [ ] **Step 4: Push to GitHub**

```bash
cd D:/Workspace/contrag && git push origin master
```

Expected: All commits pushed successfully.

---

## Self-Review

**Spec coverage check:**
- ✅ Lady Justice loading animation (Tasks 6, used in Tasks 8, 9)
- ✅ Tab 1: File tree + upload + remove (Task 7)
- ✅ Tab 2: RAG chatbot + upload from chat tab (Task 8)
- ✅ Tab 3: Contract diff, select 2 contracts, git-diff style with green/red (Task 9)
- ✅ Tab 4: Glossary dictionary (Task 10)
- ✅ Glossary auto-updates on ingest (Task 5)
- ✅ Glossary uses Ollama (Task 4 — ChatOllama llama3.2)
- ✅ Glossary shows: term, source (clickable), legal definition, layman definition, layman example (Task 10)
- ✅ Clickable source shows the exact text chunk with term highlighted (Task 10)

**Placeholder scan:** No TBDs or "implement later" present.

**Type consistency:** `diff_engine.compute_diff` returns `list[dict]` with keys `type/text/line_a/line_b` — consumed identically in `tab_diff.py`. `glossary_engine.save_term` takes `(term: str, entry: dict)` — called identically from `extract_and_update`. `file_manager.list_files()` returns list of dicts with `name/path/uploaded_at/size_kb` — consumed in `tab_files.py` and `tab_diff.py` correctly.
