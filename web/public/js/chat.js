import { api, esc } from "./api.js";
import { marked } from "/vendor/marked.esm.js";

const STORAGE_KEY = "kpe_chat_session";

function renderMarkdown(text) {
  return marked.parse(esc(text));
}

function tableHtml(table) {
  if (!table || !table.columns?.length) return "";
  const head = table.columns.map((c) => `<th>${esc(c)}</th>`).join("");
  const rows = table.rows.map((r) => `<tr>${r.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("");
  return `<div class="overflow-x-auto max-h-64 mt-2"><table class="table table-xs table-zebra"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

export function mountChat(session) {
  const root = document.createElement("div");
  root.className = "fixed bottom-4 right-4 z-40";
  root.innerHTML = `
    <button id="chat-open" class="block w-16 h-16 rounded-full shadow-lg transition-transform hover:scale-105 motion-reduce:transition-none focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-yellow-400" aria-label="Hablar con Guachimán">
      <img src="/img/wachiman-192.png" alt="" class="w-16 h-16 rounded-full" width="64" height="64">
    </button>
    <div id="chat-panel" class="hidden card bg-base-100 shadow-2xl w-[22rem] max-w-[calc(100vw-2rem)]">
      <div class="card-body p-3 gap-2">
        <div class="flex items-center gap-2">
          <div id="chat-avatar"></div>
          <div class="flex-1"><p class="font-bold leading-tight">Guachimán</p><p class="text-xs opacity-70">Asistente virtual de KPE</p></div>
          <button id="chat-close" class="btn btn-ghost btn-sm btn-circle" aria-label="Cerrar">✕</button>
        </div>
        <div id="chat-log" class="h-80 overflow-y-auto flex flex-col gap-2 text-sm"></div>
        <form id="chat-form" class="join w-full">
          <input id="chat-input" class="input input-bordered input-sm join-item flex-1" placeholder="Escriba su consulta" autocomplete="off">
          <button class="btn btn-primary btn-sm join-item">Enviar</button>
        </form>
        <button id="chat-useful" class="btn btn-link btn-xs self-start hidden">¿Le fue útil esta conversación?</button>
      </div>
    </div>`;
  document.body.appendChild(root);
  import("./layout.js").then((m) => { root.querySelector("#chat-avatar").innerHTML = m.GUACHIMAN_AVATAR; });

  const log = root.querySelector("#chat-log");
  const panel = root.querySelector("#chat-panel");
  const useful = root.querySelector("#chat-useful");
  let sessionId = sessionStorage.getItem(STORAGE_KEY);

  const add = (role, html) => {
    const bubble = document.createElement("div");
    bubble.className = `chat ${role === "user" ? "chat-end" : "chat-start"}`;
    bubble.innerHTML = `<div class="chat-bubble ${role === "user" ? "chat-bubble-primary" : ""} prose prose-sm max-w-full">${html}</div>`;
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  };

  const greet = () => add("assistant", renderMarkdown(session.role === "staff"
    ? "Hola, soy Guachimán. ¿En qué le ayudo hoy con la gestión?"
    : "¡Hola! Soy Guachimán, el asistente de KPE. ¿Busca algún carro o tiene una consulta?"));

  const load = async () => {
    if (!sessionId) return greet();
    try {
      const h = await api(`/api/chat/${sessionId}`);
      if (!h.messages.length) return greet();
      h.messages.forEach((m) => add(m.role, m.role === "user" ? esc(m.content) : renderMarkdown(m.content)));
      useful.classList.remove("hidden");
    } catch {
      greet();
    }
  };

  root.querySelector("#chat-open").addEventListener("click", () => {
    panel.classList.toggle("hidden");
    if (!log.childElementCount) load();
  });
  root.querySelector("#chat-close").addEventListener("click", () => panel.classList.add("hidden"));

  root.querySelector("#chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = root.querySelector("#chat-input");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    add("user", esc(text));
    const waiting = add("assistant", '<span class="loading loading-dots loading-sm"></span>');
    try {
      const r = await api("/api/chat", { method: "POST", body: { message: text, session_id: sessionId } });
      sessionId = r.session_id;
      sessionStorage.setItem(STORAGE_KEY, sessionId);
      waiting.querySelector(".chat-bubble").innerHTML = renderMarkdown(r.answer) + tableHtml(r.table);
      useful.classList.remove("hidden");
    } catch (err) {
      waiting.querySelector(".chat-bubble").innerHTML = esc(err.message);
    }
    log.scrollTop = log.scrollHeight;
  });

  useful.addEventListener("click", async () => {
    if (!sessionId) return;
    const r = await api(`/api/chat/${sessionId}/useful`, { method: "POST" });
    useful.textContent = r.message;
    useful.disabled = true;
  });
}
