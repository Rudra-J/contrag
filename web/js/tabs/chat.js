import { getFiles, streamChat } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

let _toast;
let _taggedSources = new Set();  // filenames currently tagged

// ── Tag picker ───────────────────────────────────────────────────

async function refreshTagPicker() {
  const row = document.getElementById("chat-tag-row");
  const hint = document.getElementById("chat-scope-hint");
  if (!row) return;

  let files = [];
  try { files = await getFiles(); } catch (_) { /* ignore */ }

  // Prune tags for files that no longer exist
  const validNames = new Set(files.map(f => f.name));
  for (const s of _taggedSources) {
    if (!validNames.has(s)) _taggedSources.delete(s);
  }

  if (!files.length) {
    row.innerHTML = `<span class="chat-tag-label">No files uploaded</span>`;
    if (hint) hint.textContent = "";
    return;
  }

  row.innerHTML = `<span class="chat-tag-label">Scope:</span>` +
    files.map(f => {
      const active = _taggedSources.has(f.name) ? " active" : "";
      return `<button class="file-tag${active}" data-name="${esc(f.name)}" title="${esc(f.name)}" aria-pressed="${_taggedSources.has(f.name)}">
        <span class="tag-dot"></span><span class="tag-name">${esc(f.name)}</span>
      </button>`;
    }).join("");

  row.querySelectorAll(".file-tag").forEach(btn => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.name;
      if (_taggedSources.has(name)) {
        _taggedSources.delete(name);
        btn.classList.remove("active");
        btn.setAttribute("aria-pressed", "false");
      } else {
        _taggedSources.add(name);
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
      }
      updateHint();
    });
  });

  updateHint();
}

function updateHint() {
  const hint = document.getElementById("chat-scope-hint");
  if (!hint) return;
  if (_taggedSources.size === 0) {
    hint.textContent = "Searching all uploaded contracts.";
  } else {
    const names = [..._taggedSources].join(", ");
    hint.textContent = `Scoped to: ${names}`;
  }
}

// ── Messages ─────────────────────────────────────────────────────

function scrollToBottom() {
  const el = document.getElementById("chat-messages");
  el.scrollTop = el.scrollHeight;
}

function renderMessage(role, content, streaming = false) {
  const el = document.getElementById("chat-messages");
  const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const avatar = role === "user" ? "U" : "⚖";
  el.insertAdjacentHTML("beforeend", `
    <div class="message ${role}" id="${id}">
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-bubble">${content}${streaming ? '<span class="cursor">&#9608;</span>' : ""}</div>
    </div>
  `);
  scrollToBottom();
  return id;
}

function updateMessage(id, content, streaming = false) {
  const bubble = document.querySelector(`#${id} .msg-bubble`);
  if (!bubble) return;
  bubble.innerHTML = content + (streaming ? '<span class="cursor">&#9608;</span>' : "");
  scrollToBottom();
}

// ── Init ─────────────────────────────────────────────────────────

export function initChat(toast) {
  _toast = toast;
  const input   = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

  refreshTagPicker();

  // Refresh tag picker when switching to chat tab (new files may have been uploaded)
  document.querySelector('[data-tab="chat"]').addEventListener("click", refreshTagPicker);

  function sendMessage() {
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    input.disabled = true;
    sendBtn.disabled = true;

    renderMessage("user", question);

    showLoader("Thinking…");
    const replyId = renderMessage("assistant", "", true);

    let fullAnswer = "";
    let loaderHidden = false;

    const sources = _taggedSources.size > 0 ? [..._taggedSources] : [];

    streamChat(
      question,
      sources,
      (chunk) => {
        if (!loaderHidden) { hideLoader(); loaderHidden = true; }
        fullAnswer += chunk;
        updateMessage(replyId, fullAnswer, true);
      },
      () => {
        if (!loaderHidden) { hideLoader(); loaderHidden = true; }
        updateMessage(replyId, fullAnswer, false);
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
      },
      (err) => {
        if (!loaderHidden) { hideLoader(); loaderHidden = true; }
        updateMessage(replyId, `Error: ${err}`, false);
        input.disabled = false;
        sendBtn.disabled = false;
      }
    );
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) sendMessage(); });
}
