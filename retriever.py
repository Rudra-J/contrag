import time
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

def get_retriever(store_path: str = "faiss_index", k: int = 5, sources: list | None = None):
    if not os.path.exists(store_path):
        raise FileNotFoundError("No contracts ingested yet. Upload a contract first.")
    db = FAISS.load_local(store_path, EMBEDDINGS,
                          allow_dangerous_deserialization=True)
    search_kwargs = {"k": k, "fetch_k": k * 4}
    if sources is not None:
        source_set = set(sources)
        search_kwargs["filter"] = lambda meta: meta.get("source") in source_set
    # MMR balances relevance with diversity, reducing repetitive clause chunks
    return db.as_retriever(search_type="mmr", search_kwargs=search_kwargs)


def retrieve_with_metrics(question: str, store_path: str = "faiss_index",
                          k: int = 5, sources: list | None = None) -> dict:
    """Return retrieved docs plus retrieval timing and provenance metadata."""
    t0 = time.time()
    retriever = get_retriever(store_path=store_path, k=k, sources=sources)
    docs = retriever.invoke(question)
    elapsed_ms = round((time.time() - t0) * 1000)

    # Deduplicate by content hash (guards against duplicate ingestion)
    seen, unique_docs = set(), []
    for d in docs:
        key = d.page_content.strip()
        if key not in seen:
            seen.add(key)
            unique_docs.append(d)

    return {
        "docs": unique_docs,
        "metrics": {
            "retrieval_ms": elapsed_ms,
            "chunks_retrieved": len(unique_docs),
            "chunks_before_dedup": len(docs),
            "sources": sorted({d.metadata.get("source", "unknown") for d in unique_docs}),
        }
    }
