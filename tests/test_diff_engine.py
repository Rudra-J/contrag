import diff_engine

def test_extract_text_from_txt(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello\nWorld\n")
    lines = diff_engine.extract_lines(str(f))
    assert lines == ["Hello\n", "World\n"]

def test_compute_diff_returns_hunks():
    a = ["line1\n", "line2\n", "line3\n"]
    b = ["line1\n", "line2 modified\n", "line3\n"]
    hunks = diff_engine.compute_diff(a, b, "a.pdf", "b.pdf")
    assert any(h["type"] == "removed" for h in hunks)
    assert any(h["type"] == "added" for h in hunks)

def test_compute_diff_context_lines():
    a = ["line1\n", "line2\n", "line3\n"]
    b = ["line1\n", "line2\n", "line3\n"]
    hunks = diff_engine.compute_diff(a, b, "a.pdf", "b.pdf")
    assert all(h["type"] == "context" for h in hunks) or hunks == []
