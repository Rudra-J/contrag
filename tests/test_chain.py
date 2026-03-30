# tests/test_chain.py
from unittest.mock import MagicMock, patch
import sys


def test_ask_stream_passes_sources_to_retriever():
    """ask_stream with sources= passes them to build_chain."""
    # Remove cached chain module so patch applies cleanly
    sys.modules.pop("chain", None)

    captured = {}

    def fake_build_chain(sources=None):
        captured["sources"] = sources
        fake_chain = MagicMock()
        fake_chain.stream.return_value = iter(["Hello"])
        return fake_chain

    with patch("chain.build_chain", side_effect=fake_build_chain):
        from chain import ask_stream
        list(ask_stream("test question", sources=["a.pdf"]))

    assert captured.get("sources") == ["a.pdf"]


def test_ask_stream_no_sources_uses_full_index():
    """ask_stream with no sources passes sources=None to get_retriever."""
    # Remove cached chain module so patch applies cleanly
    sys.modules.pop("chain", None)

    captured = {}

    def fake_build_chain(sources=None):
        captured["sources"] = sources
        fake_chain = MagicMock()
        fake_chain.stream.return_value = iter(["Hello"])
        return fake_chain

    with patch("chain.build_chain", side_effect=fake_build_chain):
        from chain import ask_stream
        list(ask_stream("test question"))

    assert captured.get("sources") is None
