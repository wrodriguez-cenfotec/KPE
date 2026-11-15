"""Natural language questions over the KPE database.

Started as a helper for the Gestión "Pregúntele a sus datos" box while the
assistant was being prototyped.
"""

import datetime as dt
import decimal
import re

import psycopg

from ..db import pool
from ..llm.provider import get_provider
from ..llm.parser import parse_reply

SCHEMA_HINT = """Tablas principales de PostgreSQL
users(id, role ('customer' o 'staff'), staff_title, full_name, national_id, phone, email, province, canton, district, address_details)
inventory_vehicles(id, plate, brand, model, year, km, fuel, transmission, price, cost, status ('available', 'reserved', 'sold'), published)
customer_vehicles(plate, owner_user_id, brand, model, year)
service_records(id, plate, service_date, km, mechanic_user_id, notes)
quotes(id, created_at, vehicle_id, customer_email, discount_pct, final_price, created_via, status ('open', 'expired', 'sold'), note, seller_name)
reservations(id, code, created_at, vehicle_id, customer_id, deposit_amount, status ('pending', 'confirmed', 'cancelled'), sinpe_ref)
price_changes(id, ts, vehicle_id, old_price, new_price, via)
outbox(id, ts, sender, recipient, subject, body)
integrations(id, provider, endpoint, api_key)
Relaciones. customer_vehicles.owner_user_id = users.id, service_records.plate = customer_vehicles.plate, quotes.vehicle_id = inventory_vehicles.id, reservations.customer_id = users.id.
Los clientes son las filas de users con role = 'customer'. Use JOIN solo cuando la pregunta necesite datos de otra tabla."""


def _plain(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


def write_sql(question: str) -> str:
    reply = get_provider().chat([
        {"role": "system", "content": "Escriba una sola consulta SQL de PostgreSQL que responda la pregunta. "
                                      'Responda solo con JSON {"sql": "..."}.\n' + SCHEMA_HINT},
        {"role": "user", "content": question}])
    # Small models sometimes wrap the answer in a Markdown code block
    content = re.sub(r"^```[a-z]*\s*|\s*```$", "", reply["content"].strip())
    obj = parse_reply(content) or {}
    return str(obj.get("sql") or content).strip().rstrip(";")


def _execute(sql: str) -> dict:
    with pool.connection() as conn:
        cur = conn.execute(sql)
        if cur.description is None:
            return {"sql": sql, "columns": [], "rows": [], "total": cur.rowcount}
        columns = [c.name for c in cur.description]
        rows = [[_plain(r[c]) for c in columns] for r in cur.fetchall()]
    return {"sql": sql, "columns": columns, "rows": rows, "total": len(rows)}


def run_sql(params: dict, ctx) -> dict:
    # The model sometimes names parameters in Spanish
    question = str(params.get("question") or params.get("pregunta") or "").strip()
    given = str(params.get("sql") or "").strip().rstrip(";")
    if given:
        return _execute(given)
    # The chat model sometimes passes its own SQL draft with made up table names as the question.
    # In that case the writer works from the customer's request instead.
    if re.match(r"(?is)^\s*(select|with)\b", question) and ctx is not None and ctx.extra.get("user_message"):
        question = ctx.extra["user_message"]
    sql = write_sql(question)
    try:
        return _execute(sql)
    except psycopg.Error as exc:
        # One retry: give the generated query and the database error back to the writer
        fixed = write_sql(f"{question}\n\nLa consulta {sql} falló con este error. {exc}\nCorríjala usando solo las tablas indicadas.")
        return _execute(fixed)
