from fastapi import APIRouter, HTTPException, Query

from ..db import query, query_one

router = APIRouter(prefix="/api", tags=["public"])

PUBLIC_COLUMNS = ("id, brand, model, year, km, fuel, transmission, body, color, price, status, description, "
                  "inspection_summary, inspection_status")


@router.get("/inventory")
def inventory(q: str | None = None, brand: str | None = None, year_min: int | None = None, year_max: int | None = None,
              price_min: int | None = None, price_max: int | None = None, fuel: str | None = None,
              transmission: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50)):
    where, params = ["published"], []
    if q:
        where.append("(brand || ' ' || model || ' ' || description) ILIKE %s")
        params.append(f"%{q}%")
    for col, val in (("brand", brand), ("fuel", fuel), ("transmission", transmission)):
        if val:
            where.append(f"{col} = %s")
            params.append(val)
    for col, op, val in (("year", ">=", year_min), ("year", "<=", year_max), ("price", ">=", price_min), ("price", "<=", price_max)):
        if val is not None:
            where.append(f"{col} {op} %s")
            params.append(val)
    clause = " AND ".join(where)
    total = query_one(f"SELECT count(*) AS n FROM inventory_vehicles WHERE {clause}", tuple(params))["n"]
    rows = query(f"SELECT {PUBLIC_COLUMNS} FROM inventory_vehicles WHERE {clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                 tuple(params) + (page_size, (page - 1) * page_size))
    return {"total": total, "page": page, "page_size": page_size, "items": rows}


@router.get("/inventory/filters")
def inventory_filters():
    def distinct(col):
        return [r["v"] for r in query(f"SELECT DISTINCT {col} AS v FROM inventory_vehicles WHERE published ORDER BY 1")]
    rng = query_one("SELECT min(year) AS year_min, max(year) AS year_max, min(price) AS price_min, max(price) AS price_max "
                    "FROM inventory_vehicles WHERE published")
    return {"brands": distinct("brand"), "fuels": distinct("fuel"), "transmissions": distinct("transmission"), **rng}


@router.get("/inventory/{vehicle_id}")
def vehicle(vehicle_id: str):
    row = query_one(f"SELECT {PUBLIC_COLUMNS} FROM inventory_vehicles WHERE id = %s AND published", (vehicle_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
    return row


@router.get("/faq")
def faq():
    return query("SELECT page, position, title, body_md FROM faq_documents ORDER BY page, position")
