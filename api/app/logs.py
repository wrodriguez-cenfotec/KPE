"""Application event log, one JSON object per line on stdout."""

import contextvars
import datetime as dt
import json
import sys
import uuid

request_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar("request_ctx", default={})


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def log_event(event: str, level: str = "INFO", detail: str | dict | None = None, **fields) -> None:
    ctx = request_ctx.get()
    record = {
        "ts": now_iso(),
        "level": level,
        "request_id": ctx.get("request_id"),
        "session_id": ctx.get("session_id"),
        "src_ip": ctx.get("src_ip"),
        "user_id": ctx.get("user_id"),
        "role": ctx.get("role"),
        "route": ctx.get("route"),
        "event": event,
        "detail": detail,
    }
    record.update(fields)
    sys.stdout.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()
