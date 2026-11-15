/** Small helpers shared by every page. */

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === "string" ? data.detail : "Ocurrió un error, intente de nuevo.");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

/** @param {number} n */
export const formatColones = (n) => "₡" + Math.round(Number(n)).toLocaleString("en-US");

export const formatKm = (n) => Number(n).toLocaleString("en-US") + " km";

/** @param {string} s */
export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("es-CR", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Costa_Rica" });
}

export const qs = (name) => new URLSearchParams(location.search).get(name);
