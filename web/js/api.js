const BASE = "";  // same origin

export async function getFiles() {
  const r = await fetch(`${BASE}/api/files`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${BASE}/api/files/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteFile(filename) {
  const r = await fetch(`${BASE}/api/files/${encodeURIComponent(filename)}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getDiff(a, b) {
  const r = await fetch(`${BASE}/api/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getGlossary(q = "") {
  const url = q ? `${BASE}/api/glossary?q=${encodeURIComponent(q)}` : `${BASE}/api/glossary`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/**
 * Streams chat via SSE. Calls onChunk(text) for each token.
 * Calls onDone() when stream ends. Calls onError(msg) on failure.
 * @param {string} question
 * @param {string[]} sources  - filenames to filter by; [] means all
 * @param {Function} onChunk
 * @param {Function} onDone
 * @param {Function} onError
 */
export function streamChat(question, sources, onChunk, onDone, onError) {
  fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, sources }),
  }).then(async (r) => {
    if (!r.ok) { onError(await r.text()); return; }
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") { onDone(); return; }
        if (payload.startsWith("ERROR:")) { onError(payload.slice(6)); return; }
        onChunk(payload.replace(/\\n/g, "\n"));
      }
    }
    onDone();
  }).catch(onError);
}
