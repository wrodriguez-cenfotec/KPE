import { api, esc } from "../api.js";
import { requireStaff } from "./common.js";

if (await requireStaff()) {
  const content = document.getElementById("content");
  document.getElementById("ask").addEventListener("submit", async (e) => {
    e.preventDefault();
    content.innerHTML = '<span class="loading loading-dots"></span>';
    try {
      const r = await api("/api/staff/data-question", { method: "POST", body: { question: e.target.question.value } });
      if (r.error) {
        content.innerHTML = `<div class="alert alert-warning">${esc(r.error)}</div>`;
        return;
      }
      const head = r.columns.map((c) => `<th>${esc(c)}</th>`).join("");
      const rows = r.rows.map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("");
      content.innerHTML = `<p class="font-mono text-xs mb-2">${esc(r.sql)}</p><p class="text-sm mb-2">${r.total} filas</p>
        <div class="overflow-x-auto card bg-base-100"><table class="table table-sm"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
    } catch (err) {
      content.innerHTML = `<div class="alert alert-error">${esc(err.message)}</div>`;
    }
  });
}
