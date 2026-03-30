const loader = document.getElementById("justice-loader");
const label  = document.getElementById("loader-label");
const app    = document.getElementById("app");

export function showLoader(text = "Analysing\u2026") {
  label.textContent = text;
  loader.classList.remove("hidden");
}

export function hideLoader() {
  loader.classList.add("hidden");
  if (app.style.display === "none") {
    app.style.display = "flex";
  }
}
