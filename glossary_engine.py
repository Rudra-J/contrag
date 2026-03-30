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
