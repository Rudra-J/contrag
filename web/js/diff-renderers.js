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

function collapseAndRender(hunks, renderLine) {
  let lines = "";
  let ctxBuf = [];

  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      ctxBuf.forEach(item => { lines += renderLine(item, item); });
    } else {
      ctxBuf.slice(0, CTX).forEach(item => { lines += renderLine(item, item); });
      lines += renderLine(null, null);
      ctxBuf.slice(-CTX).forEach(item => { lines += renderLine(item, item); });
    }
    ctxBuf = [];
  }

  for (const h of hunks) {
    if (h.type === "context") { ctxBuf.push(h); }
    else { flushCtx(); lines += renderLine(h, h); }
  }
  flushCtx();
  return lines;
}

export function renderUnified(hunks) {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }
  const lines = collapseAndRender(hunks, (h) => unifiedLineHtml(h));
  return diffStats(hunks) + `<div class="diff-viewer">${lines}</div>`;
}

// ── Side-by-side renderer ─────────────────────────────────────────

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
    if (row.isCtx) { ctxBuf.push(row); }
    else {
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

function tokenise(text) {
  return text.match(/\S+|\s+/g) || [];
}

function lcs(a, b) {
  const m = a.length, n = b.length;
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

  // First pass: build an array of "redline items" — either context lines or change blocks
  const items = [];
  let i = 0;
  while (i < hunks.length) {
    const h = hunks[i];
    if (h.type === "context") {
      items.push({ kind: "context", hunk: h });
      i++;
    } else {
      const removed = [], added = [];
      while (i < hunks.length && hunks[i].type !== "context") {
        if (hunks[i].type === "removed") removed.push(hunks[i]);
        else added.push(hunks[i]);
        i++;
      }
      const oldText   = removed.map(r => r.text).join(" ");
      const newText   = added.map(a => a.text).join(" ");
      const lineLabel = removed.length ? removed[0].line_a : (added.length ? added[0].line_b : "");
      const ops       = lcs(tokenise(oldText), tokenise(newText));
      items.push({ kind: "change", lineLabel, ops });
    }
  }

  // Second pass: collapse context runs, then render
  let html = "";
  let ctxBuf = [];

  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      for (const item of ctxBuf) {
        html += `<div class="redline-line context">
          <span class="redline-gutter">${item.hunk.line_a}</span>
          <span class="redline-text">${esc(item.hunk.text)}</span>
        </div>`;
      }
    } else {
      for (const item of ctxBuf.slice(0, CTX)) {
        html += `<div class="redline-line context">
          <span class="redline-gutter">${item.hunk.line_a}</span>
          <span class="redline-text">${esc(item.hunk.text)}</span>
        </div>`;
      }
      html += `<div class="redline-line context">
        <span class="redline-gutter"></span>
        <span class="redline-text" style="color:var(--text-dim)">&#8230;</span>
      </div>`;
      for (const item of ctxBuf.slice(-CTX)) {
        html += `<div class="redline-line context">
          <span class="redline-gutter">${item.hunk.line_a}</span>
          <span class="redline-text">${esc(item.hunk.text)}</span>
        </div>`;
      }
    }
    ctxBuf = [];
  }

  for (const item of items) {
    if (item.kind === "context") {
      ctxBuf.push(item);
    } else {
      flushCtx();
      html += `<div class="redline-line change">
        <span class="redline-gutter">${item.lineLabel}</span>
        <span class="redline-text">${wordDiffHtml(item.ops)}</span>
      </div>`;
    }
  }
  flushCtx();

  return diffStats(hunks) + `<div class="redline-viewer">${html}</div>`;
}

// ── Risk renderer ─────────────────────────────────────────────────

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

  const riskMap = {};
  for (const c of (riskData.changes || [])) {
    riskMap[c.index] = c;
  }

  const blocks = groupChangeBlocks(hunks);

  // Map each hunk to its block index
  const hunkBlockIdx = new Map();
  let b = 0;
  for (let hi = 0; hi < hunks.length; hi++) {
    if (hunks[hi].type === "context") continue;
    if (b < blocks.length && blocks[b].includes(hunks[hi])) {
      hunkBlockIdx.set(hi, b);
      if (hunks[hi] === blocks[b][blocks[b].length - 1]) b++;
    }
  }

  const LABEL = {
    risk_increase: "Risk \u25b2",
    risk_decrease: "Risk \u25bc",
    neutral:       "Neutral",
  };

  const CLAUSE_LABEL = {
    payment_terms:    "Payment",
    liability:        "Liability",
    indemnification:  "Indemnity",
    ip_ownership:     "IP",
    termination:      "Termination",
    governing_law:    "Governing Law",
    confidentiality:  "Confidentiality",
    representations:  "Representations",
    force_majeure:    "Force Majeure",
    other:            "Other",
  };

  function riskAnnotation(risk) {
    const mitigation = risk.mitigation && risk.mitigation !== "No action required"
      ? `<p class="risk-mitigation"><strong>Mitigation:</strong> ${esc(risk.mitigation)}</p>`
      : "";
    return `<div class="risk-explanation">${esc(risk.explanation)}${mitigation}</div>`;
  }

  let lines = "";
  let ctxBuf = [];
  let currentBlock = -1;
  let badgeEmitted = false;

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

  for (let hi = 0; hi < hunks.length; hi++) {
    const h = hunks[hi];

    if (h.type === "context") {
      if (currentBlock >= 0) {
        const risk = riskMap[currentBlock];
        if (risk) ctxBuf.push(riskAnnotation(risk));
        currentBlock = -1;
        badgeEmitted = false;
      }
      ctxBuf.push(`<div class="diff-line context">
        <span class="diff-gutter">${h.line_a ?? ""}</span>
        <span class="diff-gutter">${h.line_b ?? ""}</span>
        <span class="diff-prefix">&nbsp;</span>
        <span class="diff-text">${esc(h.text)}</span>
      </div>`);
    } else {
      flushCtx();

      const blockIdx = hunkBlockIdx.get(hi) ?? -1;
      if (blockIdx !== currentBlock) { currentBlock = blockIdx; badgeEmitted = false; }

      const risk = riskMap[currentBlock];
      const riskClass = risk ? ` ${risk.risk}` : "";
      const showBadge = risk && !badgeEmitted;
      if (showBadge) badgeEmitted = true;

      const prefix = h.type === "added" ? "+" : "&#8722;";
      const clauseTag = (showBadge && risk.clause_type)
        ? `<span class="clause-type-tag">${esc(CLAUSE_LABEL[risk.clause_type] || risk.clause_type)}</span>`
        : "";
      const severityTag = (showBadge && risk.severity)
        ? `<span class="severity-badge severity-${risk.severity}">${esc(risk.severity)}</span>`
        : "";
      const badge = showBadge
        ? `${clauseTag}${severityTag}<span class="risk-badge ${risk.risk}">${LABEL[risk.risk] || risk.risk}</span>`
        : "";

      lines += `<div class="diff-line ${h.type}${riskClass}">
        <span class="diff-gutter">${h.line_a ?? ""}</span>
        <span class="diff-gutter">${h.line_b ?? ""}</span>
        <span class="diff-prefix">${prefix}</span>
        <span class="diff-text">${esc(h.text)}${badge}</span>
      </div>`;
    }
  }

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
