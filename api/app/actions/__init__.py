"""Assistant actions, shared by the web chat and the MCP server."""

import json

from ..logs import log_event
from .account import get_my_reservations, get_my_vehicles
from .base import ActionContext, ActionError, record_end, record_start
from .data_query import run_sql
from .email import send_email
from .inventory import search_inventory
from .quotes import create_quote
from .reservations import book_reservation
from .service import get_service_history

ACTIONS = {
    "search_inventory": search_inventory,
    "create_quote": create_quote,
    "get_service_history": get_service_history,
    "book_reservation": book_reservation,
    "send_email": send_email,
    "run_sql": run_sql,
    "get_my_reservations": get_my_reservations,
    "get_my_vehicles": get_my_vehicles,
}


def run_action(name: str, params: dict, ctx: ActionContext) -> dict:
    fn = ACTIONS.get(name)
    if fn is None:
        return {"error": f"La acción {name} no existe."}
    params = params if isinstance(params, dict) else {}
    ctx.action_id = record_start(ctx, name, params)
    try:
        result = fn(params, ctx)
        record_end(ctx.action_id, "ok", json.dumps(result, ensure_ascii=False, default=str))
        log_event("assistant_action", detail=name, action_id=ctx.action_id, source=ctx.source)
        return result
    except ActionError as exc:
        record_end(ctx.action_id, "error", str(exc))
        return {"error": str(exc)}
    except Exception as exc:
        record_end(ctx.action_id, "error", f"{type(exc).__name__}: {exc}")
        log_event("assistant_action_error", level="ERROR", detail=f"{name}: {exc}")
        return {"error": f"{type(exc).__name__}: {exc}"}


__all__ = ["ACTIONS", "ActionContext", "ActionError", "run_action"]
