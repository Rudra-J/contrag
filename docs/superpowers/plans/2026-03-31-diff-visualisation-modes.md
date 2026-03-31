# Diff Visualisation Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three additional diff visualisation modes (Side by Side, Redline, Risk Analysis) to the Diff tab, with a mode selector bar that appears after a compare is run.

**Architecture:** All modes share the same `GET /api/diff` hunk data already returned by the backend. Side-by-side and Redline are pure frontend transforms of those hunks; Risk Analysis fires a new `POST /api/diff/risk` endpoint that runs the LLM against the changed blocks. A new `web/js/diff-renderers.js` module owns all four rendering functions (Unified, Side by Side, Redline, Risk); `diff.js` stores cached hunk state and wires the mode selector.

**Tech Stack:** FastAPI + ChatOllama (llama3.2) on the backend; vanilla ES-module JS + existing CSS design tokens on the frontend; pytest + unittest.mock for tests.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/main.py` | Modify | Add `POST /api/diff/risk` endpoint |
| `tests/test_diff_risk.py` | Create | Tests for risk endpoint |
| `web/js/api.js` | Modify | Add `getDiffRisk(hunks, nameA, nameB)` |
| `web/css/app.css` | Modify | Mode selector bar, side-by-side, redline, risk styles |
| `web/js/diff-renderers.js` | Create | `renderUnified`, `renderSideBySide`, `renderRedline`, `renderRisk` |
| `web/js/tabs/diff.js` | Modify | Mode state, result wrapper with mode bar, delegate to renderers |

---

## Task 1: Backend `/api/diff/risk` endpoint

**Files:**
- Modify: `backend/main.py` (after the existing `/api/diff` route, before the static mount)
- Create: `tests/test_diff_risk.py`

### Background

The risk endpoint receives the hunks already computed by `/api/diff` (the frontend re-sends them). It groups them into change blocks, builds a text prompt, calls the LLM via ChatOllama, and returns a structured JSON response. Index `i` in the response `changes` array maps to change-block `i` (0-based, excluding context runs).

### Step-by-step

- [ ] **Step 1: Write the failing tests**

Create `tests/test_diff_risk.py`:

```python
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

    with patch("main.ChatOllama", return_value=fake_llm):
        client = _client()
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

    with patch("main.ChatOllama", return_value=fake_llm):
        client = _client()
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
    """If all hunks are context, no change blocks exist — return empty changes."""
    context_only = [
        {"type": "context", "text": "Same line.", "line_a": 1, "line_b": 1},
    ]
    fake_llm = MagicMock()
    fake_llm.invoke.return_value.content = json.dumps({"summary": "No changes.", "changes": []})

    with patch("main.ChatOllama", return_value=fake_llm):
        client = _client()
        resp = client.post("/api/diff/risk", json={
            "hunks": context_only, "name_a": "a.pdf", "name_b": "b.pdf"
        })

    assert resp.status_code == 200
    assert resp.json()["changes"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd D:\Workspace\contrag && venv/Scripts/activate && pytest tests/test_diff_risk.py -v
```

Expected: ImportError or 404 (endpoint not found yet).

- [ ] **Step 3: Implement the endpoint in `backend/main.py`**

Add these imports at the top of `backend/main.py` (after existing imports):

```python
import re, json as _json
from langchain_ollama import ChatOllama
```

Add this endpoint after the existing `GET /api/diff` route (before `GET /api/glossary`):

```python
# ── Diff Risk Analysis ────────────────────────────────────────────────────────

_RISK_SYSTEM = (
    "You are a legal risk analyst. Review the contract changes below and classify "
    "each change block.\n\n"
    "Respond ONLY with valid JSON — no markdown, no explanation outside the JSON.\n\n"
    "Format:\n"
    '{{"summary": "<2-3 sentence executive summary>", '
    '"changes": [{{"index": 0, "risk": "<level>", "explanation": "<brief reason>"}}]}}\n\n'
    "Risk levels:\n"
    "  risk_increase — adds obligations, tightens deadlines, removes protections\n"
    "  risk_decrease — removes obligations, extends timelines, adds protections\n"
    "  neutral       — formatting, typos, clarifications, no material impact\n"
)

def _group_change_blocks(hunks: list) -> list[list]:
    """Group consecutive non-context hunks into change blocks."""
    blocks, buf = [], []
    for h in hunks:
        if h["type"] == "context":
            if buf:
                blocks.append(buf)
                buf = []
        else:
            buf.append(h)
    if buf:
        blocks.append(buf)
    return blocks

def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
    return _json.loads(text.strip())

@app.post("/api/diff/risk")
async def diff_risk(body: dict):
    hunks = body.get("hunks")
    if not hunks:
        raise HTTPException(400, "hunks is required")
    name_a = body.get("name_a", "Base")
    name_b = body.get("name_b", "Compare")

    blocks = _group_change_blocks(hunks)

    changes_text = ""
    for i, block in enumerate(blocks):
        removed_lines = [h["text"] for h in block if h["type"] == "removed"]
        added_lines   = [h["text"] for h in block if h["type"] == "added"]
        changes_text += f"[Change {i}]\n"
        if removed_lines:
            changes_text += f"  REMOVED: {' '.join(removed_lines)}\n"
        if added_lines:
            changes_text += f"  ADDED:   {' '.join(added_lines)}\n"
        changes_text += "\n"

    prompt = (
        f'{_RISK_SYSTEM}\n'
        f'Changes between "{name_a}" (base) and "{name_b}" (compare):\n\n'
        f'{changes_text}'
    )

    llm = ChatOllama(model="llama3.2", temperature=0)
    result = llm.invoke(prompt)
    try:
        data = _extract_json(result.content)
    except Exception:
        raise HTTPException(500, f"LLM returned invalid JSON: {result.content[:200]}")

    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd D:\Workspace\contrag && venv/Scripts/activate && pytest tests/test_diff_risk.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_diff_risk.py
git commit -m "feat: add POST /api/diff/risk endpoint for LLM-powered change classification"
```

---

## Task 2: `api.js` — add `getDiffRisk`

**Files:**
- Modify: `web/js/api.js`

- [ ] **Step 1: Add the function**

Open `web/js/api.js`. After the `getDiff` export, add:

```js
export async function getDiffRisk(hunks, nameA, nameB) {
  const r = await fetch(`${BASE}/api/diff/risk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hunks, name_a: nameA, name_b: nameB }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
```

- [ ] **Step 2: Verify no syntax errors**

```
cd D:\Workspace\contrag && node --input-type=module < web/js/api.js
```

Expected: No output (module evaluated, no errors). If node isn't available, skip — the browser will catch syntax errors.

- [ ] **Step 3: Commit**

```bash
git add web/js/api.js
git commit -m "feat: add getDiffRisk API helper"
```

---

## Task 3: CSS for new modes

**Files:**
- Modify: `web/css/app.css` (append at the bottom)

- [ ] **Step 1: Append the new styles**

Open `web/css/app.css` and append the following block at the very end of the file:

```css
/* ── Diff mode selector bar ─────────────────────────────────────── */
.diff-mode-bar {
  display: flex;
  gap: 4px;
  padding: 10px 0 14px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 14px;
}
.diff-mode-btn {
  padding: 5px 14px;
  border-radius: 99px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition: color var(--transition), border-color var(--transition), background var(--transition);
}
.diff-mode-btn:hover { color: var(--text); border-color: var(--text-muted); }
.diff-mode-btn.active {
  background: var(--gold-dim);
  border-color: var(--gold);
  color: var(--gold);
}

/* ── Side-by-side diff ──────────────────────────────────────────── */
.diff-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.diff-split-pane {
  overflow-x: auto;
  overflow-y: hidden;  /* scroll sync via JS */
  font-family: 'Courier New', monospace;
  font-size: 0.82rem;
}
.diff-split-pane:first-child {
  border-right: 1px solid var(--border);
}
.diff-split-header {
  padding: 6px 10px;
  font-size: 0.75rem;
  font-family: var(--font-body);
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  text-transform: uppercase;
}
.diff-split-pane .diff-line { min-width: 0; }
.diff-split-pane .diff-line.empty { background: var(--bg); opacity: 0.4; }

/* ── Redline diff ───────────────────────────────────────────────── */
.redline-viewer {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  overflow-x: auto;
}
.redline-line {
  display: flex;
  gap: 0;
  line-height: 1.6;
  padding: 2px 0;
}
.redline-line.context { background: var(--surface); }
.redline-line.change  { background: var(--surface-2); }
.redline-gutter {
  width: 40px;
  min-width: 40px;
  text-align: right;
  padding: 1px 6px;
  color: var(--text-dim);
  user-select: none;
  border-right: 1px solid var(--border);
  font-size: 0.78rem;
}
.redline-text {
  padding: 1px 10px;
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
  color: var(--text-muted);
}
.redline-line.change .redline-text { color: var(--text); }
del.rl-del {
  text-decoration: line-through;
  color: #cf8e8e;
  background: rgba(158,74,74,0.15);
  border-radius: 2px;
  padding: 0 1px;
}
ins.rl-ins {
  text-decoration: underline;
  text-decoration-color: var(--green);
  color: #8ecf8e;
  background: rgba(74,158,74,0.12);
  border-radius: 2px;
  padding: 0 1px;
  font-style: normal;
}

/* ── Risk analysis diff ─────────────────────────────────────────── */
.risk-summary-card {
  background: var(--surface-2);
  border: 1px solid var(--border-gold);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
}
.risk-summary-card h4 {
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 0.5rem;
}
.risk-summary-card p {
  font-size: 0.88rem;
  color: var(--text-muted);
  line-height: 1.6;
}
.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 99px;
  margin-left: 8px;
  vertical-align: middle;
  flex-shrink: 0;
}
.risk-badge.risk_increase { background: rgba(158,74,74,0.25); color: #cf8e8e; border: 1px solid rgba(158,74,74,0.4); }
.risk-badge.risk_decrease { background: rgba(74,158,74,0.2);  color: #8ecf8e; border: 1px solid rgba(74,158,74,0.3); }
.risk-badge.neutral       { background: rgba(255,255,255,0.05); color: var(--text-dim); border: 1px solid var(--border); }
.risk-explanation {
  font-size: 0.78rem;
  color: var(--text-dim);
  padding: 3px 10px 3px 68px;
  font-style: italic;
  line-height: 1.5;
  background: var(--surface);
}
.diff-line.risk_increase { background: rgba(158,74,74,0.12); }
.diff-line.risk_decrease { background: rgba(74,158,74,0.1); }
.diff-line.neutral.added,
.diff-line.neutral.removed { background: var(--surface-2); }
```

- [ ] **Step 2: Verify no CSS parse errors by opening the browser dev tools — or just check for obvious typos**

Visually scan the block for mismatched braces. Count opening `{` = closing `}`.

- [ ] **Step 3: Commit**

```bash
git add web/css/app.css
git commit -m "feat: add CSS for diff mode selector, side-by-side, redline, and risk modes"
```

---

## Task 4: `diff-renderers.js` — all four renderers

**Files:**
- Create: `web/js/diff-renderers.js`

### Background

This module exports four pure functions. Each receives hunk data (and optionally risk data) and returns an HTML string. It does not touch the DOM. The `esc` helper is duplicated here (not imported from diff.js) to keep the module self-contained.

- `renderUnified(hunks)` — the existing unified view, extracted from diff.js
- `renderSideBySide(hunks, nameA, nameB)` — two-column aligned view
- `renderRedline(hunks)` — inline word-level del/ins
- `renderRisk(hunks, riskData)` — unified view annotated with risk badges

### Word diff algorithm

`wordDiff(oldText, newText)` splits text into tokens (words + whitespace runs), runs LCS, and returns `[{op: "equal"|"delete"|"insert", text: string}]`. Used by `renderRedline`.

- [ ] **Step 1: Create the file**

Create `web/js/diff-renderers.js` with the full content below:

```js
// web/js/diff-renderers.js
// Pure rendering functions — no DOM mutations, no imports.

// ── Helpers ──────────────────────────────────────────────────────

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const CTX = 3;

function diffStats(hunks) {
  const added   = hunks.filter(h => h.type === "added").length;
  const removed = hunks.filter(h => h.type === "removed").length;
  return `<div class="diff-stats">
    <span class="add">+${added} additions</span> &nbsp;
    <span class="rem">&#8722;${removed} removals</span>
  </div>`;
}

/** Collapse context runs: keep CTX lines at each edge, add ellipsis between. */
function collapseContext(hunks, emitLine) {
  let ctxBuf = [];
  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      ctxBuf.forEach(emitLine);
    } else {
      ctxBuf.slice(0, CTX).forEach(emitLine);
      emitLine(null); // ellipsis sentinel
      ctxBuf.slice(-CTX).forEach(emitLine);
    }
    ctxBuf = [];
  }
  for (const h of hunks) {
    if (h.type === "context") { ctxBuf.push(h); }
    else { flushCtx(); emitLine(h); }
  }
  flushCtx();
}

// ── Unified renderer ─────────────────────────────────────────────

function unifiedLineHtml(h) {
  if (h === null) {
    return `<div class="diff-line ellipsis"><span style="padding:0 8px;color:var(--text-dim)">&#8230;</span></div>`;
  }
  const prefix = h.type === "added" ? "+" : h.type === "removed" ? "&#8722;" : "&nbsp;";
  return `<div class="diff-line ${h.type}">
    <span class="diff-gutter">${h.line_a ?? ""}</span>
    <span class="diff-gutter">${h.line_b ?? ""}</span>
    <span class="diff-prefix">${prefix}</span>
    <span class="diff-text">${esc(h.text)}</span>
  </div>`;
}

export function renderUnified(hunks) {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }
  let lines = "";
  collapseContext(hunks, h => { lines += unifiedLineHtml(h); });
  return diffStats(hunks) + `<div class="diff-viewer">${lines}</div>`;
}

// ── Side-by-side renderer ─────────────────────────────────────────

/**
 * Groups consecutive non-context hunks into blocks.
 * Within each block, pairs removed[i] with added[i] (ghost null for overflow).
 * Returns array of {left: hunk|null, right: hunk|null} rows.
 */
function buildSplitRows(hunks) {
  const rows = [];
  let i = 0;
  while (i < hunks.length) {
    const h = hunks[i];
    if (h.type === "context") {
      rows.push({ left: h, right: h, isCtx: true });
      i++;
    } else {
      const removed = [], added = [];
      while (i < hunks.length && hunks[i].type !== "context") {
        if (hunks[i].type === "removed") removed.push(hunks[i]);
        else added.push(hunks[i]);
        i++;
      }
      const len = Math.max(removed.length, added.length);
      for (let k = 0; k < len; k++) {
        rows.push({ left: removed[k] || null, right: added[k] || null, isCtx: false });
      }
    }
  }
  return rows;
}

function splitCellHtml(h, side) {
  // h is a hunk or null (ghost)
  if (h === null) {
    return `<div class="diff-line empty">
      <span class="diff-gutter"></span>
      <span class="diff-prefix">&nbsp;</span>
      <span class="diff-text"></span>
    </div>`;
  }
  const prefix = h.type === "added" ? "+" : h.type === "removed" ? "&#8722;" : "&nbsp;";
  const lineNum = side === "left" ? (h.line_a ?? "") : (h.line_b ?? "");
  return `<div class="diff-line ${h.type}">
    <span class="diff-gutter">${lineNum}</span>
    <span class="diff-prefix">${prefix}</span>
    <span class="diff-text">${esc(h.text)}</span>
  </div>`;
}

export function renderSideBySide(hunks, nameA = "Base", nameB = "Compare") {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }

  const rows = buildSplitRows(hunks);

  // Collapse context: build left and right html separately, keeping them in sync
  // We need paired collapse: both sides must emit an ellipsis at the same row index.
  // Strategy: identify which rows are context, collapse runs of CTX*2+ ctx rows.
  let leftHtml = "", rightHtml = "";
  let ctxBuf = [];

  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      for (const row of ctxBuf) {
        leftHtml  += splitCellHtml(row.left,  "left");
        rightHtml += splitCellHtml(row.right, "right");
      }
    } else {
      for (const row of ctxBuf.slice(0, CTX)) {
        leftHtml  += splitCellHtml(row.left,  "left");
        rightHtml += splitCellHtml(row.right, "right");
      }
      const ellipsis = `<div class="diff-line ellipsis"><span style="padding:0 8px;color:var(--text-dim)">&#8230;</span></div>`;
      leftHtml  += ellipsis;
      rightHtml += ellipsis;
      for (const row of ctxBuf.slice(-CTX)) {
        leftHtml  += splitCellHtml(row.left,  "left");
        rightHtml += splitCellHtml(row.right, "right");
      }
    }
    ctxBuf = [];
  }

  for (const row of rows) {
    if (row.isCtx) {
      ctxBuf.push(row);
    } else {
      flushCtx();
      leftHtml  += splitCellHtml(row.left,  "left");
      rightHtml += splitCellHtml(row.right, "right");
    }
  }
  flushCtx();

  return diffStats(hunks) + `
    <div class="diff-split">
      <div class="diff-split-pane" id="split-left">
        <div class="diff-split-header">${esc(nameA)}</div>
        ${leftHtml}
      </div>
      <div class="diff-split-pane" id="split-right">
        <div class="diff-split-header">${esc(nameB)}</div>
        ${rightHtml}
      </div>
    </div>`;
}

// ── Redline renderer ──────────────────────────────────────────────

/** Tokenise text into word/whitespace/punctuation tokens for word-level diff. */
function tokenise(text) {
  return text.match(/\S+|\s+/g) || [];
}

/** Myers-style LCS on token arrays. Returns [{op, text}]. */
function lcs(a, b) {
  const m = a.length, n = b.length;
  // For very long token arrays cap to avoid O(mn) blowup (>300 tokens each → fallback)
  if (m > 300 || n > 300) {
    return [
      ...a.map(t => ({ op: "delete", text: t })),
      ...b.map(t => ({ op: "insert", text: t })),
    ];
  }
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] + 1 : Math.max(dp[i-1][j], dp[i][j-1]);
  const ops = [];
  let i = m, j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i-1] === b[j-1]) {
      ops.unshift({ op: "equal",  text: a[i-1] }); i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j-1] >= dp[i-1][j])) {
      ops.unshift({ op: "insert", text: b[j-1] }); j--;
    } else {
      ops.unshift({ op: "delete", text: a[i-1] }); i--;
    }
  }
  return ops;
}

function wordDiffHtml(ops) {
  return ops.map(op => {
    const t = esc(op.text);
    if (op.op === "delete") return `<del class="rl-del">${t}</del>`;
    if (op.op === "insert") return `<ins class="rl-ins">${t}</ins>`;
    return t;
  }).join("");
}

export function renderRedline(hunks) {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }

  let html = "";
  let i = 0;

  while (i < hunks.length) {
    const h = hunks[i];

    if (h.type === "context") {
      html += `<div class="redline-line context">
        <span class="redline-gutter">${h.line_a}</span>
        <span class="redline-text">${esc(h.text)}</span>
      </div>`;
      i++;
      continue;
    }

    // Collect a replace/delete/insert block
    const removed = [], added = [];
    while (i < hunks.length && hunks[i].type !== "context") {
      if (hunks[i].type === "removed") removed.push(hunks[i]);
      else added.push(hunks[i]);
      i++;
    }

    const oldText = removed.map(r => r.text).join(" ");
    const newText = added.map(a => a.text).join(" ");
    const lineLabel = removed.length ? removed[0].line_a : (added.length ? added[0].line_b : "");

    const ops = lcs(tokenise(oldText), tokenise(newText));
    html += `<div class="redline-line change">
      <span class="redline-gutter">${lineLabel}</span>
      <span class="redline-text">${wordDiffHtml(ops)}</span>
    </div>`;
  }

  return diffStats(hunks) + `<div class="redline-viewer">${html}</div>`;
}

// ── Risk renderer ─────────────────────────────────────────────────

/**
 * Groups consecutive non-context hunks into change blocks.
 * Returns array of arrays. Block index i maps to riskData.changes[i].index.
 */
function groupChangeBlocks(hunks) {
  const blocks = [];
  let buf = [];
  for (const h of hunks) {
    if (h.type === "context") {
      if (buf.length) { blocks.push(buf); buf = []; }
    } else {
      buf.push(h);
    }
  }
  if (buf.length) blocks.push(buf);
  return blocks;
}

export function renderRisk(hunks, riskData) {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }

  // Build a map: blockIndex → risk info
  const riskMap = {};
  for (const c of (riskData.changes || [])) {
    riskMap[c.index] = c;
  }

  // Build a map: hunkIndex → blockIndex (for annotating lines)
  const blockIndexByHunk = new Map();
  const blocks = groupChangeBlocks(hunks);
  {
    let blockIdx = 0, scanBlock = 0;
    for (let h = 0; h < hunks.length; h++) {
      if (hunks[h].type === "context") continue;
      // Find which block this hunk belongs to
      if (scanBlock < blocks.length) {
        const block = blocks[scanBlock];
        if (block.includes(hunks[h])) {
          blockIndexByHunk.set(h, scanBlock);
        }
        // Move to next block when we've passed all members of the current one
        if (h === hunks.indexOf(block[block.length - 1])) scanBlock++;
      }
    }
  }

  // Build block-start hunk index map for annotation injection
  const blockStartHunkIdx = new Map(); // blockIdx → first hunk index in hunks array
  {
    let b = 0;
    for (let h = 0; h < hunks.length; h++) {
      if (hunks[h].type !== "context" && b < blocks.length) {
        if (!blockStartHunkIdx.has(b)) blockStartHunkIdx.set(b, h);
        if (h === hunks.indexOf(blocks[b][blocks[b].length - 1])) b++;
      }
    }
  }

  // Build risk badge label
  const LABEL = {
    risk_increase: "Risk ▲",
    risk_decrease: "Risk ▼",
    neutral:       "Neutral",
  };

  // Render unified diff lines, injecting risk badges at the first line of each block
  // and risk explanation rows after each block
  let lines = "";
  let blockPtr = 0;
  let ctxBuf = [];

  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      ctxBuf.forEach(row => { lines += row; });
    } else {
      ctxBuf.slice(0, CTX).forEach(row => { lines += row; });
      lines += `<div class="diff-line ellipsis"><span style="padding:0 8px;color:var(--text-dim)">&#8230;</span></div>`;
      ctxBuf.slice(-CTX).forEach(row => { lines += row; });
    }
    ctxBuf = [];
  }

  // Track which block we're in and whether we've emitted its badge
  let currentBlock = -1;
  let blockEmitted = false;

  for (const h of hunks) {
    if (h.type === "context") {
      // Emit explanation for closed block
      if (currentBlock >= 0 && !blockEmitted) {
        const risk = riskMap[currentBlock];
        if (risk) {
          ctxBuf.push(`<div class="risk-explanation">${esc(risk.explanation)}</div>`);
        }
        currentBlock = -1;
        blockEmitted = false;
      }
      const prefix = "&nbsp;";
      ctxBuf.push(`<div class="diff-line context">
        <span class="diff-gutter">${h.line_a ?? ""}</span>
        <span class="diff-gutter">${h.line_b ?? ""}</span>
        <span class="diff-prefix">${prefix}</span>
        <span class="diff-text">${esc(h.text)}</span>
      </div>`);
    } else {
      flushCtx();

      // Determine block index for this hunk
      if (currentBlock < 0) {
        // Find which block we just entered
        for (let b = 0; b < blocks.length; b++) {
          if (blocks[b].includes(h)) { currentBlock = b; blockEmitted = false; break; }
        }
      }

      const risk = riskMap[currentBlock];
      const riskClass = risk ? ` ${risk.risk}` : "";
      const badge = (risk && !blockEmitted)
        ? `<span class="risk-badge ${risk.risk}">${LABEL[risk.risk] || risk.risk}</span>`
        : "";
      if (!blockEmitted && risk) blockEmitted = false; // badge emitted below

      const prefix = h.type === "added" ? "+" : "&#8722;";
      const showBadge = risk && !blockEmitted;
      if (showBadge) blockEmitted = true;

      lines += `<div class="diff-line ${h.type}${riskClass}">
        <span class="diff-gutter">${h.line_a ?? ""}</span>
        <span class="diff-gutter">${h.line_b ?? ""}</span>
        <span class="diff-prefix">${prefix}</span>
        <span class="diff-text">${esc(h.text)}${showBadge ? `<span class="risk-badge ${risk.risk}">${LABEL[risk.risk] || risk.risk}</span>` : ""}</span>
      </div>`;
    }
  }
  // Flush final block explanation
  if (currentBlock >= 0) {
    const risk = riskMap[currentBlock];
    if (risk) ctxBuf.push(`<div class="risk-explanation">${esc(risk.explanation)}</div>`);
  }
  flushCtx();

  const summaryCard = `
    <div class="risk-summary-card">
      <h4>Risk Summary</h4>
      <p>${esc(riskData.summary || "No summary available.")}</p>
    </div>`;

  return summaryCard + diffStats(hunks) + `<div class="diff-viewer">${lines}</div>`;
}
```

- [ ] **Step 2: Verify the file was created**

```
ls web/js/diff-renderers.js
```

Expected: file listed.

- [ ] **Step 3: Commit**

```bash
git add web/js/diff-renderers.js
git commit -m "feat: add diff-renderers.js with unified, side-by-side, redline, and risk renderers"
```

---

## Task 5: Wire mode selector into `diff.js`

**Files:**
- Modify: `web/js/tabs/diff.js`

### Background

`diff.js` needs to:
1. Import `getDiffRisk` from `api.js` and the four renderers from `diff-renderers.js`
2. Store last compare result: `_lastHunks`, `_lastNameA`, `_lastNameB`, `_lastRiskData`
3. After a successful compare, render a result wrapper containing the mode bar + a `#diff-mode-content` div
4. On mode button click: re-render `#diff-mode-content` (fetching risk data on first Risk Analysis click)
5. Scroll-sync the two panes in Side by Side mode
6. Default mode is "unified"

### Full replacement of `diff.js`

- [ ] **Step 1: Replace the entire file content**

Replace `web/js/tabs/diff.js` with:

```js
import { getFiles, uploadFile, getDiff, getDiffRisk } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";
import { renderUnified, renderSideBySide, renderRedline, renderRisk } from "../diff-renderers.js";

let _toast;

// ── Cached diff state ─────────────────────────────────────────────
let _lastHunks    = null;
let _lastNameA    = null;
let _lastNameB    = null;
let _lastRiskData = null;   // fetched lazily, cached after first fetch
let _currentMode  = "unified";

// ── HTML escaping ─────────────────────────────────────────────────

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ── Slot builder ─────────────────────────────────────────────────

function buildSlot(id, labelText, names, defaultIndex) {
  const opts = names.map((n, i) =>
    `<option value="${esc(n)}"${i === defaultIndex ? " selected" : ""}>${esc(n)}</option>`
  ).join("");

  return `
    <div class="diff-slot">
      <label for="${id}">${esc(labelText)}</label>
      <div class="diff-slot-controls">
        <select id="${id}">${opts}</select>
        <label class="btn btn-secondary diff-upload-btn" title="Upload a new contract for this slot">
          Upload new
          <input class="diff-upload-input" type="file" accept=".pdf,.docx,.txt">
        </label>
      </div>
    </div>
  `;
}

function buildSelectors(files) {
  const names = files.map(f => f.name);

  const selectorBlock = `
    <div class="card">
      <div class="diff-selectors">
        ${buildSlot("diff-a", "Base contract", names, 0)}
        ${buildSlot("diff-b", "Compare contract", names, Math.min(1, Math.max(0, names.length - 1)))}
        <button class="btn btn-primary" id="diff-btn"${names.length < 2 ? " disabled" : ""}>Compare</button>
      </div>
    </div>
    <div id="diff-result"></div>
  `;

  if (names.length === 0) {
    return `<div class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-dim)" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      <p>Upload contracts using the buttons below, or add them on the Files page first.</p>
    </div>
    ${selectorBlock}`;
  }

  return selectorBlock;
}

// ── Diff result wrapper with mode bar ─────────────────────────────

const MODES = [
  { id: "unified",    label: "Unified" },
  { id: "side-by-side", label: "Side by Side" },
  { id: "redline",    label: "Redline" },
  { id: "risk",       label: "Risk Analysis" },
];

function modeBtns() {
  return MODES.map(m =>
    `<button class="diff-mode-btn${m.id === _currentMode ? " active" : ""}" data-mode="${m.id}">${m.label}</button>`
  ).join("");
}

function buildResultWrapper(innerHtml) {
  return `
    <div class="diff-mode-bar" id="diff-mode-bar">${modeBtns()}</div>
    <div id="diff-mode-content">${innerHtml}</div>
  `;
}

// ── Scroll sync for side-by-side ─────────────────────────────────

function wireSplitSync() {
  const left  = document.getElementById("split-left");
  const right = document.getElementById("split-right");
  if (!left || !right) return;
  let syncing = false;
  left.addEventListener("scroll", () => {
    if (syncing) return; syncing = true;
    right.scrollTop = left.scrollTop; syncing = false;
  });
  right.addEventListener("scroll", () => {
    if (syncing) return; syncing = true;
    left.scrollTop = right.scrollTop; syncing = false;
  });
}

// ── Mode rendering ────────────────────────────────────────────────

async function renderMode(mode) {
  const content = document.getElementById("diff-mode-content");
  if (!content || !_lastHunks) return;

  if (mode === "unified") {
    content.innerHTML = renderUnified(_lastHunks);
  } else if (mode === "side-by-side") {
    content.innerHTML = renderSideBySide(_lastHunks, _lastNameA, _lastNameB);
    wireSplitSync();
  } else if (mode === "redline") {
    content.innerHTML = renderRedline(_lastHunks);
  } else if (mode === "risk") {
    if (!_lastRiskData) {
      content.innerHTML = `
        <div class="diff-inline-loader">
          <svg viewBox="0 0 140 150" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect x="66" y="40" width="8" height="96" fill="#b0a080" rx="2"/>
            <rect x="34" y="132" width="72" height="9" fill="#b0a080" rx="3"/>
            <circle cx="70" cy="36" r="6" fill="#c8a850"/>
            <g class="beam-group">
              <line x1="10" y1="42" x2="130" y2="42" stroke="#c8a850" stroke-width="3.5" stroke-linecap="round"/>
              <line x1="20" y1="42" x2="20" y2="70" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="4 3"/>
              <line x1="120" y1="42" x2="120" y2="70" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="4 3"/>
              <g class="pan-left"><ellipse cx="20" cy="74" rx="19" ry="6" fill="#c8a850" opacity="0.9"/></g>
              <g class="pan-right"><ellipse cx="120" cy="74" rx="19" ry="6" fill="#c8a850" opacity="0.9"/></g>
            </g>
          </svg>
          Analysing risks&hellip;
        </div>`;
      try {
        _lastRiskData = await getDiffRisk(_lastHunks, _lastNameA, _lastNameB);
      } catch (e) {
        content.innerHTML = `<div class="empty-state"><p>Risk analysis failed: ${esc(String(e))}</p></div>`;
        return;
      }
    }
    content.innerHTML = renderRisk(_lastHunks, _lastRiskData);
  }
}

// ── Upload wiring ─────────────────────────────────────────────────

function wireUploadInputs(container, onUploadComplete) {
  ["diff-a", "diff-b"].forEach(slotId => {
    const select = container.querySelector(`#${slotId}`);
    if (!select) return;
    const slotEl = select.closest(".diff-slot");
    if (!slotEl) return;
    const fileInput = slotEl.querySelector(".diff-upload-input");
    if (!fileInput) return;

    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      showLoader(`Ingesting ${file.name}\u2026`);
      try {
        await uploadFile(file);
        _toast(`${file.name} uploaded.`, "success");
        await onUploadComplete(slotId, file.name);
      } catch(e) {
        _toast(`Upload failed: ${e.message || e}`, "error");
      } finally {
        hideLoader();
        fileInput.value = "";
      }
    });
  });
}

// ── Init ─────────────────────────────────────────────────────────

export async function initDiff(toast) {
  _toast = toast;
  const container = document.getElementById("diff-content");

  async function render(selectAfterUpload = null) {
    const files = await getFiles();
    container.innerHTML = buildSelectors(files);

    if (selectAfterUpload) {
      const select = document.getElementById(selectAfterUpload.slotId);
      if (select) select.value = selectAfterUpload.filename;
    }

    wireUploadInputs(container, async (slotId, filename) => {
      await render({ slotId, filename });
    });

    const btn = document.getElementById("diff-btn");
    if (!btn || btn.disabled) return;

    btn.addEventListener("click", async () => {
      const a = document.getElementById("diff-a").value;
      const b = document.getElementById("diff-b").value;
      if (a === b) { _toast("Select two different contracts.", "error"); return; }

      btn.disabled = true;
      const resultEl = document.getElementById("diff-result");

      // Show inline loader while fetching hunks
      resultEl.innerHTML = `
        <div class="diff-inline-loader">
          <svg viewBox="0 0 140 150" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect x="66" y="40" width="8" height="96" fill="#b0a080" rx="2"/>
            <rect x="34" y="132" width="72" height="9" fill="#b0a080" rx="3"/>
            <circle cx="70" cy="36" r="6" fill="#c8a850"/>
            <g class="beam-group">
              <line x1="10" y1="42" x2="130" y2="42" stroke="#c8a850" stroke-width="3.5" stroke-linecap="round"/>
              <line x1="20" y1="42" x2="20" y2="70" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="4 3"/>
              <line x1="120" y1="42" x2="120" y2="70" stroke="#c8a850" stroke-width="1.5" stroke-dasharray="4 3"/>
              <g class="pan-left"><ellipse cx="20" cy="74" rx="19" ry="6" fill="#c8a850" opacity="0.9"/></g>
              <g class="pan-right"><ellipse cx="120" cy="74" rx="19" ry="6" fill="#c8a850" opacity="0.9"/></g>
            </g>
          </svg>
          Comparing contracts&hellip;
        </div>`;

      try {
        const { hunks } = await getDiff(a, b);
        // Cache state, reset risk cache when new compare runs
        _lastHunks    = hunks;
        _lastNameA    = a;
        _lastNameB    = b;
        _lastRiskData = null;
        _currentMode  = "unified";

        resultEl.innerHTML = buildResultWrapper(renderUnified(hunks));

        // Wire mode bar
        resultEl.querySelectorAll(".diff-mode-btn").forEach(modeBtn => {
          modeBtn.addEventListener("click", async () => {
            const mode = modeBtn.dataset.mode;
            if (mode === _currentMode) return;
            _currentMode = mode;
            // Update active state
            resultEl.querySelectorAll(".diff-mode-btn").forEach(b2 => {
              b2.classList.toggle("active", b2.dataset.mode === mode);
            });
            await renderMode(mode);
          });
        });
      } catch(e) {
        resultEl.innerHTML = "";
        _toast(String(e), "error");
      } finally {
        btn.disabled = false;
      }
    });
  }

  await render();
  document.querySelector('[data-tab="diff"]').addEventListener("click", () => render());
}
```

- [ ] **Step 2: Run the existing diff engine tests**

```
cd D:\Workspace\contrag && venv/Scripts/activate && pytest tests/test_diff_engine.py -v
```

Expected: 3 PASSED (unchanged tests still pass)

- [ ] **Step 3: Run all tests**

```
cd D:\Workspace\contrag && venv/Scripts/activate && pytest tests/ -v
```

Expected: all tests pass (diff_engine, diff_risk, chain, retriever, file_manager, glossary_engine)

- [ ] **Step 4: Manual smoke test checklist**

Start the server:
```
cd D:\Workspace\contrag && venv/Scripts/activate && uvicorn backend.main:app --reload
```

Open `http://localhost:8000`, go to Diff tab. Verify:
- [ ] Upload two contract files (or use existing ones from Files page)
- [ ] Click Compare — inline scales animation appears while loading
- [ ] Unified mode renders (default) with mode bar showing 4 buttons
- [ ] "Side by Side" mode — two columns with headers, scrolling one syncs the other
- [ ] "Redline" mode — single column, deleted text in red strikethrough, added text in green underline
- [ ] "Risk Analysis" mode — scales animation shows while LLM runs, then risk summary card + diff with colour-coded badges appears
- [ ] Switching between modes while staying on same compare result works instantly (except Risk which re-uses cache)
- [ ] Running a new Compare resets to Unified and clears risk cache

- [ ] **Step 5: Commit**

```bash
git add web/js/tabs/diff.js web/js/diff-renderers.js
git commit -m "feat: wire diff mode selector with side-by-side, redline, and risk analysis modes"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Side-by-side split view — Task 4/5 (`renderSideBySide` + CSS `.diff-split`)
- ✅ Redline / track-changes — Task 4/5 (`renderRedline` + `lcs` word diff + CSS `del.rl-del` / `ins.rl-ins`)
- ✅ Risk change highlights — Task 1 (backend endpoint) + Task 4/5 (`renderRisk` + CSS `.risk-badge`)
- ✅ Mode selector — Task 5 (mode bar in `diff.js`, CSS `.diff-mode-bar/.diff-mode-btn`)
- ✅ LLM risk caching — `_lastRiskData` persists across mode switches, cleared on new Compare
- ✅ Scroll sync for side-by-side — `wireSplitSync()` in Task 5
- ✅ Inline loader (not full-screen) — both for initial compare and Risk Analysis loading

**Placeholder scan:** No TBDs, all code blocks complete.

**Type consistency:**
- `renderSideBySide(hunks, nameA, nameB)` — matches call in `diff.js`
- `renderRisk(hunks, riskData)` — `riskData` is `{summary, changes: [{index, risk, explanation}]}` — consistent between backend response and frontend consumption
- `groupChangeBlocks(hunks)` — used in both `renderRisk` (frontend) and `_group_change_blocks` (backend) with identical grouping logic
- `getDiffRisk(hunks, nameA, nameB)` in `api.js` — sends `{hunks, name_a, name_b}` — backend reads `body.get("name_a")` ✅
