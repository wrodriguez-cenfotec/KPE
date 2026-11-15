import { api, esc, formatDate } from "../api.js";
import { label } from "../labels.js";
import { marked } from "/vendor/marked.esm.js";
import { requireStaff } from "./common.js";

if (await requireStaff()) {
  const list = document.getElementById("list");
  const content = document.getElementById("content");

  const loadList = async (q = "") => {
    const rows = await api("/api/staff/conversations" + (q ? `?q=${encodeURIComponent(q)}` : ""));
    list.innerHTML = `<ul class="menu bg-base-100 rounded-box">${rows.map((s) => `<li><a data-id="${esc(s.id)}">
      <div><div class="font-mono text-xs">${esc(s.id)}</div><div class="text-xs opacity-70">${formatDate(s.started_at)} · ${esc(s.src_ip)} · ${esc(s.customer || label("role", s.role))}
      · ${s.message_count} mensajes ${s.useful ? "· útil" : ""}</div></div></a></li>`).join("")}</ul>`;
  };

  const show = async (id) => {
    const r = await api(`/api/staff/conversations/${encodeURIComponent(id)}`);
    const msgs = r.messages.map((m) => `<div class="chat ${m.role === "user" ? "chat-start" : "chat-end"}">
      <div class="chat-header text-xs opacity-70">${m.role === "user" ? "Cliente" : "Guachimán"} · ${formatDate(m.ts)}</div>
      <div class="chat-bubble ${m.role === "user" ? "" : "chat-bubble-primary"}">${marked.parse(m.content)}</div></div>`).join("");
    const acts = r.actions.map((a) => `<tr><td>${formatDate(a.ts)}</td><td>${esc(a.action)}</td><td class="font-mono text-xs">${esc(JSON.stringify(a.params))}</td>
      <td>${esc(label("actionStatus", a.status))}</td><td class="text-xs">${esc(a.result_summary)}</td></tr>`).join("");
    content.innerHTML = `<div class="card bg-base-100"><div class="card-body"><h2 class="card-title font-mono text-base">${esc(id)}</h2>${msgs}
      <h3 class="font-bold mt-4">Acciones del asistente</h3>
      <div class="overflow-x-auto"><table class="table table-xs"><thead><tr><th>Hora</th><th>Acción</th><th>Parámetros</th><th>Estado</th><th>Resultado</th></tr></thead>
      <tbody>${acts || "<tr><td colspan=5>Sin acciones</td></tr>"}</tbody></table></div></div></div>`;
  };

  list.addEventListener("click", (e) => { const a = e.target.closest("[data-id]"); if (a) show(a.dataset.id); });
  document.getElementById("search").addEventListener("submit", (e) => { e.preventDefault(); loadList(e.target.q.value); });
  await loadList();
}
