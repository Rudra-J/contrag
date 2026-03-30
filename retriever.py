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
