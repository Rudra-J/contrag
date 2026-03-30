import streamlit as st
import glossary_engine

def render():
    st.subheader("Legal Glossary")
    glossary = glossary_engine.load_glossary()

    if not glossary:
        st.info("No glossary terms yet. Upload and ingest a contract to auto-populate.")
        return

    # Search / filter
    search = st.text_input("Search terms", placeholder="e.g. indemnity, force majeure…")
    terms = sorted(glossary.keys())
    if search:
        terms = [t for t in terms if search.lower() in t]

    if not terms:
        st.warning("No matching terms found.")
        return

    st.caption(f"{len(terms)} term(s) found")

    for term in terms:
        entry = glossary[term]
        with st.expander(f"**{term.title()}**", expanded=False):
            st.markdown(f"**Legal definition:** {entry['legal']}")
            st.markdown(f"**Plain English:** {entry['layman']}")
            st.markdown(f"**Example:** _{entry['example']}_")

            st.markdown("**Sources:**")
            for src in entry.get("sources", []):
                file_name = src["file"]
                chunk_text = src.get("chunk", "")
                chunk_index = src.get("chunk_index", 0)
                # Clickable source — expands to show the exact excerpt
                with st.expander(f"📄 {file_name} · chunk #{chunk_index}", expanded=False):
                    # Highlight the term within the chunk
                    highlighted = chunk_text.replace(
                        term,
                        f'<mark style="background:#c8a85044;border-radius:3px">{term}</mark>'
                    )
                    st.markdown(
                        f'<div style="background:#1e1e1e;padding:10px;border-radius:6px;'
                        f'font-family:monospace;font-size:0.85rem;line-height:1.5">{highlighted}</div>',
                        unsafe_allow_html=True
                    )
