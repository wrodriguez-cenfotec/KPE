import { api, formatColones, formatKm } from "../api.js";
import { label } from "../labels.js";
import { requireStaff, table } from "./common.js";

if (await requireStaff()) {
  const rows = await api("/api/staff/inventory");
  document.getElementById("content").innerHTML = table([
    ["id", "Código"], ["plate", "Placa"], ["brand", "Marca"], ["model", "Modelo"], ["year", "Año"], ["km", "Kilometraje", formatKm],
    ["price", "Precio", formatColones], ["status", "Estado", (v) => label("vehicleStatus", v)],
    ["published", "Publicado", (v) => (v ? "Sí" : "No")],
  ], rows);
}
