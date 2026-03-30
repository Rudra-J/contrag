import streamlit as st

st.set_page_config(
    page_title="Contrag",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Global dark theme overrides
st.markdown("""
<style>
/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #333;
}
.stTabs [data-baseweb="tab"] {
    padding: 8px 20px;
    font-weight: 500;
    border-radius: 6px 6px 0 0;
}
/* Subtle brand header */
.contrag-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0.5rem 0 1.5rem 0;
    border-bottom: 1px solid #333;
    margin-bottom: 1.5rem;
}
.contrag-title {
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    font-family: serif;
}
.contrag-subtitle {
    font-size: 0.85rem;
    color: #888;
    margin-top: 2px;
}
</style>
<div class="contrag-header">
  <span style="font-size:2rem">⚖️</span>
  <div>
    <div class="contrag-title">Contrag</div>
    <div class="contrag-subtitle">Contract Intelligence — RAG · Diff · Glossary</div>
  </div>
</div>
""", unsafe_allow_html=True)

from ui import tab_files, tab_chat, tab_diff, tab_glossary

tab1, tab2, tab3, tab4 = st.tabs(["📁 Files", "💬 Chat", "🔀 Diff", "📖 Glossary"])

with tab1:
    tab_files.render()

with tab2:
    tab_chat.render()

with tab3:
    tab_diff.render()

with tab4:
    tab_glossary.render()
