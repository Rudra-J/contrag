import streamlit as st
import file_manager
import ingest

def render():
    st.subheader("Contract Files")

    # Upload section
    st.markdown("#### Upload Contracts")
    uploaded = st.file_uploader(
        "Upload PDF or DOCX contracts",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="files_tab_uploader"
    )
    if uploaded:
        for f in uploaded:
            with st.spinner(f"Ingesting {f.name}..."):
                path = file_manager.save_file(f.name, f.read())
                try:
                    ingest.ingest(path)
                    st.success(f"{f.name} ingested successfully.")
                except Exception as e:
                    st.error(f"Failed to ingest {f.name}: {e}")
        st.rerun()

    # File tree
    st.markdown("#### Uploaded Files")
    files = file_manager.list_files()
    if not files:
        st.info("No contracts uploaded yet.")
        return

    for meta in files:
        col1, col2, col3 = st.columns([5, 2, 1])
        col1.markdown(f"📄 **{meta['name']}**")
        col2.caption(f"{meta['size_kb']} KB · {meta['uploaded_at'][:10]}")
        if col3.button("🗑", key=f"del_{meta['name']}", help=f"Remove {meta['name']}"):
            file_manager.remove_file(meta["name"])
            st.rerun()
