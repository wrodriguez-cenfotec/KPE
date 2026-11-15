import { api, esc, formatColones, formatDate } from "./api.js";
import { label } from "./labels.js";
import { renderLayout } from "./layout.js";

const session = await renderLayout();
const box = document.getElementById("account");
if (session.role !== "customer") {
  location.href = "/login.html?next=/account.html";
} else {
  const rows = await api("/api/reservations/mine");
  const badge = { pending: "badge-warning", confirmed: "badge-success", cancelled: "badge-ghost" };
  box.innerHTML = `<div class="flex flex-wrap items-center justify-between gap-2 mb-4"><p>Hola, ${esc(session.name)}.</p>
    <a href="/" class="btn btn-primary btn-sm">Ver carros disponibles</a></div>
    <div class="card bg-base-100"><div class="card-body"><h2 class="card-title">Mis reservas</h2>
    ${rows.length ? `<div class="overflow-x-auto"><table class="table"><thead><tr><th>Código</th><th>Vehículo</th><th>Fecha</th><th>Depósito</th><th>Estado</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td>${esc(r.code)}</td><td>${esc(r.brand)} ${esc(r.model)} ${r.year}</td><td>${formatDate(r.created_at)}</td>
      <td>${formatColones(r.deposit_amount)}</td><td><span class="badge ${badge[r.status] || ""}">${esc(label("reservationStatus", r.status))}</span></td></tr>`).join("")}
    </tbody></table></div>` : "<p>Todavía no tiene reservas.</p>"}</div></div>`;
}
