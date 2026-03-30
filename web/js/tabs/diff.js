import { getFiles, uploadFile, getDiff } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

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
        ${buildSlot("diff-b", "Compare contract", names, Math.min(1, names.length - 1))}
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

// ── Diff renderer ─────────────────────────────────────────────────

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
        // Reset input so the same file can be re-selected if needed
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

    // If called after an upload, pre-select the new file in the specified slot
    if (selectAfterUpload) {
      const select = document.getElementById(selectAfterUpload.slotId);
      if (select) select.value = selectAfterUpload.filename;
    }

    // Wire upload inputs
    wireUploadInputs(container, async (slotId, filename) => {
      await render({ slotId, filename });
    });

    // Wire compare button
    const btn = document.getElementById("diff-btn");
    if (!btn || btn.disabled) return;

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
  document.querySelector('[data-tab="diff"]').addEventListener("click", () => render());
}
