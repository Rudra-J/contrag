# Chat File Tagging + Diff Inline Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users tag specific uploaded files in the chat tab to scope RAG queries, and let users upload or pick existing files directly from the diff tab.

**Architecture:** The FAISS index already stores `metadata={"source": filename}` per chunk. We add a `sources` filter to `retriever.py` using a callable filter, thread it through `chain.py` and `/api/chat`, then wire up the chat UI with tag chips and the diff UI with per-slot hybrid select+upload controls. All uploads from any tab go through the existing `POST /api/files/upload` endpoint so they appear in the Files page.

**Tech Stack:** Python (LangChain FAISS callable filter), FastAPI, vanilla JS ES modules, CSS custom properties.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `retriever.py` | Modify | Accept `sources: list[str] \| None`; apply callable filter to FAISS retriever |
| `chain.py` | Modify | Accept `sources` param; pass to `get_retriever` |
| `backend/main.py` | Modify | Read `sources` from `/api/chat` body; pass to `ask_stream` |
| `web/js/api.js` | Modify | `streamChat` accepts optional `sources` array in POST body |
| `web/js/tabs/chat.js` | Modify | File tag picker strip above input; send tagged sources with question |
| `web/js/tabs/diff.js` | Modify | Each slot gets hybrid select+upload; upload calls existing endpoint then refreshes selectors |
| `web/css/app.css` | Modify | Styles for tag chips (`.file-tag`, `.file-tag.active`) and diff upload slots |
| `tests/test_retriever.py` | Modify | Add tests for filtered retriever |
| `tests/test_chain.py` | Create | Test `ask_stream` with and without sources filter |

---

### Task 1: Backend — filtered retriever + chain

**Files:**
- Modify: `retriever.py`
- Modify: `chain.py`
- Modify: `backend/main.py:97-115`
- Modify: `tests/test_retriever.py`
- Create: `tests/test_chain.py`

- [ ] **Step 1: Write failing test for retriever with sources filter**

```python
# tests/test_retriever.py  — add after existing tests

def test_get_retriever_with_sources_passes_filter(tmp_path, monkeypatch):
    """get_retriever with sources= sets a filter on the FAISS retriever."""
    from unittest.mock import MagicMock, patch

    fake_db = MagicMock()
    fake_retriever = MagicMock()
    fake_db.as_retriever.return_value = fake_retriever

    with patch("retriever.os.path.exists", return_value=True), \
         patch("retriever.FAISS.load_local", return_value=fake_db):
        from retriever import get_retriever
        get_retriever(sources=["contract_a.pdf"])

    call_kwargs = fake_db.as_retriever.call_args[1]["search_kwargs"]
    assert "filter" in call_kwargs
    filter_fn = call_kwargs["filter"]
    assert filter_fn({"source": "contract_a.pdf"}) is True
    assert filter_fn({"source": "contract_b.pdf"}) is False


def test_get_retriever_no_sources_no_filter(monkeypatch):
    """get_retriever with no sources sets no filter."""
    from unittest.mock import MagicMock, patch

    fake_db = MagicMock()
    with patch("retriever.os.path.exists", return_value=True), \
         patch("retriever.FAISS.load_local", return_value=fake_db):
        from retriever import get_retriever
        get_retriever()

    call_kwargs = fake_db.as_retriever.call_args[1]["search_kwargs"]
    assert "filter" not in call_kwargs
```

- [ ] **Step 2: Run test to confirm it fails**

```
pytest tests/test_retriever.py::test_get_retriever_with_sources_passes_filter tests/test_retriever.py::test_get_retriever_no_sources_no_filter -v
```

Expected: FAIL — `get_retriever` has no `sources` parameter yet.

- [ ] **Step 3: Update `retriever.py`**

```python
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

def get_retriever(store_path: str = "faiss_index", k: int = 5, sources: list = None):
    if not os.path.exists(store_path):
        raise FileNotFoundError("No contracts ingested yet. Upload a contract first.")
    db = FAISS.load_local(store_path, EMBEDDINGS,
                          allow_dangerous_deserialization=True)
    search_kwargs = {"k": k}
    if sources:
        source_set = set(sources)
        search_kwargs["filter"] = lambda meta: meta.get("source") in source_set
    return db.as_retriever(search_kwargs=search_kwargs)
```

- [ ] **Step 4: Run retriever tests — expect PASS**

```
pytest tests/test_retriever.py -v
```

Expected: All PASS.

- [ ] **Step 5: Write failing test for chain with sources**

Create `tests/test_chain.py`:

```python
# tests/test_chain.py
import pytest
from unittest.mock import MagicMock, patch


def test_ask_stream_passes_sources_to_retriever():
    """ask_stream with sources= passes them to get_retriever."""
    captured = {}

    def fake_get_retriever(store_path="faiss_index", k=5, sources=None):
        captured["sources"] = sources
        mock_retriever = MagicMock()
        mock_retriever.__or__ = lambda self, other: other  # allow | chaining
        return mock_retriever

    fake_chain = MagicMock()
    fake_chain.stream.return_value = iter(["Hello"])

    with patch("chain.get_retriever", side_effect=fake_get_retriever), \
         patch("chain.build_chain", return_value=fake_chain):
        from chain import ask_stream
        list(ask_stream("test question", sources=["a.pdf"]))

    assert captured.get("sources") == ["a.pdf"]


def test_ask_stream_no_sources_uses_full_index():
    """ask_stream with no sources passes sources=None to get_retriever."""
    captured = {}

    def fake_get_retriever(store_path="faiss_index", k=5, sources=None):
        captured["sources"] = sources
        mock_retriever = MagicMock()
        mock_retriever.__or__ = lambda self, other: other
        return mock_retriever

    fake_chain = MagicMock()
    fake_chain.stream.return_value = iter(["Hello"])

    with patch("chain.get_retriever", side_effect=fake_get_retriever), \
         patch("chain.build_chain", return_value=fake_chain):
        from chain import ask_stream
        list(ask_stream("test question"))

    assert captured.get("sources") is None
```

- [ ] **Step 6: Run chain tests — expect FAIL**

```
pytest tests/test_chain.py -v
```

Expected: FAIL — `ask_stream` has no `sources` param yet.

- [ ] **Step 7: Update `chain.py`**

```python
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from retriever import get_retriever

OLLAMA_MODEL = "llama3.2"

PROMPT = ChatPromptTemplate.from_template("""You are a legal contract analyst.
Answer the question using ONLY the contract clauses below.
For each point you make, cite the source in square brackets like [Clause from: filename.pdf].
If the answer is not found in the clauses, respond with exactly:
"This is not addressed in the uploaded contracts."
Do not speculate or use outside knowledge.

CONTRACT CLAUSES:
{context}

QUESTION: {question}

ANSWER:""")

def format_docs(docs):
    return "\n\n---\n\n".join(
        f"[Clause from: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
        for d in docs
    )

def build_chain(sources: list = None):
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)
    retriever = get_retriever(sources=sources)
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )

def ask(question: str, sources: list = None) -> str:
    return build_chain(sources=sources).invoke(question)

def ask_stream(question: str, sources: list = None):
    for chunk in build_chain(sources=sources).stream(question):
        yield chunk
```

- [ ] **Step 8: Update `/api/chat` in `backend/main.py`**

Replace lines 97–115:

```python
@app.post("/api/chat")
async def chat(body: dict):
    question = body.get("question", "")
    if not question.strip():
        raise HTTPException(400, "Question is required")
    sources = body.get("sources") or None  # [] treated as None → full index

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
```

- [ ] **Step 9: Run all tests**

```
pytest tests/ -v
```

Expected: All existing tests still pass, new tests pass.

- [ ] **Step 10: Commit**

```bash
git add retriever.py chain.py backend/main.py tests/test_retriever.py tests/test_chain.py
git commit -m "feat: add per-source FAISS filter to retriever and chat API"
```

---

### Task 2: Chat UI — file tag picker

**Files:**
- Modify: `web/js/api.js`
- Modify: `web/js/tabs/chat.js`
- Modify: `web/css/app.css`

- [ ] **Step 1: Update `streamChat` in `web/js/api.js` to accept `sources`**

Replace the `streamChat` function (lines 40–66):

```js
/**
 * Streams chat via SSE. Calls onChunk(text) for each token.
 * Calls onDone() when stream ends. Calls onError(msg) on failure.
 * @param {string} question
 * @param {string[]} sources  - filenames to filter by; [] means all
 * @param {Function} onChunk
 * @param {Function} onDone
 * @param {Function} onError
 */
export function streamChat(question, sources, onChunk, onDone, onError) {
  fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, sources }),
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
        onChunk(payload.replace(/\\n/g, "\n"));
      }
    }
    onDone();
  }).catch(onError);
}
```

- [ ] **Step 2: Add tag chip styles to `web/css/app.css`**

Append to `web/css/app.css`:

```css
/* ── Chat file tag picker ───────────────────────────────────────── */
.chat-tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 16px 0;
  min-height: 36px;
  align-items: center;
}

.chat-tag-label {
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 4px;
  white-space: nowrap;
  line-height: 26px;
}

.file-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px 3px 8px;
  border-radius: 99px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  user-select: none;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-tag:hover {
  border-color: var(--gold);
  color: var(--text);
}

.file-tag.active {
  border-color: var(--gold);
  background: rgba(200, 168, 80, 0.12);
  color: var(--gold);
}

.file-tag .tag-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.chat-scope-hint {
  font-size: 11px;
  color: var(--text-dim);
  padding: 2px 16px 4px;
  font-style: italic;
}
```

- [ ] **Step 3: Rewrite `web/js/tabs/chat.js`**

```js
import { getFiles, streamChat } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;
let _taggedSources = new Set();  // filenames currently tagged

// ── Tag picker ───────────────────────────────────────────────────

async function refreshTagPicker() {
  const row = document.getElementById("chat-tag-row");
  const hint = document.getElementById("chat-scope-hint");
  if (!row) return;

  let files = [];
  try { files = await getFiles(); } catch (_) { /* ignore */ }

  if (!files.length) {
    row.innerHTML = `<span class="chat-tag-label">No files uploaded</span>`;
    if (hint) hint.textContent = "";
    return;
  }

  row.innerHTML = `<span class="chat-tag-label">Scope:</span>` +
    files.map(f => {
      const active = _taggedSources.has(f.name) ? " active" : "";
      return `<button class="file-tag${active}" data-name="${f.name}" title="${f.name}">
        <span class="tag-dot"></span>${f.name}
      </button>`;
    }).join("");

  row.querySelectorAll(".file-tag").forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.name;
      if (_taggedSources.has(name)) {
        _taggedSources.delete(name);
        btn.classList.remove("active");
      } else {
        _taggedSources.add(name);
        btn.classList.add("active");
      }
      updateHint();
    });
  });

  updateHint();
}

function updateHint() {
  const hint = document.getElementById("chat-scope-hint");
  if (!hint) return;
  if (_taggedSources.size === 0) {
    hint.textContent = "Searching all uploaded contracts.";
  } else {
    const names = [..._taggedSources].join(", ");
    hint.textContent = `Scoped to: ${names}`;
  }
}

// ── Messages ─────────────────────────────────────────────────────

function scrollToBottom() {
  const el = document.getElementById("chat-messages");
  el.scrollTop = el.scrollHeight;
}

function renderMessage(role, content, streaming = false) {
  const el = document.getElementById("chat-messages");
  const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const avatar = role === "user" ? "U" : "⚖";
  el.insertAdjacentHTML("beforeend", `
    <div class="message ${role}" id="${id}">
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-bubble">${content}${streaming ? '<span class="cursor">&#9608;</span>' : ""}</div>
    </div>
  `);
  scrollToBottom();
  return id;
}

function updateMessage(id, content, streaming = false) {
  const bubble = document.querySelector(`#${id} .msg-bubble`);
  if (!bubble) return;
  bubble.innerHTML = content + (streaming ? '<span class="cursor">&#9608;</span>' : "");
  scrollToBottom();
}

// ── Init ─────────────────────────────────────────────────────────

export function initChat(toast) {
  _toast = toast;
  const input   = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

  refreshTagPicker();

  // Refresh tag picker when switching to chat tab (new files may have been uploaded)
  document.querySelector('[data-tab="chat"]').addEventListener("click", refreshTagPicker);

  function sendMessage() {
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    input.disabled = true;
    sendBtn.disabled = true;

    renderMessage("user", question);

    showLoader("Thinking…");
    const replyId = renderMessage("assistant", "", true);

    let fullAnswer = "";
    let loaderHidden = false;

    const sources = _taggedSources.size > 0 ? [..._taggedSources] : [];

    streamChat(
      question,
      sources,
      (chunk) => {
        if (!loaderHidden) { hideLoader(); loaderHidden = true; }
        fullAnswer += chunk;
        updateMessage(replyId, fullAnswer, true);
      },
      () => {
        if (!loaderHidden) { hideLoader(); loaderHidden = true; }
        updateMessage(replyId, fullAnswer, false);
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
      },
      (err) => {
        if (!loaderHidden) { hideLoader(); loaderHidden = true; }
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

- [ ] **Step 4: Add tag row + hint elements to `web/index.html`**

In `web/index.html`, replace the chat tab panel (lines 65–75):

```html
    <div id="tab-chat" class="tab-panel" role="tabpanel" aria-label="Chat">
      <h2 class="panel-title">Contract Q&amp;A</h2>
      <div class="chat-messages" id="chat-messages"></div>
      <div class="chat-tag-row" id="chat-tag-row" aria-label="Filter by file"></div>
      <div class="chat-scope-hint" id="chat-scope-hint"></div>
      <div class="chat-input-row">
        <input type="text" id="chat-input" placeholder="Ask about your contracts…" autocomplete="off">
        <button class="btn btn-primary" id="chat-send">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          Send
        </button>
      </div>
    </div>
```

- [ ] **Step 5: Smoke-test manually**

Start the server: `uvicorn backend.main:app --reload --port 8000`

- Open http://localhost:8000
- Upload 2 contracts on the Files tab
- Switch to Chat — tag chips should appear for both files
- Tag one file, ask a question — response should only cite that file's content
- Untag all, ask again — response may cite both files
- No console errors

- [ ] **Step 6: Commit**

```bash
git add web/js/api.js web/js/tabs/chat.js web/css/app.css web/index.html
git commit -m "feat: chat file tag picker — scope RAG queries to selected contracts"
```

---

### Task 3: Diff tab — per-slot inline upload

**Files:**
- Modify: `web/js/tabs/diff.js`
- Modify: `web/css/app.css`

The diff tab currently only allows picking from already-uploaded files. This task adds an inline "Upload new…" button to each selector slot. When a user uploads a file via the diff tab, it calls `POST /api/files/upload` (existing endpoint) so the file is ingested and visible in Files.

- [ ] **Step 1: Add diff upload slot styles to `web/css/app.css`**

Append:

```css
/* ── Diff upload slots ──────────────────────────────────────────── */
.diff-slot {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.diff-slot label {
  font-size: 12px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.diff-slot-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.diff-slot-controls select {
  flex: 1;
  min-width: 0;
}

.diff-upload-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 6px 10px;
  white-space: nowrap;
}

.diff-upload-input {
  display: none;
}
```

- [ ] **Step 2: Rewrite `web/js/tabs/diff.js`**

```js
import { getFiles, uploadFile, getDiff } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

// ── Slot builder ─────────────────────────────────────────────────

function buildSlot(id, labelText, names, defaultIndex) {
  const opts = names.map((n, i) =>
    `<option value="${n}"${i === defaultIndex ? " selected" : ""}>${n}</option>`
  ).join("");

  return `
    <div class="diff-slot">
      <label for="${id}">${labelText}</label>
      <div class="diff-slot-controls">
        <select id="${id}">${opts}</select>
        <label class="btn btn-secondary diff-upload-btn" title="Upload a new contract for this slot">
          Upload new
          <input class="diff-upload-input" type="file" accept=".pdf,.docx,.txt" aria-label="Upload ${labelText}">
        </label>
      </div>
    </div>
  `;
}

function buildSelectors(files) {
  const names = files.map(f => f.name);
  if (names.length === 0) {
    return `<div class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-dim)" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      <p>Upload at least one contract to compare, or use the Upload buttons below.</p>
    </div>
    <div class="card">
      <div class="diff-selectors">
        ${buildSlot("diff-a", "Base contract", [], -1).replace("<select", "<select disabled").replace("<option", "")}
        ${buildSlot("diff-b", "Compare contract", [], -1).replace("<select", "<select disabled").replace("<option", "")}
        <button class="btn btn-primary" id="diff-btn" disabled>Compare</button>
      </div>
    </div>
    <div id="diff-result"></div>`;
  }

  return `
    <div class="card">
      <div class="diff-selectors">
        ${buildSlot("diff-a", "Base contract", names, 0)}
        ${buildSlot("diff-b", "Compare contract", names, Math.min(1, names.length - 1))}
        <button class="btn btn-primary" id="diff-btn">Compare</button>
      </div>
    </div>
    <div id="diff-result"></div>
  `;
}

// ── Diff renderer (unchanged logic) ──────────────────────────────

const CTX = 3;

function renderDiff(hunks) {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }
  const added   = hunks.filter(h => h.type === "added").length;
  const removed = hunks.filter(h => h.type === "removed").length;

  let lines = "";
  let ctxBuf = [];

  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      ctxBuf.forEach(h => { lines += hunkHtml(h); });
    } else {
      ctxBuf.slice(0, CTX).forEach(h => { lines += hunkHtml(h); });
      lines += `<div class="diff-line ellipsis"><span style="padding:0 8px;color:var(--text-dim)">&#8230;</span></div>`;
      ctxBuf.slice(-CTX).forEach(h => { lines += hunkHtml(h); });
    }
    ctxBuf = [];
  }

  for (const h of hunks) {
    if (h.type === "context") { ctxBuf.push(h); }
    else { flushCtx(); lines += hunkHtml(h); }
  }
  flushCtx();

  return `
    <div class="diff-stats">
      <span class="add">+${added} additions</span> &nbsp;
      <span class="rem">&#8722;${removed} removals</span>
    </div>
    <div class="diff-viewer">${lines}</div>
  `;
}

function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}

function hunkHtml(h) {
  const prefix = h.type === "added" ? "+" : h.type === "removed" ? "&#8722;" : "&nbsp;";
  const la = h.line_a ?? "";
  const lb = h.line_b ?? "";
  return `<div class="diff-line ${h.type}">
    <span class="diff-gutter">${la}</span>
    <span class="diff-gutter">${lb}</span>
    <span class="diff-prefix">${prefix}</span>
    <span class="diff-text">${esc(h.text)}</span>
  </div>`;
}

// ── Init ─────────────────────────────────────────────────────────

export async function initDiff(toast) {
  _toast = toast;
  const container = document.getElementById("diff-content");

  async function render() {
    const files = await getFiles();
    container.innerHTML = buildSelectors(files);

    // Wire upload inputs for each slot
    ["diff-a", "diff-b"].forEach(slotId => {
      const slotEl = container.querySelector(`#${slotId}`)?.closest(".diff-slot");
      if (!slotEl) return;
      const fileInput = slotEl.querySelector(".diff-upload-input");
      if (!fileInput) return;

      fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];
        if (!file) return;
        showLoader(`Ingesting ${file.name}\u2026`);
        try {
          await uploadFile(file);
          _toast(`${file.name} uploaded.`, "success");
        } catch(e) {
          _toast(`Upload failed: ${e.message || e}`, "error");
          hideLoader();
          return;
        }
        hideLoader();
        // Re-render selectors with updated file list, then select the new file
        const updated = await getFiles();
        container.innerHTML = buildSelectors(updated);
        rewireAfterRender();  // re-attach all listeners after re-render
        // Select the just-uploaded file in this slot
        const select = document.getElementById(slotId);
        if (select) select.value = file.name;
      });
    });

    rewireAfterRender();
  }

  function rewireAfterRender() {
    // Wire upload inputs again (called after re-renders too)
    ["diff-a", "diff-b"].forEach(slotId => {
      const slotEl = container.querySelector(`#${slotId}`)?.closest(".diff-slot");
      if (!slotEl) return;
      const fileInput = slotEl.querySelector(".diff-upload-input");
      if (!fileInput) return;

      // Remove old listener by cloning
      const fresh = fileInput.cloneNode(true);
      fileInput.replaceWith(fresh);

      fresh.addEventListener("change", async () => {
        const file = fresh.files[0];
        if (!file) return;
        showLoader(`Ingesting ${file.name}\u2026`);
        try {
          await uploadFile(file);
          _toast(`${file.name} uploaded.`, "success");
        } catch(e) {
          _toast(`Upload failed: ${e.message || e}`, "error");
          hideLoader();
          return;
        }
        hideLoader();
        const updated = await getFiles();
        container.innerHTML = buildSelectors(updated);
        rewireAfterRender();
        const select = document.getElementById(slotId);
        if (select) select.value = file.name;
      });
    });

    // Wire compare button
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
      } catch(e) {
        _toast(String(e), "error");
      } finally {
        hideLoader();
      }
    });
  }

  await render();
  document.querySelector('[data-tab="diff"]').addEventListener("click", render);
}
```

- [ ] **Step 3: Smoke-test manually**

Start the server: `uvicorn backend.main:app --reload --port 8000`

- Open http://localhost:8000
- Go to Diff tab with 0 files — should show descriptive empty state with Upload buttons still visible
- Click "Upload new" on Base slot — upload a PDF — it should ingest, appear in Files tab, and be selected in the Base slot selector
- Click "Upload new" on Compare slot — upload a second PDF
- Click Compare — diff renders correctly
- Go back to Files tab — both uploaded files appear in the list
- Go back to Diff tab — both files still present in selectors

- [ ] **Step 4: Commit**

```bash
git add web/js/tabs/diff.js web/css/app.css
git commit -m "feat: diff tab per-slot inline upload — new files visible in Files page"
```

---

### Task 4: Push

- [ ] **Step 1: Run full test suite**

```
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Push to GitHub**

```bash
git push origin master
```

---

## Self-Review

**Spec coverage:**

| Requirement | Covered by |
|---|---|
| Chat: tag files from Files page | Task 2 — tag picker strip |
| Chat: tagged → filter FAISS to those docs | Task 1 — retriever filter + chain + API |
| Chat: untagged → full vector store | Task 1 — `sources=None` path |
| Diff: upload 1 or both docs inline | Task 3 — per-slot Upload button |
| Diff: use already-uploaded docs | Task 3 — select dropdown (existing behaviour preserved) |
| Uploads from diff visible in Files | Task 3 — calls existing `/api/files/upload`; Task 1 doesn't change file_manager |

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:** `sources` is `list[str] | None` throughout Python; `string[]` in JS. `streamChat` signature change (added `sources` as 2nd param) is consistent across api.js → chat.js call site.

**Edge cases handled:**
- Empty `sources` list from JS → treated as `None` in API (`body.get("sources") or None`) → full index query
- 0 files in diff tab → selects are disabled but upload inputs still work
- Uploading same filename twice → `file_manager.save_file` deduplicates by name (existing behaviour)
- Slot re-render after upload clones `input` elements to avoid duplicate event listeners
