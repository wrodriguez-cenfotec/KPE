import { api, esc } from "../api.js";
import { renderLayout } from "../layout.js";

/** Renders the layout and, when there is no staff session, the shared password form. */
export async function requireStaff() {
  const session = await renderLayout({ zone: "staff" });
  if (session.role === "staff") return session;
  document.getElementById("main").innerHTML = `<div class="card bg-base-100 max-w-sm mx-auto mt-10"><div class="card-body">
    <h1 class="card-title">Gestión</h1><p class="text-sm opacity-70">Ingrese la contraseña del equipo.</p>
    <form id="staff-login" class="grid gap-2"><input type="password" name="password" class="input input-bordered" placeholder="Contraseña" required>
    <button class="btn btn-primary">Ingresar</button><p id="err" class="text-error text-sm"></p></form></div></div>`;
  document.getElementById("staff-login").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/auth/staff", { method: "POST", body: { password: e.target.password.value } });
      location.reload();
    } catch (err) {
      document.getElementById("err").textContent = err.message;
    }
  });
  return null;
}

export function table(columns, rows) {
  const head = columns.map(([, label]) => `<th>${esc(label)}</th>`).join("");
  const body = rows.map((r) => `<tr>${columns.map(([key, , fmt]) => `<td>${fmt ? fmt(r[key], r) : esc(r[key])}</td>`).join("")}</tr>`).join("");
  return `<div class="overflow-x-auto card bg-base-100"><table class="table table-sm table-zebra"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
