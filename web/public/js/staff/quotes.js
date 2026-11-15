import { api, esc, formatColones, formatDate } from "../api.js";
import { label } from "../labels.js";
import { toast } from "../layout.js";
import { requireStaff, table } from "./common.js";

if (await requireStaff()) {
  const rows = await api("/api/staff/quotes");
  document.getElementById("content").innerHTML = table([
    ["id", "Cotización"], ["created_at", "Fecha", formatDate], ["vehicle_id", "Vehículo"], ["model", "Modelo"], ["customer_email", "Cliente"],
    ["discount_pct", "Descuento", (v) => `${Number(v)} %`], ["final_price", "Precio final", formatColones],
    ["created_via", "Origen", (v) => label("origin", v)], ["status", "Estado", (v) => label("quoteStatus", v)],
    ["seller_name", "Vendedor"], ["note", "Nota"],
    ["id", "", (id, r) => (r.status === "open" ? `<button class="btn btn-xs" data-close="${esc(id)}">Cerrar venta</button>` : "")],
  ], rows);
  document.getElementById("content").addEventListener("click", async (e) => {
    const id = e.target.dataset.close;
    if (!id) return;
    try {
      await api(`/api/staff/quotes/${id}/close`, { method: "POST" });
    } catch (err) {
      toast(err.message, "warning");
    }
  });
}
