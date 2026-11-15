import { api, formatColones, formatDate } from "../api.js";
import { label } from "../labels.js";
import { requireStaff, table } from "./common.js";

if (await requireStaff()) {
  const rows = await api("/api/staff/reservations");
  document.getElementById("content").innerHTML = table([
    ["code", "Código"], ["created_at", "Fecha", formatDate], ["vehicle_id", "Vehículo"], ["model", "Modelo"], ["customer", "Cliente"],
    ["phone", "Teléfono"], ["deposit_amount", "Depósito", formatColones], ["status", "Estado", (v) => label("reservationStatus", v)],
    ["sinpe_ref", "Referencia SINPE"],
  ], rows);
}
