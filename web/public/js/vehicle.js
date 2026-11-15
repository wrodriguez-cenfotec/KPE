import { api, esc, formatColones, formatKm, qs } from "./api.js";
import { carPhoto } from "./car.js";
import { label } from "./labels.js";
import { renderLayout } from "./layout.js";

const session = await renderLayout();
const id = qs("id");
const detail = document.getElementById("detail");

/** Traffic light for the inspection result: code, emoji and tile colors. */
const LIGHTS = [["excellent", "🟢", "border-success bg-success/10"], ["acceptable", "🟡", "border-warning bg-warning/10"],
  ["needs_repairs", "🔴", "border-error bg-error/10"]];

try {
  const v = await api(`/api/inventory/${encodeURIComponent(id)}`);
  document.title = `${v.brand} ${v.model} ${v.year} | Kilometreados Pero Enteritos`;
  detail.innerHTML = `<div class="card lg:card-side bg-base-100 shadow">
    <figure class="lg:w-1/2 p-4 flex-col items-stretch">${carPhoto(v, { eager: true })}
      <figcaption class="text-xs opacity-70 mt-2">Foto de referencia del modelo. El color y el equipamiento pueden variar. <a href="/credits.html" class="link">Créditos de las fotos</a></figcaption></figure>
    <div class="card-body">
      <h1 class="card-title text-2xl">${esc(v.brand)} ${esc(v.model)} ${v.year}</h1>
      <p class="text-3xl font-bold">${formatColones(v.price)}</p>
      <dl class="grid grid-cols-2 sm:grid-cols-3 gap-2">${specs(v)}</dl>
      <p>${esc(v.description)}</p>
      ${inspection(v)}
      <div class="card-actions justify-end">
        <button id="btn-finance" class="btn">Simular financiamiento</button>
        <button id="btn-reserve" class="btn btn-primary" ${v.status !== "available" ? "disabled" : ""}>Reservar</button>
      </div>
    </div></div>`;
  setupFinance(v);
  setupReserve(v);
  const sim = await api(`/api/inventory/${encodeURIComponent(id)}/similar`);
  const { card } = await import("./cards.js");
  document.getElementById("similar").innerHTML = sim.items.map(card).join("") || "<p class='opacity-70'>Sin sugerencias por ahora.</p>";
} catch (err) {
  detail.innerHTML = `<div class="alert alert-warning">${esc(err.message)}</div>`;
}

function specs(v) {
  const items = [["Kilometraje", formatKm(v.km)], ["Transmisión", label("transmission", v.transmission)], ["Combustible", label("fuel", v.fuel)],
    ["Carrocería", label("body", v.body)], ["Color", label("color", v.color)], ["Código", v.id]];
  return items.map(([name, value]) => `<div class="rounded-lg bg-primary/5 border border-primary/15 px-3 py-2">
    <dt class="text-xs font-semibold text-primary">${name}</dt><dd class="font-semibold">${esc(value)}</dd></div>`).join("");
}

/** Inspection summary with the traffic light. The lit light matches the stored status. */
function inspection(v) {
  const current = LIGHTS.find(([code]) => code === v.inspection_status) || LIGHTS[1];
  const lights = LIGHTS.map(([code, emoji]) => `<span class="${code === current[0] ? "" : "opacity-20 grayscale"}" title="${label("inspection", code)}">${emoji}</span>`).join("");
  return `<section class="rounded-lg border-l-4 ${current[2]} p-4" aria-label="Resumen de inspección">
    <h2 class="font-bold text-lg">Resumen de inspección</h2>
    <p class="flex items-center gap-3 mt-1"><span class="text-xl tracking-widest" aria-hidden="true">${lights}</span>
      <span class="font-semibold">${label("inspection", current[0])}</span></p>
    <p class="mt-1">${esc(v.inspection_summary)}</p></section>`;
}

function setupFinance(v) {
  const dlg = document.getElementById("finance");
  const f = document.getElementById("finance-form");
  f.price.value = v.price;
  const calc = () => {
    const principal = v.price * (1 - Number(f.down_payment.value) / 100);
    const r = Number(f.rate.value) / 100 / 12;
    const n = Number(f.term.value);
    const payment = r ? (principal * r) / (1 - Math.pow(1 + r, -n)) : principal / n;
    document.getElementById("payment").textContent = formatColones(payment);
  };
  f.addEventListener("input", calc);
  calc();
  document.getElementById("btn-finance").addEventListener("click", () => dlg.showModal());
}

function setupReserve(v) {
  const dlg = document.getElementById("reserve");
  const body = document.getElementById("reserve-body");
  document.getElementById("btn-reserve").addEventListener("click", () => {
    if (session.role !== "customer") {
      body.innerHTML = `<h3 class="font-bold text-lg">Inicie sesión para reservar</h3>
        <p class="py-2">Las reservas son solo para clientes registrados.</p>
        <div class="modal-action"><a class="btn btn-primary" href="/login.html?next=${encodeURIComponent(location.pathname + location.search)}">Ingresar</a>
        <form method="dialog"><button class="btn">Cerrar</button></form></div>`;
      return dlg.showModal();
    }
    body.innerHTML = `<h3 class="font-bold text-lg">Reservar ${esc(v.brand)} ${esc(v.model)} ${v.year}</h3>
      <p class="py-2">El depósito de reserva es de <b>₡100,000</b> y se paga por SINPE Móvil.</p>
      <label class="label cursor-pointer justify-start gap-2"><input type="radio" checked class="radio radio-sm"> SINPE Móvil</label>
      <div class="modal-action"><button id="confirm" class="btn btn-primary">Confirmar reserva</button>
      <form method="dialog"><button class="btn">Cancelar</button></form></div>`;
    dlg.showModal();
    document.getElementById("confirm").addEventListener("click", async () => {
      try {
        const r = await api("/api/reservations", { method: "POST", body: { vehicle_id: v.id } });
        body.innerHTML = `<h3 class="font-bold text-lg">Reserva ${esc(r.reservation)} registrada</h3>
          <p class="py-2">Envíe <b>₡100,000</b> por SINPE Móvil al número oficial de KPE <b>${esc(r.sinpe_number)}</b>
          e indique el código <b>${esc(r.reservation)}</b> en el detalle. Nuestro personal confirma la reserva en horario de oficina.</p>
          <div class="modal-action"><a href="/account.html" class="btn btn-primary">Ver mis reservas</a></div>`;
      } catch (err) {
        body.innerHTML = `<p class="text-error">${esc(err.message)}</p><div class="modal-action"><form method="dialog"><button class="btn">Cerrar</button></form></div>`;
      }
    });
  });
}
