"""Builds the knowledge base the assistant searches.

Every source goes into rag_chunks. Progress is tracked per source row in
index_jobs, so an interrupted run resumes where it stopped.
"""

import json
import time

from ..db import pool, query
from ..llm.provider import LLMError
from ..logs import log_event
from .chunking import chunk_text
from .embeddings import embed_documents, to_pgvector

LAUNCH_DATE = "2026-09-14T09:00:00-06:00"


def _money(n: int) -> str:
    return f"₡{n:,}"


def inventory_sources():
    for v in query("SELECT * FROM inventory_vehicles ORDER BY id"):
        text = f"{v['description']} Precio {_money(v['price'])}. {v['inspection_summary']}"
        yield dict(source_type="inventory", source_id=v["id"], owner_user_id=None, plate=v["plate"],
                   title=f"{v['brand']} {v['model']} {v['year']}", text=text, created_at=v["created_at"],
                   metadata={"vehicle_id": v["id"], "published": v["published"]})


def bulletin_sources():
    for b in query("SELECT * FROM bulletins ORDER BY id"):
        yield dict(source_type="bulletin", source_id=b["code"], owner_user_id=None, plate=None, title=b["title"],
                   text=f"{b['title']}\n{b['body_md']}", created_at=b["published_at"], metadata={"code": b["code"]})


def faq_sources():
    pages: dict[str, list[str]] = {}
    for f in query("SELECT * FROM faq_documents ORDER BY page, position"):
        pages.setdefault(f["page"], []).append(f"{f['title']}\n{f['body_md']}")
    for page, sections in pages.items():
        yield dict(source_type="faq", source_id=page, owner_user_id=None, plate=None, title=page,
                   text="\n".join(sections), created_at=LAUNCH_DATE, metadata={"page": page})


def policy_sources():
    for p in query("SELECT * FROM internal_policies ORDER BY id"):
        yield dict(source_type="internal_policy", source_id=p["slug"], owner_user_id=None, plate=None, title=p["title"],
                   text=f"{p['title']}\n{p['body_md']}", created_at=LAUNCH_DATE, metadata={"slug": p["slug"]})


def service_record_sources():
    rows = query("SELECT s.*, c.owner_user_id FROM service_records s LEFT JOIN customer_vehicles c ON c.plate = s.plate ORDER BY s.id")
    for s in rows:
        text = f"Historial de servicio placa {s['plate']}. {s['service_date']}, {s['km']:,} km. {s['notes']}"
        yield dict(source_type="service_record", source_id=str(s["id"]), owner_user_id=s["owner_user_id"], plate=s["plate"],
                   title=f"Servicio {s['plate']} {s['service_date']}", text=text, created_at=str(s["service_date"]),
                   metadata={"record_id": s["id"]})


def transcript(session_id: str) -> str:
    lines = []
    for m in query("SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY ts, id", (session_id,)):
        who = "Cliente" if m["role"] == "user" else "Guachimán"
        lines.append(f"{who}: {m['content']}")
    return "\n".join(lines)


def conversation_sources():
    for f in query("SELECT session_id, flagged_at FROM conversation_index_flags ORDER BY flagged_at"):
        yield dict(source_type="conversation", source_id=f["session_id"], owner_user_id=None, plate=None,
                   title="Conversación útil", text=transcript(f["session_id"]), created_at=f["flagged_at"],
                   metadata={"session_id": f["session_id"]})


SOURCES = [faq_sources, bulletin_sources, inventory_sources, policy_sources, service_record_sources, conversation_sources]


def index_source(src: dict) -> int:
    pieces = chunk_text(src["text"])
    if not pieces:
        return 0
    vectors = embed_documents(pieces)
    with pool.connection() as conn:
        with conn.transaction():
            conn.execute("DELETE FROM rag_chunks WHERE source_type = %s AND source_id = %s", (src["source_type"], src["source_id"]))
            for piece, vec in zip(pieces, vectors):
                conn.execute(
                    "INSERT INTO rag_chunks (source_type, source_id, owner_user_id, plate, title, content, metadata, created_at, embedding) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)",
                    (src["source_type"], src["source_id"], src["owner_user_id"], src["plate"], src["title"], piece,
                     json.dumps(src["metadata"], default=str), src["created_at"], to_pgvector(vec)))
            conn.execute(
                "INSERT INTO index_jobs (source_type, source_id, status, chunks, updated_at) VALUES (%s, %s, 'done', %s, now()) "
                "ON CONFLICT (source_type, source_id) DO UPDATE SET status = 'done', chunks = EXCLUDED.chunks, updated_at = now()",
                (src["source_type"], src["source_id"], len(pieces)))
    return len(pieces)


def index_conversation(session_id: str) -> int:
    """Called when a visitor marks a conversation as useful."""
    flag = query("SELECT flagged_at FROM conversation_index_flags WHERE session_id = %s", (session_id,))
    if not flag:
        return 0
    n = index_source(dict(source_type="conversation", source_id=session_id, owner_user_id=None, plate=None,
                          title="Conversación útil", text=transcript(session_id), created_at=flag[0]["flagged_at"],
                          metadata={"session_id": session_id}))
    log_event("conversation_indexed", detail=session_id, chunks=n)
    return n


def _wait_for_embeddings(state: dict) -> None:
    delay = 2
    while True:
        try:
            embed_documents(["ping"])
            return
        except LLMError as exc:
            state.update(stage="index_waiting_llm", detail=str(exc))
            time.sleep(delay)
            delay = min(delay * 2, 30)


def run_bootstrap_index(state: dict) -> bool:
    _wait_for_embeddings(state)
    state.update(stage="index", detail=None)
    done = {(r["source_type"], r["source_id"]) for r in query("SELECT source_type, source_id FROM index_jobs WHERE status = 'done'")}
    pending = [s for gen in SOURCES for s in gen() if (s["source_type"], s["source_id"]) not in done]
    state["chunks_total"] = len(pending) + len(done)
    state["chunks_done"] = len(done)
    for src in pending:
        while True:
            try:
                index_source(src)
                break
            except LLMError as exc:
                state.update(detail=str(exc))
                _wait_for_embeddings(state)
                state.update(stage="index", detail=None)
        state["chunks_done"] += 1
    return True


def reindex_all(state: dict) -> None:
    query("TRUNCATE rag_chunks, index_jobs")
    run_bootstrap_index(state)
    state["stage"] = "ready"
