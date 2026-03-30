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

def build_chain():
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)
    retriever = get_retriever()
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )

def ask(question: str) -> str:
    return build_chain().invoke(question)

def ask_stream(question: str):
    for chunk in build_chain().stream(question):
        yield chunk