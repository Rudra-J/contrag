import { getFiles, getDiff } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

function buildSelectors(files) {
  const names = files.map(f => f.name);
  if (names.length < 2) {
    return `<div class="empty-state"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-dim)" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg><p>Upload at least 2 contracts to compare.</p></div>`;
  }
  const opts = names.map(n => `<option value="${n}">${n}</option>`).join("");
  const opts2 = [...names.slice(1), names[0]].map(n => `<option value="${n}">${n}</option>`).join("");
  return `
    <div class="card">
      <div class="diff-selectors">
        <label>Base contract<select id="diff-a">${opts}</select></label>
        <label>Compare contract<select id="diff-b">${opts2}</select></label>
        <button class="btn btn-primary" id="diff-btn">Compare</button>
      </div>
    </div>
    <div id="diff-result"></div>
  `;
}

const CTX = 3;

function renderDiff(hunks) {
  if (!hunks.length) {
    return `<div class="empty-state"><p>The contracts are identical.</p></div>`;
  }
  const added   = hunks.filter(h => h.type === "added").length;
  const removed = hunks.filter(h => h.type === "removed").length;

  let lines = "";
  let ctxBuf = [];

  function flushCtx() {
    if (ctxBuf.length <= CTX * 2) {
      ctxBuf.forEach(h => { lines += hunkHtml(h); });
    } else {
      ctxBuf.slice(0, CTX).forEach(h => { lines += hunkHtml(h); });
      lines += `<div class="diff-line ellipsis"><span style="padding:0 8px;color:var(--text-dim)">&#8230;</span></div>`;
      ctxBuf.slice(-CTX).forEach(h => { lines += hunkHtml(h); });
    }
    ctxBuf = [];
  }

  for (const h of hunks) {
    if (h.type === "context") { ctxBuf.push(h); }
    else { flushCtx(); lines += hunkHtml(h); }
  }
  flushCtx();

  return `
    <div class="diff-stats">
      <span class="add">+${added} additions</span> &nbsp;
      <span class="rem">&#8722;${removed} removals</span>
    </div>
    <div class="diff-viewer">${lines}</div>
  `;
}

function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;");
}

function hunkHtml(h) {
  const prefix = h.type === "added" ? "+" : h.type === "removed" ? "&#8722;" : "&nbsp;";
  const la = h.line_a ?? "";
  const lb = h.line_b ?? "";
  return `<div class="diff-line ${h.type}">
    <span class="diff-gutter">${la}</span>
    <span class="diff-gutter">${lb}</span>
    <span class="diff-prefix">${prefix}</span>
    <span class="diff-text">${esc(h.text)}</span>
  </div>`;
}

export async function initDiff(toast) {
  _toast = toast;
  const container = document.getElementById("diff-content");

  async function render() {
    const files = await getFiles();
    container.innerHTML = buildSelectors(files);

    const btn = document.getElementById("diff-btn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
      const a = document.getElementById("diff-a").value;
      const b = document.getElementById("diff-b").value;
      if (a === b) { _toast("Select two different contracts.", "error"); return; }
      showLoader("Comparing contracts\u2026");
      try {
        const { hunks } = await getDiff(a, b);
        document.getElementById("diff-result").innerHTML = renderDiff(hunks);
      } catch(e) {
        _toast(String(e), "error");
      } finally {
        hideLoader();
      }
    });
  }

  await render();
  document.querySelector('[data-tab="diff"]').addEventListener("click", render);
}
