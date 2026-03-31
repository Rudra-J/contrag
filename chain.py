import time
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from retriever import get_retriever

OLLAMA_MODEL = "llama3.2"

PROMPT = ChatPromptTemplate.from_template("""You are a legal contract analyst.
Answer the question using ONLY the contract clauses below.
Follow these rules strictly:

1. Quote or paraphrase ONLY what is explicitly written. Do not infer relationships,
   draw conclusions, or fill in gaps — even if they seem obvious.
2. If a field appears blank or contains a placeholder (e.g. underscores, empty lines),
   state that it is not filled in. Do not guess the value.
3. If clauses from multiple contracts are provided, keep each contract's information
   separate. Never mix facts from different source files.
4. Cite every claim with its source: [Clause from: filename, Section X].
5. If the answer is not found in the clauses, respond with exactly:
   "This is not addressed in the uploaded contracts."

CONTRACT CLAUSES:
{context}

QUESTION: {question}

ANSWER:""")

def format_docs(docs):
    # Deduplicate by content to avoid repeating overlapping chunks
    seen, unique = set(), []
    for d in docs:
        key = d.page_content.strip()
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return "\n\n---\n\n".join(
        f"[Clause from: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
        for d in unique
    )

def build_chain(sources: list | None = None):
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)
    retriever = get_retriever(sources=sources)
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )

def ask(question: str, sources: list | None = None) -> str:
    return build_chain(sources=sources).invoke(question)

def ask_stream(question: str, sources: list | None = None):
    t0 = time.time()
    first_token = True
    for chunk in build_chain(sources=sources).stream(question):
        if first_token:
            ttft_ms = round((time.time() - t0) * 1000)
            print(f"[metrics] time_to_first_token={ttft_ms}ms")
            first_token = False
        yield chunk
    total_ms = round((time.time() - t0) * 1000)
    print(f"[metrics] generation_total_ms={total_ms}ms")
