from ..db import query
from .embeddings import embed_query, to_pgvector

TOP_K = 5
CANDIDATES = 20
# Conversations were marked useful by real customers, so they get a small boost
USEFUL_CHAT_BOOST = 0.1


def retrieve(question: str, k: int = TOP_K, source_types: list[str] | None = None) -> list[dict]:
    vec = to_pgvector(embed_query(question))
    where, params = "", [vec]
    if source_types:
        where = "WHERE source_type = ANY(%s)"
        params.append(source_types)
    params += [vec, CANDIDATES]
    rows = query(
        "SELECT id, source_type, source_id, owner_user_id, plate, title, content, metadata, created_at, "
        f"1 - (embedding <=> %s::vector) AS similarity FROM rag_chunks {where} "
        "ORDER BY embedding <=> %s::vector LIMIT %s", tuple(params))
    for r in rows:
        r["score"] = r["similarity"] + (USEFUL_CHAT_BOOST if r["source_type"] == "conversation" else 0.0)
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:k]


def format_context(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{c['source_type']}] {c['title']}\n{c['content']}" for c in chunks)


def similar_vehicles(vehicle_id: str, k: int = 3) -> list[str]:
    rows = query(
        "SELECT c2.source_id FROM rag_chunks c1 JOIN rag_chunks c2 ON c2.source_type = 'inventory' AND c2.source_id <> c1.source_id "
        "JOIN inventory_vehicles v ON v.id = c2.source_id AND v.published "
        "WHERE c1.source_type = 'inventory' AND c1.source_id = %s "
        "ORDER BY c1.embedding <=> c2.embedding LIMIT %s", (vehicle_id, k * 3))
    seen: list[str] = []
    for r in rows:
        if r["source_id"] not in seen:
            seen.append(r["source_id"])
    return seen[:k]
