import { api, esc } from "./api.js";
import { mountChat } from "./chat.js";

export const GUACHIMAN_AVATAR = `<img src="/img/wachiman-192.png" alt="" class="w-10 h-10 rounded-full" width="40" height="40">`;

export async function me() {
  try {
    return await api("/api/auth/me");
  } catch {
    return { role: "visitor" };
  }
}

export async function renderLayout({ zone = "public" } = {}) {
  const session = await me();
  const header = document.getElementById("navbar");
  const staff = zone === "staff";
  const link = (href, text) => `<a href="${href}"${location.pathname === href ? ' aria-current="page"' : ""}>${text}</a>`;
  const left = staff ? link("/", "Ver el sitio") : link("/", "Catálogo");
  let right = session.role === "customer"
    ? `${link("/account.html", "Mi cuenta")}<button id="logout" type="button">Salir</button>`
    : link("/login.html", "Ingresar");
  if (staff) right = session.role === "staff" ? '<button id="logout" type="button">Salir</button>' : "";
  const staffLinks = staff && session.role === "staff"
    ? `<nav class="kpe-nav flex flex-wrap justify-center gap-1 pb-2" aria-label="Gestión">
        ${link("/staff/", "Catálogo")}${link("/staff/reservations.html", "Reservas")}${link("/staff/quotes.html", "Cotizaciones")}
        ${link("/staff/conversations.html", "Conversaciones")}${link("/staff/data.html", "Consultas")}${link("/staff/audit.html", "Auditoría")}</nav>`
    : "";
  header.innerHTML = `<div class="kpe-header">
    <div class="max-w-6xl mx-auto px-4 py-3 grid grid-cols-2 md:grid-cols-[1fr_auto_1fr] items-center gap-y-3">
      <nav class="kpe-nav order-2 md:order-1 flex gap-1 justify-start" aria-label="Principal">${left}</nav>
      <div class="order-1 md:order-2 col-span-2 md:col-span-1 flex justify-center">
        <a href="${staff ? "/staff/" : "/"}" class="kpe-plate" aria-label="Kilometreados Pero Enteritos${staff ? ", Gestión" : ", ir al catálogo"}">
          <span class="kpe-plate-band">${staff ? "Gestión" : "Costa Rica"}</span>
          <span class="kpe-plate-name">Kilometreados Pero Enteritos</span>
        </a>
      </div>
      <div class="kpe-nav order-3 flex gap-1 justify-end">${right}</div>
    </div>
    ${staffLinks}
    <div class="kpe-road" aria-hidden="true"></div></div>
    <div id="bootstrap-banner"></div>`;
  document.getElementById("logout")?.addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    location.href = zone === "staff" ? "/staff/" : "/";
  });
  checkBootstrap();
  mountChat(session);
  return session;
}

async function checkBootstrap() {
  try {
    const s = await api("/api/admin/bootstrap/status");
    if (s.stage !== "ready") {
      document.getElementById("bootstrap-banner").innerHTML = `<div class="alert alert-info rounded-none text-sm">
        Estamos preparando la búsqueda inteligente y el asistente. El sitio ya funciona, Guachimán estará listo en unos minutos.</div>`;
    }
  } catch {
    /* status is informative only */
  }
}

export function toast(msg, kind = "info") {
  const el = document.createElement("div");
  el.className = "toast toast-end z-50";
  el.innerHTML = `<div class="alert alert-${kind}"><span>${esc(msg)}</span></div>`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
