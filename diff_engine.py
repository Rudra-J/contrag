import difflib

def extract_lines(file_path: str) -> list[str]:
    """Extract text lines from a contract file (PDF, DOCX, TXT)."""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    # Lazy-load unstructured to avoid Windows python-magic issues
    from unstructured.partition.auto import partition
    elements = partition(filename=file_path)
    text = "\n".join(str(e) for e in elements if str(e).strip())
    return [line + "\n" for line in text.splitlines()]

def compute_diff(lines_a: list[str], lines_b: list[str], name_a: str, name_b: str) -> list[dict]:
    """
    Returns list of hunk dicts: {type: 'added'|'removed'|'context', text: str, line_a: int, line_b: int}
    """
    hunks = []
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k, line in enumerate(lines_a[i1:i2]):
                hunks.append({"type": "context", "text": line.rstrip("\n"), "line_a": i1+k+1, "line_b": j1+k+1})
        elif tag in ("replace", "delete"):
            for k, line in enumerate(lines_a[i1:i2]):
                hunks.append({"type": "removed", "text": line.rstrip("\n"), "line_a": i1+k+1, "line_b": None})
        if tag in ("replace", "insert"):
            for k, line in enumerate(lines_b[j1:j2]):
                hunks.append({"type": "added", "text": line.rstrip("\n"), "line_a": None, "line_b": j1+k+1})
    return hunks

def diff_contracts(path_a: str, path_b: str, name_a: str, name_b: str) -> list[dict]:
    lines_a = extract_lines(path_a)
    lines_b = extract_lines(path_b)
    return compute_diff(lines_a, lines_b, name_a, name_b)
