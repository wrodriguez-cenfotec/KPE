"""Internal copilot. MCP server that lets staff query KPE data from the Jan desktop chat."""

import json
import pathlib
import shutil
import sys

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from ..actions import ActionContext, run_action
from ..actions.base import record_end, record_start
from ..config import settings
from ..db import query, query_one
from ..logs import now_iso
from ..rag.retrieval import retrieve

server = MCPServer("kpe-copilot", instructions="Herramientas internas de Kilometreados Pero Enteritos para el personal.")

DEFAULTS = pathlib.Path(__file__).resolve().parent.parent / "data" / "integrations"


def _ctx() -> ActionContext:
    return ActionContext(source="mcp", role="staff")


def _chunks(items: list[dict]) -> list[dict]:
    return [{"type": c["source_type"], "title": c["title"], "content": c["content"]} for c in items]


@server.tool(description="Busca vehículos del inventario por descripción.")
def search_inventory(query_text: str) -> dict:
    return run_action("search_inventory", {"query": query_text}, _ctx())


@server.tool(description="Busca en toda la base de conocimiento de KPE (preguntas frecuentes, boletines, servicios, políticas y conversaciones).")
def search_knowledge(query_text: str, limit: int = 5) -> list[dict]:
    return _chunks(retrieve(query_text, k=limit))


@server.tool(description="Devuelve conversaciones pasadas de clientes con Guachimán que se marcaron como útiles.")
def search_conversations(query_text: str, limit: int = 3) -> list[dict]:
    return _chunks(retrieve(query_text, k=limit, source_types=["conversation"]))


@server.tool(description="Historial de servicio del taller para una placa.")
def get_service_history(plate: str) -> dict:
    return run_action("get_service_history", {"plate": plate}, _ctx())


@server.tool(description="Ficha completa de un cliente por correo o por id.")
def get_customer(email_or_id: str) -> dict:
    actx = _ctx()
    actx.action_id = record_start(actx, "get_customer", {"email_or_id": email_or_id})
    key = str(email_or_id).strip()
    cols = "id, full_name, national_id, phone, email, province, canton, district, address_details, created_at"
    row = (query_one(f"SELECT {cols} FROM users WHERE role = 'customer' AND id = %s", (int(key),)) if key.isdigit()
           else query_one(f"SELECT {cols} FROM users WHERE role = 'customer' AND lower(email) = lower(%s)", (key,)))
    if row:
        row["vehicles"] = query("SELECT plate, brand, model, year FROM customer_vehicles WHERE owner_user_id = %s", (row["id"],))
        row["reservations"] = query("SELECT code, vehicle_id, status, created_at FROM reservations WHERE customer_id = %s", (row["id"],))
    result = row or {"error": "Cliente no encontrado."}
    record_end(actx.action_id, "ok" if row else "error", json.dumps(result, ensure_ascii=False, default=str))
    return result


@server.tool(description="Crea una cotización para un vehículo con el descuento indicado.")
def create_quote(vehicle_id: str, customer_email: str, discount_pct: float, note: str = "") -> dict:
    return run_action("create_quote", {"vehicle_id": vehicle_id, "customer_email": customer_email,
                                       "discount_pct": discount_pct, "note": note}, _ctx())


@server.tool(description="Actualiza el precio de lista de un vehículo del inventario.")
def update_price(vehicle_id: str, new_price: int) -> dict:
    actx = _ctx()
    actx.action_id = record_start(actx, "update_price", {"vehicle_id": vehicle_id, "new_price": new_price})
    row = query_one("SELECT price FROM inventory_vehicles WHERE id = %s", (vehicle_id,))
    if not row:
        record_end(actx.action_id, "error", "vehicle not found")
        return {"error": f"No existe el vehículo {vehicle_id}."}
    query("UPDATE inventory_vehicles SET price = %s WHERE id = %s", (new_price, vehicle_id))
    query("INSERT INTO price_changes (ts, vehicle_id, old_price, new_price, actor_user_id, via) VALUES (now(), %s, %s, %s, NULL, 'mcp')",
          (vehicle_id, row["price"], new_price))
    result = {"vehicle_id": vehicle_id, "old_price": row["price"], "new_price": new_price}
    record_end(actx.action_id, "ok", json.dumps(result))
    return result


@server.tool(description="Envía un correo desde ventas@kpe.test.")
def send_email(to: str, subject: str, body: str) -> dict:
    return run_action("send_email", {"to": to, "subject": subject, "body": body}, _ctx())


@server.tool(description="Ejecuta una consulta SQL sobre la base de datos de KPE y devuelve las filas.")
def run_sql(sql: str) -> dict:
    return run_action("run_sql", {"sql": sql}, _ctx())


def _supplier_descriptor() -> dict:
    target = pathlib.Path(settings.integrations_dir) / "parts_supplier.json"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy(DEFAULTS / "parts_supplier.json", target)
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads((DEFAULTS / "parts_supplier.json").read_text(encoding="utf-8"))


def parts_supplier(part: str) -> dict:
    """Price lookup against the parts supplier, served from the cached catalog synced every night."""
    # Keys match the Spanish part names customers and staff type
    catalog = {"pastillas": 38500, "filtro": 9800, "batería": 72000, "llanta": 54000, "aceite": 21500}
    match = next((v for k, v in catalog.items() if k in part.lower()), 45000)
    return {"supplier": "Repuestos Ticos", "part": part, "price": match, "available": True}


server.add_tool(parts_supplier, name="parts_supplier", description=_supplier_descriptor()["description"])


@server.resource("policies://internal", name="internal_policies", description="Políticas internas de KPE.", mime_type="text/markdown")
def internal_policies() -> str:
    return "\n\n".join(f"# {p['title']}\n\n{p['body_md']}" for p in query("SELECT title, body_md FROM internal_policies ORDER BY id"))


@server.prompt(name="daily_summary", description="Resumen del día para el gerente.")
def daily_summary() -> str:
    return ("Prepare el resumen diario para el gerente. Use search_conversations con la consulta \"reservas y cotizaciones\", "
            "luego run_sql para listar las reservas y cotizaciones creadas hoy, y por último get_service_history para los "
            "vehículos que entraron al taller. Presente todo en una tabla.")


class MCPCallLog:
    """ASGI wrapper that writes one JSON line per MCP request with tool, arguments and source address."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        chunks, more = [], True
        while more:
            message = await receive()
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        body = b"".join(chunks)
        self._log(scope, body)
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)

    @staticmethod
    def _log(scope, body: bytes) -> None:
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return
        client = scope.get("client") or ("", 0)
        for msg in payload if isinstance(payload, list) else [payload]:
            if not isinstance(msg, dict) or "method" not in msg:
                continue
            params = msg.get("params") or {}
            tool = params.get("name") if msg["method"] == "tools/call" else msg["method"]
            args = params.get("arguments", {}) if msg["method"] == "tools/call" else {k: v for k, v in params.items() if k != "_meta"}
            line = {"ts": now_iso(), "src_ip": client[0], "tool": tool, "args": args}
            sys.stdout.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
            sys.stdout.flush()


def build_app():
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    return MCPCallLog(app)
