def test_get_retriever_with_sources_passes_filter(monkeypatch):
    """get_retriever with sources= sets a filter on the FAISS retriever."""
    from unittest.mock import MagicMock, patch

    fake_db = MagicMock()
    fake_db.as_retriever.return_value = MagicMock()

    with patch("retriever.os.path.exists", return_value=True), \
         patch("retriever.FAISS.load_local", return_value=fake_db):
        from retriever import get_retriever
        get_retriever(sources=["contract_a.pdf"])

    call_kwargs = fake_db.as_retriever.call_args[1]["search_kwargs"]
    assert "filter" in call_kwargs
    filter_fn = call_kwargs["filter"]
    assert filter_fn({"source": "contract_a.pdf"}) is True
    assert filter_fn({"source": "contract_b.pdf"}) is False


def test_get_retriever_no_sources_no_filter(monkeypatch):
    """get_retriever with no sources sets no filter."""
    from unittest.mock import MagicMock, patch

    fake_db = MagicMock()
    with patch("retriever.os.path.exists", return_value=True), \
         patch("retriever.FAISS.load_local", return_value=fake_db):
        from retriever import get_retriever
        get_retriever()

    call_kwargs = fake_db.as_retriever.call_args[1]["search_kwargs"]
    assert "filter" not in call_kwargs
