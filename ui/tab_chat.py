import streamlit as st
import file_manager
import ingest
from chain import ask_stream
from ui.justice_loader import get_justice_loader_html

def render():
    st.subheader("Contract Q&A")

    # Inline upload
    with st.expander("Upload a contract to chat about", expanded=False):
        f = st.file_uploader("Upload PDF/DOCX/TXT", type=["pdf","docx","txt"], key="chat_uploader")
        if f:
            with st.spinner(f"Ingesting {f.name}..."):
                path = file_manager.save_file(f.name, f.read())
                try:
                    ingest.ingest(path)
                    st.success(f"{f.name} ready.")
                except Exception as e:
                    st.error(str(e))

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Ask about your contracts…")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            loader_placeholder = st.empty()
            loader_placeholder.markdown(get_justice_loader_html(), unsafe_allow_html=True)
            answer_placeholder = st.empty()
            full_answer = ""
            try:
                loader_placeholder.empty()
                for chunk in ask_stream(question):
                    full_answer += chunk
                    answer_placeholder.markdown(full_answer + "▌")
                answer_placeholder.markdown(full_answer)
            except FileNotFoundError:
                loader_placeholder.empty()
                answer_placeholder.warning("No contracts ingested yet. Upload a contract first.")
                full_answer = "No contracts ingested yet."

        st.session_state.messages.append({"role": "assistant", "content": full_answer})
