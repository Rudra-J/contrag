import streamlit as st
import file_manager
import diff_engine
from ui.justice_loader import get_justice_loader_html

_CONTEXT_LINES = 3  # unchanged lines to show around each change

def _render_diff(hunks: list[dict]):
    """Render diff hunks as styled HTML blocks."""
    # Group hunks; collapse long context runs
    lines_html = []
    context_buffer = []

    def flush_context():
        if len(context_buffer) <= _CONTEXT_LINES * 2:
            for h in context_buffer:
                lines_html.append(_hunk_html(h))
        else:
            for h in context_buffer[:_CONTEXT_LINES]:
                lines_html.append(_hunk_html(h))
            lines_html.append(
                '<div style="color:#888;padding:2px 8px;font-family:monospace;font-size:0.8rem">…</div>'
            )
            for h in context_buffer[-_CONTEXT_LINES:]:
                lines_html.append(_hunk_html(h))
        context_buffer.clear()

    for h in hunks:
        if h["type"] == "context":
            context_buffer.append(h)
        else:
            flush_context()
            lines_html.append(_hunk_html(h))

    flush_context()

    html = (
        '<div style="font-family:monospace;font-size:0.85rem;border:1px solid #333;'
        'border-radius:6px;overflow:hidden;background:#1e1e1e">'
        + "".join(lines_html)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

def _hunk_html(h: dict) -> str:
    text = h["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    line_a = h["line_a"] or ""
    line_b = h["line_b"] or ""
    if h["type"] == "added":
        bg, prefix, color = "#1a3a1a", "+", "#6dbf67"
    elif h["type"] == "removed":
        bg, prefix, color = "#3a1a1a", "−", "#bf6767"
    else:
        bg, prefix, color = "transparent", " ", "#888"
    return (
        f'<div style="background:{bg};padding:1px 8px;display:flex;gap:8px">'
        f'<span style="color:#555;min-width:36px;text-align:right;user-select:none">{line_a}</span>'
        f'<span style="color:#555;min-width:36px;text-align:right;user-select:none">{line_b}</span>'
        f'<span style="color:{color};white-space:pre-wrap">{prefix} {text}</span>'
        f'</div>'
    )

def render():
    st.subheader("Contract Diff")
    files = file_manager.list_files()
    names = [m["name"] for m in files]

    if len(names) < 2:
        st.info("Upload at least 2 contracts to compare.")
        return

    col1, col2 = st.columns(2)
    a = col1.selectbox("Base contract", names, key="diff_a")
    b = col2.selectbox("Compare contract", [n for n in names if n != a], key="diff_b")

    if st.button("Compare", type="primary"):
        loader = st.empty()
        loader.markdown(get_justice_loader_html(), unsafe_allow_html=True)
        path_a = file_manager.get_file_path(a)
        path_b = file_manager.get_file_path(b)
        try:
            hunks = diff_engine.diff_contracts(path_a, path_b, a, b)
            loader.empty()
            added = sum(1 for h in hunks if h["type"] == "added")
            removed = sum(1 for h in hunks if h["type"] == "removed")
            st.caption(f"+{added} additions · −{removed} removals")
            _render_diff(hunks)
        except Exception as e:
            loader.empty()
            st.error(str(e))
