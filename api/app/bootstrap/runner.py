"""First run pipeline. Each stage runs once and is recorded in app_bootstrap.

1 schema  create the extension and the tables
2 load    load every CSV in api/app/data/csv
3 index   chunk and embed the knowledge sources (needs Jan)
4 ready   mark the snapshot as complete
"""

import json
import pathlib
import threading
import time

from ..config import settings
from ..db import pool, query, query_one
from ..logs import log_event

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

LOAD_ORDER = [
    "users", "customer_vehicles", "inventory_vehicles", "service_records", "bulletins", "faq_documents",
    "internal_policies", "integrations", "quotes", "price_changes", "reservations", "chat_sessions",
    "chat_messages", "conversation_index_flags", "assistant_actions", "outbox", "audit_log",
]

state = {"stage": "starting", "detail": None, "chunks_done": 0, "chunks_total": 0}


def _stage_done(stage: str) -> bool:
    exists = query_one("SELECT to_regclass('public.app_bootstrap') AS t")
    if not exists or not exists["t"]:
        return False
    return query_one("SELECT 1 AS ok FROM app_bootstrap WHERE stage = %s", (stage,)) is not None


def _mark(stage: str, info: dict | None = None) -> None:
    query("INSERT INTO app_bootstrap (stage, info) VALUES (%s, %s) ON CONFLICT (stage) DO NOTHING",
          (stage, json.dumps(info or {})))


def stage_schema() -> None:
    sql = (DATA / "schema.sql").read_text().replace(":EMBED_DIM", str(settings.embed_dim))
    with pool.connection() as conn:
        conn.execute(sql)
    _mark("schema", {"embed_dim": settings.embed_dim})


def stage_load() -> None:
    with pool.connection() as conn:
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                for table in LOAD_ORDER:
                    path = DATA / "csv" / f"{table}.csv"
                    header = path.open(encoding="utf-8").readline().strip()
                    with cur.copy(f"COPY {table} ({header}) FROM STDIN WITH (FORMAT csv, HEADER true)") as copy:
                        copy.write(path.read_bytes())
                    cur.execute(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = %s AND column_name = 'id' AND is_identity = 'YES'", (table,))
                    if cur.fetchone():
                        cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                                    f"GREATEST((SELECT COALESCE(MAX(id), 0) FROM {table}), 1))")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit = True
    counts = {t: query_one(f"SELECT count(*) AS n FROM {t}")["n"] for t in LOAD_ORDER}
    _mark("load", counts)


def stage_index() -> bool:
    try:
        from ..rag.indexing import run_bootstrap_index
    except ImportError:
        return False
    return run_bootstrap_index(state)


def stage_ready() -> None:
    _mark("ready", {"embed_model": settings.llm_embed_model, "embed_dim": settings.embed_dim})


def run() -> None:
    while True:
        try:
            query("SELECT 1")
            break
        except Exception as exc:
            state.update(stage="waiting_db", detail=str(exc))
            time.sleep(2)
    try:
        if not _stage_done("schema"):
            state["stage"] = "schema"
            stage_schema()
            log_event("bootstrap_stage", detail="schema")
        if not _stage_done("load"):
            state["stage"] = "load"
            stage_load()
            log_event("bootstrap_stage", detail="load")
        if not _stage_done("index"):
            state["stage"] = "index"
            if not stage_index():
                return
            _mark("index", {"chunks": state["chunks_done"]})
            log_event("bootstrap_stage", detail="index")
        if not _stage_done("ready"):
            stage_ready()
            log_event("bootstrap_stage", detail="ready")
        state["stage"] = "ready"
    except Exception as exc:
        state.update(stage="error", detail=str(exc))
        log_event("bootstrap_error", level="ERROR", detail=str(exc))


def start_background() -> None:
    threading.Thread(target=run, name="bootstrap", daemon=True).start()


def status() -> dict:
    recorded = {}
    if _stage_done("schema"):
        recorded = {r["stage"]: r["done_at"] for r in query("SELECT stage, done_at FROM app_bootstrap")}
    out = {"stage": state["stage"], "detail": state["detail"], "sources_done": state["chunks_done"],
           "sources_total": state["chunks_total"], "stages": recorded}
    if "ready" in recorded:
        info = query_one("SELECT info FROM app_bootstrap WHERE stage = 'ready'")["info"]
        if info.get("embed_model") != settings.llm_embed_model or info.get("embed_dim") != settings.embed_dim:
            out["reindex_required"] = True
            out["message"] = "El modelo de embeddings cambió. Ejecute POST /api/admin/reindex."
    return out
