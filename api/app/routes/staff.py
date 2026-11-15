"""Back office endpoints used by the Gestión console."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..actions import ActionContext, run_action
from ..auth import require_staff
from ..db import query

router = APIRouter(prefix="/api/staff", tags=["staff"])


class DataQuestion(BaseModel):
    question: str


@router.get("/inventory")
def inventory(request: Request):
    require_staff(request)
    return query("SELECT id, plate, brand, model, year, km, price, status, published FROM inventory_vehicles ORDER BY id")


@router.get("/reservations")
def reservations(request: Request):
    require_staff(request)
    return query("SELECT r.code, r.created_at, r.vehicle_id, v.brand, v.model, u.full_name AS customer, u.phone, r.deposit_amount, "
                 "r.status, r.sinpe_ref FROM reservations r JOIN users u ON u.id = r.customer_id "
                 "JOIN inventory_vehicles v ON v.id = r.vehicle_id ORDER BY r.created_at DESC")


@router.get("/quotes")
def quotes(request: Request):
    require_staff(request)
    return query("SELECT q.id, q.created_at, q.vehicle_id, v.brand, v.model, v.year, v.price AS current_price, q.customer_email, "
                 "q.discount_pct, q.final_price, q.created_via, q.status, q.note, q.seller_name, q.sold_at "
                 "FROM quotes q JOIN inventory_vehicles v ON v.id = q.vehicle_id ORDER BY q.created_at DESC")


DISABLED = "Función deshabilitada temporalmente después del incidente."


@router.post("/quotes")
def create_quote(request: Request):
    require_staff(request)
    raise HTTPException(status_code=503, detail=DISABLED)


@router.post("/quotes/{quote_id}/close")
def close_sale(quote_id: str, request: Request):
    require_staff(request)
    raise HTTPException(status_code=503, detail=DISABLED)


@router.post("/inventory/{vehicle_id}/price")
def change_price(vehicle_id: str, request: Request):
    require_staff(request)
    raise HTTPException(status_code=503, detail=DISABLED)


@router.get("/conversations")
def conversations(request: Request, q: str | None = None):
    require_staff(request)
    where, params = "", ()
    if q:
        where = "WHERE s.id IN (SELECT session_id FROM chat_messages WHERE content ILIKE %s) OR s.src_ip ILIKE %s"
        params = (f"%{q}%", f"%{q}%")
    return query("SELECT s.id, s.started_at, s.src_ip, s.user_agent, s.role, u.full_name AS customer, "
                 "(SELECT count(*) FROM chat_messages m WHERE m.session_id = s.id) AS message_count, "
                 "(f.session_id IS NOT NULL) AS useful FROM chat_sessions s LEFT JOIN users u ON u.id = s.user_id "
                 f"LEFT JOIN conversation_index_flags f ON f.session_id = s.id {where} ORDER BY s.started_at DESC", params)


@router.get("/conversations/{session_id}")
def conversation(session_id: str, request: Request):
    require_staff(request)
    return {
        "messages": query("SELECT ts, role, content FROM chat_messages WHERE session_id = %s ORDER BY ts, id", (session_id,)),
        "actions": query("SELECT ts, action, params, status, result_summary FROM assistant_actions WHERE session_id = %s "
                         "ORDER BY ts, id", (session_id,)),
    }


@router.post("/data-question")
def data_question(body: DataQuestion, request: Request):
    require_staff(request)
    return run_action("run_sql", {"question": body.question}, ActionContext(source="staff", role="staff"))


@router.get("/emails")
def emails(request: Request):
    require_staff(request)
    return query("SELECT id, ts, sender, recipient, subject, body FROM outbox ORDER BY ts DESC")


@router.get("/audit")
def audit(request: Request):
    require_staff(request)
    return query("SELECT id, ts_naive, event, detail, subject_text FROM audit_log ORDER BY id")


@router.post("/audit/clear")
def clear_audit(request: Request):
    require_staff(request)
    query("DELETE FROM audit_log")
    return {"ok": True}
