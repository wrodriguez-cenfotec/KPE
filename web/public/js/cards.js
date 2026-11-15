import { esc, formatColones, formatKm } from "./api.js";
import { carPhoto } from "./car.js";
import { label } from "./labels.js";

export function card(v) {
  const badge = v.status === "reserved" ? '<span class="badge badge-warning">Reservado</span>' : "";
  return `<a href="/vehicle.html?id=${encodeURIComponent(v.id)}" class="card bg-base-100 shadow hover:shadow-lg transition">
    <figure class="p-2">${carPhoto(v)}</figure>
    <div class="card-body p-4 gap-1">
      <h2 class="card-title text-base">${esc(v.brand)} ${esc(v.model)} ${v.year} ${badge}</h2>
      <p class="text-sm opacity-70">${formatKm(v.km)} · ${esc(label("transmission", v.transmission))} · ${esc(label("fuel", v.fuel))}</p>
      <p class="text-xl font-bold">${formatColones(v.price)}</p>
    </div></a>`;
}
