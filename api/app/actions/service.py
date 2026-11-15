from ..db import query


def get_service_history(params: dict, ctx) -> dict:
    plate = str(params.get("plate") or params.get("placa") or "").strip().upper()
    records = query("SELECT service_date, km, notes FROM service_records WHERE upper(plate) = %s ORDER BY service_date", (plate,))
    return {"plate": plate, "services": [{"date": str(r["service_date"]), "km": r["km"], "notes": r["notes"]} for r in records]}
