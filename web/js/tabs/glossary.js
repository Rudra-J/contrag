import { getGlossary } from "../api.js";

let _toast;
let _allGlossary = {};

function renderGlossary(glossary) {
  _allGlossary = glossary;
  const el = document.getElementById("glossary-content");
  const terms = Object.keys(glossary).sort();
  if (!terms.length) {
    el.innerHTML = `<div class="empty-state"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-dim)" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg><p>No glossary terms yet. Ingest a contract first.</p></div>`;
    return;
  }
  el.innerHTML = `
    <input class="glossary-search" type="text" id="glossary-search" placeholder="Search terms (e.g. indemnity, force majeure…)" autocomplete="off">
    <div class="glossary-count" id="glossary-count">${terms.length} term(s)</div>
    <div class="glossary-grid" id="glossary-grid"></div>
  `;
  renderTerms(terms, glossary);

  document.getElementById("glossary-search").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    const filtered = q ? terms.filter(t => t.includes(q)) : terms;
    document.getElementById("glossary-count").textContent = `${filtered.length} term(s)`;
    renderTerms(filtered, glossary);
  });
}

function renderTerms(terms, glossary) {
  const grid = document.getElementById("glossary-grid");
  if (!grid) return;
  grid.innerHTML = terms.map(term => termCard(term, glossary[term])).join("");

  grid.querySelectorAll(".term-header").forEach(h => {
    h.addEventListener("click", () => {
      const card = h.closest(".term-card");
      card.classList.toggle("open");
      h.setAttribute("aria-expanded", card.classList.contains("open"));
    });
    h.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); h.click(); } });
  });

  grid.querySelectorAll(".source-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const pop = chip.nextElementSibling;
      const isVisible = pop.classList.toggle("visible");
      chip.setAttribute("aria-expanded", isVisible);
    });
    chip.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); chip.click(); } });
  });
}

function hl(text, term) {
  if (!text || !term) return text || "";
  const re = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
  return text.replace(re, m => `<mark class="term-hl">${m}</mark>`);
}

function termCard(term, entry) {
  if (!entry) return "";
  const sources = (entry.sources || []).map(src => {
    const highlighted = hl(src.chunk || "", term);
    return `<span class="source-chip" role="button" tabindex="0" aria-expanded="false">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        ${src.file} &middot; &sect;${(src.chunk_index || 0) + 1}
      </span>
      <div class="source-popover" role="region" aria-label="Source excerpt for ${term}">${highlighted || "(no excerpt)"}</div>`;
  }).join("");

  const title = term.charAt(0).toUpperCase() + term.slice(1);
  return `
    <div class="term-card" data-term="${term}">
      <div class="term-header" role="button" tabindex="0" aria-expanded="false">
        <h3>${title}</h3>
        <svg class="term-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>
      </div>
      <div class="term-body">
        <div class="term-field"><label>Legal definition</label><p>${entry.legal || ""}</p></div>
        <div class="term-field"><label>Plain English</label><p>${entry.layman || ""}</p></div>
        <div class="term-field"><label>Example</label><p><em>${entry.example || ""}</em></p></div>
        <div class="term-field"><label>Sources</label>${sources || "<p style='color:var(--text-dim);font-size:0.8rem'>No sources available.</p>"}</div>
      </div>
    </div>
  `;
}

export async function initGlossary(toast) {
  _toast = toast;
  const glossary = await getGlossary();
  renderGlossary(glossary);

  document.querySelector('[data-tab="glossary"]').addEventListener("click", async () => {
    const g = await getGlossary();
    renderGlossary(g);
  });
}
