import { hideLoader } from "./loader.js";
import { initFiles }    from "./tabs/files.js";
import { initChat }     from "./tabs/chat.js";
import { initDiff }     from "./tabs/diff.js";
import { initGlossary } from "./tabs/glossary.js";

// ── Tab routing ──────────────────────────────────────────────────────
const navItems = document.querySelectorAll(".nav-item[data-tab]");
const panels   = document.querySelectorAll(".tab-panel");

function switchTab(name) {
  navItems.forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  panels.forEach(p => p.classList.toggle("active", p.id === `tab-${name}`));
}

navItems.forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ── Toast ────────────────────────────────────────────────────────────
export function toast(msg, type = "info", ms = 4000) {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), ms);
}

// ── Init ─────────────────────────────────────────────────────────────
(async () => {
  try {
    await initFiles(toast);
    initChat(toast);
    initDiff(toast);
    await initGlossary(toast);
  } catch(e) {
    console.error("Init error:", e);
  } finally {
    hideLoader();
  }
})();
