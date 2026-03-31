"""
Generate a synthetic evaluation dataset from ingested FAISS chunks.

Run once (or whenever new contracts are uploaded):
    python eval/generate_dataset.py

Reads all chunks from faiss_index/, asks llama3.2 to write 3 questions per chunk
that the chunk directly answers, and saves to eval/dataset.json.
"""

import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama

STORE_PATH   = "faiss_index"
OUT_PATH     = "eval/dataset.json"
QUESTIONS_PER_CHUNK = 3
MODEL        = "llama3.2"

EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

_PROMPT = """\
You are building a test dataset for a legal contract retrieval system.
Given the contract clause below, write exactly {n} questions that this clause \
and only this clause directly answers.
Questions must be specific enough that retrieving this exact clause would be \
essential to answer them.
Return ONLY a valid JSON array of {n} strings — no markdown, no explanation.

CONTRACT CLAUSE:
{chunk}
"""

def _parse_json_array(text: str) -> list:
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


def main():
    if not os.path.exists(STORE_PATH):
        print("ERROR: faiss_index/ not found. Upload at least one contract first.")
        sys.exit(1)

    print("Loading FAISS index...")
    db   = FAISS.load_local(STORE_PATH, EMBEDDINGS, allow_dangerous_deserialization=True)
    docs = list(db.docstore._dict.values())
    # Filter out very short fragments
    docs = [d for d in docs if len(d.page_content.strip()) >= 80]
    print(f"Found {len(docs)} chunks across all ingested contracts.\n")

    llm     = ChatOllama(model=MODEL, temperature=0)
    dataset = []

    for i, doc in enumerate(docs):
        chunk_text = doc.page_content.strip()
        source     = doc.metadata.get("source", "unknown")
        print(f"[{i+1:3}/{len(docs)}] {source} — chunk {i}", end=" ", flush=True)

        try:
            prompt    = _PROMPT.format(n=QUESTIONS_PER_CHUNK, chunk=chunk_text)
            response  = llm.invoke(prompt)
            questions = _parse_json_array(response.content)

            if not isinstance(questions, list):
                print("(skipped — not a list)")
                continue

            added = 0
            for q in questions[:QUESTIONS_PER_CHUNK]:
                if isinstance(q, str) and q.strip():
                    dataset.append({
                        "question":    q.strip(),
                        "source_chunk": chunk_text,
                        "source_file": source,
                        "chunk_index": i,
                    })
                    added += 1
            print(f"-> {added} questions")

        except Exception as e:
            print(f"(skipped — {e})")

    os.makedirs("eval", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"\nDataset written to {OUT_PATH}")
    print(f"Total questions : {len(dataset)}  ({len(docs)} chunks × {QUESTIONS_PER_CHUNK})")


if __name__ == "__main__":
    main()
