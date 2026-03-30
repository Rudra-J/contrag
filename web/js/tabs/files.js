import { getFiles, uploadFile, deleteFile } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

function fileIcon() {
  return `<svg class="file-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;
}

function renderFiles(files) {
  const el = document.getElementById("files-content");
  // Remove any existing file-list (keep upload zone)
  const existing = el.querySelector(".file-list");
  if (existing) existing.remove();

  if (!files.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-dim)" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><p>No contracts uploaded yet.</p>`;
    el.appendChild(empty);
    return;
  }

  // Remove any empty state
  const emptyEl = el.querySelector(".empty-state");
  if (emptyEl) emptyEl.remove();

  const list = document.createElement("div");
  list.className = "file-list";
  list.innerHTML = files.map(f => `
    <div class="file-row" data-name="${f.name}">
      ${fileIcon()}
      <span class="file-name">${f.name}</span>
      <span class="file-meta">${f.size_kb} KB &middot; ${f.uploaded_at.slice(0,10)}</span>
      <button class="btn btn-danger del-btn" data-name="${f.name}" aria-label="Delete ${f.name}">Remove</button>
    </div>`).join("");
  el.appendChild(list);

  el.querySelectorAll(".del-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm(`Remove ${btn.dataset.name}?`)) return;
      try {
        await deleteFile(btn.dataset.name);
        _toast(`${btn.dataset.name} removed.`, "success");
        const files = await getFiles();
        renderFiles(files);
      } catch(e) { _toast(String(e), "error"); }
    });
  });
}

async function refresh() {
  const files = await getFiles();
  renderFiles(files);
}

function buildUploadZone(container) {
  const zone = document.createElement("div");
  zone.className = "upload-zone card";
  zone.innerHTML = `
    <span class="upload-zone-icon" aria-hidden="true">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--gold)"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
    </span>
    <p><strong>Click to upload</strong> or drag &amp; drop</p>
    <p>PDF, DOCX, TXT</p>
    <input type="file" accept=".pdf,.docx,.txt" multiple aria-label="Upload contracts">
  `;
  const input = zone.querySelector("input");

  async function handleFiles(files) {
    for (const file of files) {
      showLoader(`Ingesting ${file.name}\u2026`);
      try {
        await uploadFile(file);
        _toast(`${file.name} ingested.`, "success");
      } catch(e) {
        _toast(`Failed: ${e.message || e}`, "error");
      }
    }
    hideLoader();
    await refresh();
  }

  input.addEventListener("change", () => handleFiles(Array.from(input.files)));
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    handleFiles(Array.from(e.dataTransfer.files));
  });

  container.appendChild(zone);
}

export async function initFiles(toast) {
  _toast = toast;
  const container = document.getElementById("files-content");
  buildUploadZone(container);
  const files = await getFiles();
  renderFiles(files);
}
