import random

from ..db import query, query_one
from .base import ActionError

DEPOSIT = 100000
SINPE_NUMBER = "8000-0100"


def book_reservation(params: dict, ctx) -> dict:
    customer_id = params.get("customer_id") or ctx.user_id
    if not customer_id:
        raise ActionError("Para reservar debe iniciar sesión.")
    vehicle_id = str(params.get("vehicle_id", "")).strip().upper()
    vehicle = query_one("SELECT id, status FROM inventory_vehicles WHERE id = %s AND published", (vehicle_id,))
    if not vehicle:
        raise ActionError(f"No existe el vehículo {vehicle_id}.")
    if vehicle["status"] != "available":
        raise ActionError("Ese vehículo ya no está disponible.")
    code = f"RES-{random.randint(1000, 9999)}"
    query("INSERT INTO reservations (code, created_at, vehicle_id, customer_id, deposit_amount, status) "
          "VALUES (%s, now(), %s, %s, %s, 'pending')", (code, vehicle_id, customer_id, DEPOSIT))
    return {"reservation": code, "vehicle_id": vehicle_id, "deposit": DEPOSIT, "sinpe_number": SINPE_NUMBER, "status": "pending"}
