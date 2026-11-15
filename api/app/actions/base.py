import json
from dataclasses import dataclass, field

from ..db import query, query_one


@dataclass
class ActionContext:
    source: str                     # web_chat | mcp
    role: str = "visitor"
    user_id: int | None = None
    session_id: str | None = None
    action_id: int | None = None
    extra: dict = field(default_factory=dict)


class ActionError(Exception):
    pass


def record_start(ctx: ActionContext, name: str, params: dict) -> int:
    row = query_one(
        "INSERT INTO assistant_actions (ts, source, session_id, actor_user_id, action, params, status) "
        "VALUES (now(), %s, %s, %s, %s, %s, 'running') RETURNING id",
        (ctx.source, ctx.session_id, ctx.user_id, name, json.dumps(params, ensure_ascii=False, default=str)))
    return row["id"]


def record_end(action_id: int, status: str, summary: str) -> None:
    query("UPDATE assistant_actions SET status = %s, result_summary = %s WHERE id = %s", (status, summary[:500], action_id))
