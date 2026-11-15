from fastapi import APIRouter, Query

from ..db import query
from ..llm.provider import LLMError
from ..rag.retrieval import retrieve, similar_vehicles
from .public import PUBLIC_COLUMNS

router = APIRouter(prefix="/api", tags=["search"])

SEARCH_UNAVAILABLE = {"items": [], "message": "La búsqueda inteligente no está disponible en este momento."}


@router.get("/search")
def search(q: str, k: int = Query(5, ge=1, le=20)):
    try:
        chunks = retrieve(q, k=k)
    except LLMError:
        return SEARCH_UNAVAILABLE
    return {"items": [{key: c[key] for key in ("source_type", "source_id", "owner_user_id", "plate", "title", "content",
                                                "metadata", "created_at", "score")} for c in chunks]}


@router.get("/inventory/search")
def semantic_inventory(q: str, k: int = Query(12, ge=1, le=50)):
    try:
        chunks = retrieve(q, k=k * 2, source_types=["inventory"])
    except LLMError:
        return SEARCH_UNAVAILABLE
    ids = list(dict.fromkeys(c["source_id"] for c in chunks))
    if not ids:
        return {"items": []}
    rows = {r["id"]: r for r in query(f"SELECT {PUBLIC_COLUMNS} FROM inventory_vehicles WHERE published AND id = ANY(%s)", (ids,))}
    return {"items": [rows[i] for i in ids if i in rows][:k]}


@router.get("/inventory/{vehicle_id}/similar")
def similar(vehicle_id: str):
    ids = similar_vehicles(vehicle_id)
    rows = {r["id"]: r for r in query(f"SELECT {PUBLIC_COLUMNS} FROM inventory_vehicles WHERE id = ANY(%s)", (ids,))}
    return {"items": [rows[i] for i in ids if i in rows]}
