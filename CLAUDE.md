# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Contrag** is a legal contract analysis platform. Users upload contracts (PDF, DOCX, TXT), chat with them via RAG, compare contracts with diff analysis, and browse an auto-extracted legal glossary.

## Running the Application

**Prerequisites:** Ollama must be running locally with the `llama3.2` model pulled.

```bash
# Start the backend (from repo root)
cd backend
python -m uvicorn main:app --reload
```

The frontend is served statically by FastAPI — no build step. Visit `http://localhost:8000`.

## Running Tests

```bash
# All tests
pytest

# Single test file
pytest tests/test_diff_risk.py

# Single test
pytest tests/test_diff_risk.py::test_function_name
```

Tests mock `ChatOllama` — no real Ollama instance needed for tests.

## Architecture

### Backend Modules

| File | Responsibility |
|------|---------------|
| `backend/main.py` | FastAPI app, all API routes, FAISS integration |
| `chain.py` | LangChain RAG chain (Ollama llama3.2, k=5 retrieval) |
| `retriever.py` | FAISS retrieval with optional source-file filtering |
| `ingest.py` | Document ingestion: text extraction → chunking → embedding → FAISS |
| `file_manager.py` | Upload/delete/metadata management (`data/files_meta.json`) |
| `diff_engine.py` | Text-based contract diff (unified diff algorithm) |
| `glossary_engine.py` | LLM-powered legal term extraction → `data/glossary.json` |

### Data Flow

1. **Upload:** File → `unstructured` extraction → clause-aware chunking (800 chars, 100 overlap) → `BAAI/bge-small-en-v1.5` embeddings → FAISS index on disk + background glossary extraction
2. **Chat:** Query → FAISS retrieval (optionally filtered by source contract) → Ollama llama3.2 → SSE stream to browser
3. **Diff:** Two contract texts → unified diff → optional LLM risk classification per changed block → JSON response
4. **Glossary:** Auto-extracted per chunk at upload time; browsable/searchable in UI

### Frontend (`web/`)

Vanilla JS with ES modules — no build tooling. Single-page app with four tabs:
- **Files** (`tabs/files.js`) — upload, list, delete contracts
- **Chat** (`tabs/chat.js`) — RAG chat with source filtering, SSE streaming
- **Diff** (`tabs/diff.js`) — compare two contracts; renders in 4 modes via `diff-renderers.js`
- **Glossary** (`tabs/glossary.js`) — browse extracted legal terms

### Diff Visualization Modes (`web/js/diff-renderers.js`)

Four rendering modes: Unified, Side-by-Side, Redline, Risk Analysis. The Risk Analysis mode calls `/api/diff/risk` which sends changed blocks to Ollama for classification.

### Persistent State

- `faiss_index/` — vector store (grows with each upload, excluded from git)
- `data/files_meta.json` — upload metadata
- `data/glossary.json` — extracted legal terms

## Test Patterns

All tests patch `ChatOllama` and use FastAPI's `TestClient`:

```python
fake_llm = MagicMock()
fake_llm.invoke.return_value.content = '{"terms": [...]}'
with patch("main.ChatOllama", return_value=fake_llm):
    client = TestClient(app)
    resp = client.post("/api/endpoint", json=body)
```

## Key Constraints

- **Ollama model:** `llama3.2` — hardcoded in `chain.py` and `backend/main.py`
- **Embeddings:** CPU-only (`BAAI/bge-small-en-v1.5`) — slow on large documents
- **Clause chunking:** Uses hardcoded markers (numbered sections, "WHEREAS", "ARTICLE", etc.) in `ingest.py`
