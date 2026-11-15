import { api, esc } from "./api.js";
import { card } from "./cards.js";
import { label } from "./labels.js";
import { renderLayout } from "./layout.js";

await renderLayout();

const form = document.getElementById("filters");
const grid = document.getElementById("grid");
const pager = document.getElementById("pager");
let page = 1;

async function loadFilters() {
  const f = await api("/api/inventory/filters");
  const fill = (name, values, group) => values.forEach((v) => form[name].insertAdjacentHTML("beforeend",
    `<option value="${esc(v)}">${esc(group ? label(group, v) : v)}</option>`));
  fill("brand", f.brands);
  fill("fuel", f.fuels, "fuel");
  fill("transmission", f.transmissions, "transmission");
}

async function load() {
  const data = Object.fromEntries(new FormData(form));
  if (data.semantic && data.q) {
    const r = await api("/api/inventory/search?" + new URLSearchParams({ q: data.q }));
    grid.innerHTML = r.items.map(card).join("") || `<p>${esc(r.message || "No encontramos vehículos.")}</p>`;
    document.getElementById("total").textContent = `${r.items.length} resultados de la búsqueda inteligente`;
    pager.innerHTML = "";
    return;
  }
  const params = new URLSearchParams({ page, page_size: 12 });
  for (const k of ["q", "brand", "fuel", "transmission", "price_max", "year_min"]) if (data[k]) params.set(k, data[k]);
  const r = await api("/api/inventory?" + params);
  grid.innerHTML = r.items.map(card).join("") || "<p>No encontramos vehículos con esos filtros.</p>";
  document.getElementById("total").textContent = `${r.total} vehículos`;
  const pages = Math.ceil(r.total / r.page_size);
  pager.innerHTML = Array.from({ length: pages }, (_, i) =>
    `<button class="join-item btn btn-sm ${i + 1 === page ? "btn-active" : ""}" data-page="${i + 1}">${i + 1}</button>`).join("");
}

form.addEventListener("submit", (e) => { e.preventDefault(); page = 1; load(); });
pager.addEventListener("click", (e) => { const p = e.target.dataset.page; if (p) { page = Number(p); load(); } });

await loadFilters();
await load();
