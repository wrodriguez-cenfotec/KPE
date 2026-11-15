import { api, qs } from "./api.js";
import { renderLayout } from "./layout.js";

await renderLayout();
const form = document.getElementById("login");
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/auth/login", { method: "POST", body: { email: form.email.value, password: form.password.value } });
    location.href = qs("next") || "/account.html";
  } catch (err) {
    document.getElementById("error").textContent = err.message;
  }
});
