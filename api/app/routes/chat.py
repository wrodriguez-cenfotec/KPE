import dataclasses
import json
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..actions import ActionContext, run_action
from ..auth import current_session
from ..config import settings
from ..db import query, query_one
from ..llm.parser import parse_reply
from ..llm.prompts import action_result_message, build_messages
from ..llm.provider import LLMError, get_provider
from ..logs import log_event, request_ctx
from ..rag.indexing import index_conversation
from ..rag.retrieval import format_context, retrieve

router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_STEPS = 12
TABLE_PREVIEW_ROWS = 10


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _ensure_session(request: Request, session_id: str | None, sess: dict) -> str:
    if session_id and query_one("SELECT 1 AS ok FROM chat_sessions WHERE id = %s", (session_id,)):
        return session_id
    new_id = "ch_" + secrets.token_hex(6)
    query("INSERT INTO chat_sessions (id, started_at, src_ip, user_agent, user_id, role) VALUES (%s, now(), %s, %s, %s, %s)",
          (new_id, _client_ip(request), request.headers.get("user-agent", ""), sess["user_id"], sess["role"]))
    return new_id


def _history(session_id: str) -> list[dict]:
    """Chat messages of the session, each assistant answer with the actions that ran in its turn."""
    messages = query("SELECT role, content, ts FROM chat_messages WHERE session_id = %s ORDER BY ts, id", (session_id,))
    actions = query("SELECT action, params, ts FROM assistant_actions WHERE session_id = %s AND status = 'ok' ORDER BY ts, id",
                    (session_id,))
    turn_start = None
    for m in messages:
        if m["role"] == "user":
            turn_start = m["ts"]
        elif turn_start is not None:
            m["actions"] = [a for a in actions if turn_start <= a["ts"] <= m["ts"]]
    return messages


def _store(session_id: str, role: str, content: str) -> None:
    query("INSERT INTO chat_messages (session_id, ts, role, content) VALUES (%s, clock_timestamp(), %s, %s)",
          (session_id, role, content))


def _result_for_model(result: dict) -> str:
    if "rows" in result:
        preview = dict(result, rows=result["rows"][:TABLE_PREVIEW_ROWS])
        return json.dumps(preview, ensure_ascii=False, default=str)
    return json.dumps(result, ensure_ascii=False, default=str)


def _timeout_response(exc: LLMError) -> JSONResponse:
    return JSONResponse(status_code=504, content={
        "detail": "El asistente tardó demasiado en responder.",
        "error": str(exc),
        "config": dataclasses.asdict(settings),
    })


@router.post("")
def chat(body: ChatIn, request: Request):
    sess = current_session(request)
    session_id = _ensure_session(request, body.session_id, sess)
    ctx_vars = dict(request_ctx.get(), session_id=session_id)
    request_ctx.set(ctx_vars)
    history = _history(session_id)
    _store(session_id, "user", body.message)
    provider = get_provider()
    try:
        context = format_context(retrieve(body.message))
    except LLMError:
        context = ""
    plates = None
    if sess["role"] == "customer":
        plates = [r["plate"] for r in query("SELECT plate FROM customer_vehicles WHERE owner_user_id = %s ORDER BY plate", (sess["user_id"],))]
    messages = build_messages(sess["role"], sess["user_id"], context, history, body.message, plates)
    actx = ActionContext(source="web_chat", role=sess["role"], user_id=sess["user_id"], session_id=session_id,
                         extra={"user_message": body.message})
    actions, table, answer = [], None, None
    try:
        for _ in range(MAX_STEPS):
            reply = provider.chat(messages)
            obj = parse_reply(reply["content"])
            if not obj or "action" not in obj:
                answer = str(obj.get("answer", "")) if obj else reply["content"].strip()
                break
            name, params = str(obj.get("action")), obj.get("params") or {}
            result = run_action(name, params, actx)
            actions.append({"action": name, "params": params, "ok": "error" not in result})
            if "rows" in result:
                table = {"columns": result["columns"], "rows": result["rows"]}
            messages += [{"role": "assistant", "content": json.dumps(obj, ensure_ascii=False)},
                         action_result_message(name, _result_for_model(result))]
    except LLMError as exc:
        log_event("llm_error", level="ERROR", detail=str(exc))
        if "timeout" in str(exc):
            return _timeout_response(exc)
        raise HTTPException(status_code=503, detail="Guachimán no está disponible en este momento. Intente de nuevo en unos minutos.")
    if not answer:
        answer = "Listo, ya quedó hecho." if actions else "Disculpe, no entendí. ¿Me lo puede explicar de otra forma?"
    _store(session_id, "assistant", answer)
    log_event("chat_turn", detail=f"{len(actions)} actions")
    return {"session_id": session_id, "answer": answer, "actions": actions, "table": table}


@router.get("/{session_id}")
def history(session_id: str):
    rows = query("SELECT role, content, ts FROM chat_messages WHERE session_id = %s ORDER BY ts, id", (session_id,))
    return {"session_id": session_id, "messages": rows}


@router.post("/{session_id}/useful")
def mark_useful(session_id: str, request: Request):
    if not query_one("SELECT 1 AS ok FROM chat_sessions WHERE id = %s", (session_id,)):
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    query("INSERT INTO conversation_index_flags (session_id, flagged_at, flagged_by_ip) VALUES (%s, now(), %s) "
          "ON CONFLICT (session_id) DO UPDATE SET flagged_at = now()", (session_id, _client_ip(request)))
    try:
        chunks = index_conversation(session_id)
    except LLMError:
        chunks = 0
    return {"ok": True, "message": "¡Gracias! Su opinión nos ayuda a mejorar.", "chunks": chunks}
