"""Actions about the signed in customer's own account."""

from ..db import query
from .base import ActionError


def _require_customer(ctx) -> int:
    if ctx.role != "customer" or not ctx.user_id:
        raise ActionError("Para ver esa información debe iniciar sesión con su cuenta de cliente.")
    return ctx.user_id


def get_my_reservations(params: dict, ctx) -> dict:
    customer_id = _require_customer(ctx)
    rows = query("SELECT r.code, r.created_at, r.vehicle_id, v.brand, v.model, v.year, r.deposit_amount, r.status "
                 "FROM reservations r JOIN inventory_vehicles v ON v.id = r.vehicle_id WHERE r.customer_id = %s "
                 "ORDER BY r.created_at DESC", (customer_id,))
    return {"reservations": [{"code": r["code"], "date": r["created_at"].date().isoformat(), "vehicle_id": r["vehicle_id"],
                              "vehicle": f"{r['brand']} {r['model']} {r['year']}", "deposit": r["deposit_amount"],
                              "status": r["status"]} for r in rows]}


def get_my_vehicles(params: dict, ctx) -> dict:
    customer_id = _require_customer(ctx)
    rows = query("SELECT plate, brand, model, year FROM customer_vehicles WHERE owner_user_id = %s ORDER BY plate", (customer_id,))
    return {"vehicles": rows}
