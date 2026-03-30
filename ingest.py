from unstructured.partition.auto import partition
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

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