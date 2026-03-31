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
| `chain.py` | LangChain RAG chain (Ollama llama3.2); logs time-to-first-token and generation time |
| `retriever.py` | MMR retrieval with source filtering and content deduplication; `retrieve_with_metrics()` returns timing + chunk stats |
| `ingest.py` | Document ingestion: text extraction → chunking → embedding → FAISS |
| `file_manager.py` | Upload/delete/metadata management (`data/files_meta.json`) |
| `diff_engine.py` | Text-based contract diff (unified diff algorithm) |
| `glossary_engine.py` | LLM-powered legal term extraction → `data/glossary.json` |

### Data Flow

1. **Upload:** File → `unstructured` extraction → clause-aware chunking (800 chars, 100 overlap) → `BAAI/bge-small-en-v1.5` embeddings (~27 chunks/sec on CPU) → FAISS index on disk + background glossary extraction
2. **Chat:** Query → MMR retrieval (k=5, fetch_k=20, optionally filtered by source) → content deduplication → Ollama llama3.2 → SSE stream to browser
3. **Diff:** Two contract texts → unified diff → optional LLM risk classification per changed block → JSON response with `clause_type`, `severity`, and `mitigation` per change
4. **Glossary:** Auto-extracted per chunk at upload time; browsable/searchable in UI

### Retrieval Design

- **Chunking:** `RecursiveCharacterTextSplitter` with clause markers (`\nARTICLE`, `\nSECTION`, `\nWHEREAS`, etc.) as preferred split points; 800-char chunks, 100-char overlap
- **Retrieval:** MMR (`search_type="mmr"`, `fetch_k = k * 4`) for diversity — prevents boilerplate chunks from dominating context
- **Deduplication:** Content-hash dedup in both `format_docs` (chain.py) and `retrieve_with_metrics` (retriever.py)
- **Metrics:** `retrieve_with_metrics()` returns `retrieval_ms`, `chunks_retrieved`, `chunks_before_dedup`, `sources`; logged to console on every chat request

### Frontend (`web/`)

Vanilla JS with ES modules — no build tooling. Single-page app with four tabs:
- **Files** (`tabs/files.js`) — upload, list, delete contracts
- **Chat** (`tabs/chat.js`) — RAG chat with source filtering, SSE streaming
- **Diff** (`tabs/diff.js`) — compare two contracts; renders in 4 modes via `diff-renderers.js`
- **Glossary** (`tabs/glossary.js`) — browse extracted legal terms

### Diff Visualization Modes (`web/js/diff-renderers.js`)

Four rendering modes: Unified, Side-by-Side, Redline, Risk Analysis. The Risk Analysis mode calls `/api/diff/risk` which classifies each change block with `clause_type` (10 categories), `risk` direction, `severity` (high/medium/low), `explanation`, and `mitigation`.

### API Response Shapes

`POST /api/chat/context` returns:
```json
{
  "docs": [{"source": "file.pdf", "text": "..."}],
  "metrics": {"retrieval_ms": 55, "chunks_retrieved": 5, "chunks_before_dedup": 5, "sources": ["file.pdf"]}
}
```

`POST /api/diff/risk` returns:
```json
{
  "summary": "...",
  "changes": [{"index": 0, "clause_type": "governing_law", "risk": "risk_increase", "severity": "high", "explanation": "...", "mitigation": "..."}]
}
```

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
- **Embeddings:** CPU-only (`BAAI/bge-small-en-v1.5`) — ~27 chunks/sec, 37ms/chunk on typical hardware
- **Clause chunking:** Uses hardcoded markers (numbered sections, "WHEREAS", "ARTICLE", etc.) in `ingest.py`
- **Risk analysis clause categories:** `payment_terms`, `liability`, `indemnification`, `ip_ownership`, `termination`, `governing_law`, `confidentiality`, `representations`, `force_majeure`, `other` — defined in `_RISK_SYSTEM` in `backend/main.py`
