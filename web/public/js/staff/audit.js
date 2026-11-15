import { api } from "../api.js";
import { label } from "../labels.js";
import { requireStaff, table } from "./common.js";

if (await requireStaff()) {
  const load = async () => {
    const rows = await api("/api/staff/audit");
    document.getElementById("content").innerHTML = table([
      ["id", "#"], ["ts_naive", "Fecha y hora"], ["event", "Evento", (v) => label("auditEvent", v)], ["detail", "Detalle"],
      ["subject_text", "Usuario o dato"],
    ], rows);
  };
  document.getElementById("clear").addEventListener("click", async () => {
    await api("/api/staff/audit/clear", { method: "POST" });
    load();
  });
  await load();
}
