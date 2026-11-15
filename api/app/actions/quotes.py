from ..db import query, query_one
from .base import ActionError


def _next_quote_id() -> str:
    row = query_one("SELECT COALESCE(MAX(substring(id from 3)::int), 0) + 1 AS n FROM quotes")
    return f"Q-{row['n']:03d}"


def create_quote(params: dict, ctx) -> dict:
    vehicle_id = str(params.get("vehicle_id", "")).strip().upper()
    email = str(params.get("customer_email", "")).strip()
    try:
        discount = float(str(params.get("discount_pct", 0)).replace("%", "").strip() or 0)
    except ValueError:
        discount = 0.0
    note = str(params.get("note") or "").strip() or None
    vehicle = query_one("SELECT id, brand, model, year, price FROM inventory_vehicles WHERE id = %s", (vehicle_id,))
    if not vehicle:
        raise ActionError(f"No existe el vehículo {vehicle_id}.")
    if not email:
        raise ActionError("Falta el correo del cliente.")
    final_price = int(round(vehicle["price"] * (1 - discount / 100), -3))
    quote_id = _next_quote_id()
    via = "mcp" if ctx.source == "mcp" else "web_chat"
    query("INSERT INTO quotes (id, created_at, vehicle_id, customer_email, discount_pct, final_price, created_via, status, note) "
          "VALUES (%s, now(), %s, %s, %s, %s, %s, 'open', %s)", (quote_id, vehicle_id, email, discount, final_price, via, note))
    return {"quote_id": quote_id, "vehicle": f"{vehicle['brand']} {vehicle['model']} {vehicle['year']}",
            "list_price": vehicle["price"], "discount_pct": discount, "final_price": final_price, "note": note}
