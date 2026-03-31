# tests/test_diff_risk.py
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


def _client():
    sys.modules.pop("main", None)
    from main import app
    return TestClient(app)


SAMPLE_HUNKS = [
    {"type": "context",  "text": "Preamble text.", "line_a": 1, "line_b": 1},
    {"type": "removed",  "text": "Payment due in 30 days.", "line_a": 2, "line_b": None},
    {"type": "added",    "text": "Payment due in 14 days.", "line_a": None, "line_b": 2},
    {"type": "context",  "text": "End clause.", "line_a": 3, "line_b": 3},
]

MOCK_LLM_JSON = json.dumps({
    "summary": "Payment deadline tightened from 30 to 14 days.",
    "changes": [{"index": 0, "risk": "risk_increase", "explanation": "Shorter payment window."}]
})


def test_risk_returns_summary_and_changes():
    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = MOCK_LLM_JSON
    client = _client()

    with patch("main.ChatOllama", return_value=fake_llm):
        resp = client.post("/api/diff/risk", json={
            "hunks": SAMPLE_HUNKS,
            "name_a": "base.pdf",
            "name_b": "compare.pdf",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert isinstance(data["changes"], list)
    assert data["changes"][0]["risk"] == "risk_increase"


def test_risk_handles_llm_markdown_fences():
    """LLM sometimes wraps JSON in ```json ... ``` — strip it."""
    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = f"```json\n{MOCK_LLM_JSON}\n```"
    client = _client()

    with patch("main.ChatOllama", return_value=fake_llm):
        resp = client.post("/api/diff/risk", json={
            "hunks": SAMPLE_HUNKS,
            "name_a": "a.pdf",
            "name_b": "b.pdf",
        })

    assert resp.status_code == 200
    assert resp.json()["summary"] != ""


def test_risk_rejects_missing_hunks():
    client = _client()
    resp = client.post("/api/diff/risk", json={"name_a": "a.pdf", "name_b": "b.pdf"})
    assert resp.status_code == 400


def test_risk_returns_empty_changes_for_identical_contracts():
    """If all hunks are context, no LLM call is made — return empty changes immediately."""
    context_only = [
        {"type": "context", "text": "Same line.", "line_a": 1, "line_b": 1},
    ]
    fake_llm = MagicMock()

    client = _client()
    with patch("main.ChatOllama", return_value=fake_llm):
        resp = client.post("/api/diff/risk", json={
            "hunks": context_only, "name_a": "a.pdf", "name_b": "b.pdf"
        })

    assert resp.status_code == 200
    assert resp.json()["changes"] == []
    fake_llm.invoke.assert_not_called()


def test_risk_returns_500_on_invalid_llm_json():
    """LLM returns non-JSON — endpoint must return 500."""
    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = "Sorry, I cannot help with that."

    client = _client()
    with patch("main.ChatOllama", return_value=fake_llm):
        resp = client.post("/api/diff/risk", json={
            "hunks": SAMPLE_HUNKS,
            "name_a": "a.pdf",
            "name_b": "b.pdf",
        })

    assert resp.status_code == 500
