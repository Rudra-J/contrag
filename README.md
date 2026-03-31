# Contrag

A local-first legal contract analysis platform. Upload contracts, chat with them using RAG, compare versions with diff analysis, and browse an auto-extracted legal glossary — all powered by a local LLM via Ollama.

## Features

- **Contract Chat** — Ask questions about your contracts using retrieval-augmented generation. Filter responses to specific source documents.
- **Diff Analysis** — Compare two contracts side-by-side with four visualization modes: Unified, Side-by-Side, Redline, and Risk Analysis (LLM-powered risk classification per change block).
- **Legal Glossary** — Legal terms are automatically extracted from uploaded contracts and stored in a searchable glossary.
- **Multi-format Support** — Upload PDF, DOCX, or TXT contracts.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) running locally with the `llama3.2` model

```bash
ollama pull llama3.2
```

## Setup

```bash
git clone https://github.com/Rudra-J/contrag.git
cd contrag
python -m venv venv
venv/Scripts/activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

## Running

```bash
cd backend
python -m uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

## How It Works

Uploaded contracts are chunked, embedded with `BAAI/bge-small-en-v1.5`, and stored in a FAISS vector index on disk. Chat queries retrieve the most relevant chunks and pass them as context to `llama3.2` via Ollama, with responses streamed to the browser via SSE.

The diff engine computes a unified diff between two contracts. The Risk Analysis mode sends each changed block to the LLM for classification: `risk_increase`, `risk_decrease`, or `neutral`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, LangChain, Ollama |
| LLM | llama3.2 (local via Ollama) |
| Embeddings | BAAI/bge-small-en-v1.5 (CPU) |
| Vector store | FAISS |
| Frontend | Vanilla JS, HTML/CSS |
| Document parsing | Unstructured |

## Running Tests

```bash
pytest
```
