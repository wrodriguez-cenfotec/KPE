from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..actions import ActionContext, ActionError
from ..actions.reservations import book_reservation
from ..auth import require_customer
from ..db import query

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


class ReservationIn(BaseModel):
    vehicle_id: str


@router.post("")
def create(body: ReservationIn, request: Request):
    sess = require_customer(request)
    try:
        return book_reservation({"vehicle_id": body.vehicle_id}, ActionContext(source="web", role="customer", user_id=sess["user_id"]))
    except ActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/mine")
def mine(request: Request):
    sess = require_customer(request)
    return query("SELECT r.code, r.created_at, r.vehicle_id, v.brand, v.model, v.year, r.deposit_amount, r.status, r.sinpe_ref "
                 "FROM reservations r JOIN inventory_vehicles v ON v.id = r.vehicle_id WHERE r.customer_id = %s "
                 "ORDER BY r.created_at DESC", (sess["user_id"],))
