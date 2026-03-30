import { streamChat } from "../api.js";
import { showLoader, hideLoader } from "../loader.js";

let _toast;

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

export function initChat(toast) {
  _toast = toast;
  const input   = document.getElementById("chat-input");
  const sendBtn = document.getElementById("chat-send");

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

    streamChat(
      question,
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
