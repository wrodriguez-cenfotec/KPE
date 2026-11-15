from ..db import query
from ..rag.retrieval import retrieve

FIELDS = "id, brand, model, year, km, fuel, transmission, body, price, status"


def search_inventory(params: dict, ctx) -> dict:
    text = str(params.get("query") or params.get("consulta") or "").strip()
    if not text:
        rows = query(f"SELECT {FIELDS} FROM inventory_vehicles WHERE published ORDER BY created_at DESC LIMIT 5")
    else:
        ids = list(dict.fromkeys(c["source_id"] for c in retrieve(text, k=10, source_types=["inventory"])))
        found = {r["id"]: r for r in query(f"SELECT {FIELDS} FROM inventory_vehicles WHERE published AND id = ANY(%s)", (ids,))}
        rows = [found[i] for i in ids if i in found][:5]
    return {"vehicles": rows}
