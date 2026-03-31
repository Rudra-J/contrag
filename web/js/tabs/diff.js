import { getFiles, uploadFile, getDiff, getDiffRisk } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";
import { renderUnified, renderSideBySide, renderRedline, renderRisk } from "../diff-renderers.js";

let _toast;

// ── Cached diff state ─────────────────────────────────────────────
let _lastHunks    = null;
let _lastNameA    = null;
let _lastNameB    = null;
let _lastRiskData = null;
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
        <label class="btn btn-ghost diff-upload-btn" title="Upload a new contract for this slot">
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
  { id: "unified",      label: "Unified" },
  { id: "side-by-side", label: "Side by Side" },
  { id: "redline",      label: "Redline" },
  { id: "risk",         label: "Risk Analysis" },
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

// ── Inline scales loader HTML ─────────────────────────────────────

const INLINE_LOADER = (label) => `
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
    ${label}
  </div>`;

// ── Scroll sync for side-by-side ─────────────────────────────────

function wireSplitSync() {
  const left  = document.getElementById("split-left");
  const right = document.getElementById("split-right");
  if (!left || !right) return;
  let syncing = false;
  left.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    right.scrollTop = left.scrollTop;
    setTimeout(() => { syncing = false; }, 0);
  });
  right.addEventListener("scroll", () => {
    if (syncing) return;
    syncing = true;
    left.scrollTop = right.scrollTop;
    setTimeout(() => { syncing = false; }, 0);
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
      content.innerHTML = INLINE_LOADER("Analysing risks&hellip;");
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
      resultEl.innerHTML = INLINE_LOADER("Comparing contracts&hellip;");

      try {
        const { hunks } = await getDiff(a, b);
        _lastHunks    = hunks;
        _lastNameA    = a;
        _lastNameB    = b;
        _lastRiskData = null;
        _currentMode  = "unified";

        resultEl.innerHTML = buildResultWrapper(renderUnified(hunks));

        resultEl.querySelectorAll(".diff-mode-btn").forEach(modeBtn => {
          modeBtn.addEventListener("click", async () => {
            const mode = modeBtn.dataset.mode;
            if (mode === _currentMode) return;
            _currentMode = mode;
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
