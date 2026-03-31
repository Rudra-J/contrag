import { getFiles, streamChat, getChatContext } from "../api.js";

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

// ── Thinking animation ───────────────────────────────────────────

function setThinking(active) {
  const btn = document.getElementById("chat-send");
  if (!btn) return;
  if (active) {
    btn.classList.add("thinking");
    btn.disabled = true;
  } else {
    btn.classList.remove("thinking");
    btn.disabled = false;
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

/**
 * Inject a scope indicator row directly after the message element.
 */
function renderScopeIndicator(afterMsgId, sources) {
  if (!sources || sources.length === 0) return;
  const msgEl = document.getElementById(afterMsgId);
  if (!msgEl) return;
  const chips = sources.map(s => `<span class="scope-file">${esc(s)}</span>`).join("");
  const div = document.createElement("div");
  div.className = "scope-indicator";
  div.innerHTML = `<span class="scope-label">Scope:</span>${chips}`;
  msgEl.insertAdjacentElement("afterend", div);
}

/**
 * Append a collapsible sources panel inside the assistant bubble.
 */
function appendSources(msgId, chunks) {
  if (!chunks || chunks.length === 0) return;
  const bubble = document.querySelector(`#${msgId} .msg-bubble`);
  if (!bubble) return;

  const items = chunks.map(c => `
    <div class="source-item">
      <div class="source-file">${esc(c.source)}</div>
      <p class="source-text">${esc(c.text)}</p>
    </div>
  `).join("");

  const panel = document.createElement("div");
  panel.className = "sources-panel";
  panel.innerHTML = `
    <button class="sources-toggle" aria-expanded="false">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
      ${chunks.length} source${chunks.length !== 1 ? "s" : ""}
    </button>
    <div class="sources-list" role="list"></div>
  `;
  panel.querySelector(".sources-list").innerHTML = items;

  panel.querySelector(".sources-toggle").addEventListener("click", function () {
    const list = panel.querySelector(".sources-list");
    const open = list.classList.toggle("open");
    this.classList.toggle("open", open);
    this.setAttribute("aria-expanded", String(open));
  });

  bubble.appendChild(panel);
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

    const sources = _taggedSources.size > 0 ? [..._taggedSources] : [];

    const userMsgId = renderMessage("user", question);
    renderScopeIndicator(userMsgId, sources);

    setThinking(true);
    const replyId = renderMessage("assistant", "", true);

    let fullAnswer = "";
    let thinkingCleared = false;

    // Fire context fetch in parallel with the LLM stream
    let contextPromise = getChatContext(question, sources).then(r => r.docs ?? r).catch(() => []);

    streamChat(
      question,
      sources,
      (chunk) => {
        if (!thinkingCleared) { setThinking(false); thinkingCleared = true; }
        fullAnswer += chunk;
        updateMessage(replyId, fullAnswer, true);
      },
      async () => {
        if (!thinkingCleared) { setThinking(false); thinkingCleared = true; }
        updateMessage(replyId, fullAnswer, false);
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        const chunks = await contextPromise;
        appendSources(replyId, chunks);
      },
      (err) => {
        if (!thinkingCleared) { setThinking(false); thinkingCleared = true; }
        updateMessage(replyId, `Error: ${err}`, false);
        input.disabled = false;
        sendBtn.disabled = false;
      }
    );
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) sendMessage(); });
}
