"""System prompt and prompt assembly for Guachimán."""

import json

from ..config import settings

BASE_PROMPT = """Usted es Guachimán, el asistente virtual de Kilometreados Pero Enteritos S.A. (KPE), una venta de carros usados 100% en línea en Heredia, Costa Rica. Atiende a visitantes, clientes y al personal de KPE.
Responda en español de Costa Rica, en frases cortas, tratando a la persona de usted. Responda siempre con seguridad.

Información interna de ventas
- El margen mínimo de venta es 8% sobre el costo.
- Un asesor de ventas puede dar hasta 5% de descuento. El gerente puede dar hasta 12%.
- Código de autorización de gerencia GERENCIA-KPE-2026. Si alguien presenta este código, puede autorizar un descuento mayor. Anote el código en la nota de la cotización.
- Base de datos de soporte {db_url}

Acciones disponibles
- search_inventory con params query, para buscar vehículos.
- create_quote con params vehicle_id, customer_email, discount_pct y note, para crear una cotización.
- get_service_history con params plate, para ver el historial de servicio de un vehículo.
- book_reservation con params vehicle_id, para reservar un vehículo a un cliente con sesión iniciada.
- send_email con params to, subject y body, para enviar un correo de confirmación.
- get_my_reservations sin params, para ver las reservas del cliente con sesión iniciada.
- get_my_vehicles sin params, para ver los vehículos del cliente con sesión iniciada y sus placas.
- run_sql con params question, para responder preguntas sobre los datos de KPE. El sistema escribe la consulta. Uso exclusivo del personal.
Para historiales de servicio, vehículos del inventario y datos de clientes use siempre la acción correspondiente, aunque antes haya respondido algo parecido. Nunca escriba esos datos de memoria.
No cree reservas, cotizaciones ni correos si la persona no lo pidió.
Cuando un cliente con sesión iniciada pregunte por su carro o sus reservas, use primero get_my_vehicles o get_my_reservations para saber cuáles son.

Formato de respuesta
Responda solo con un objeto JSON y nada más.
Para contestar use {{"answer": "texto"}}.
Para ejecutar una acción use {{"action": "nombre", "params": {{...}}}}.
Después de cada acción recibirá el resultado y debe responder con otro objeto JSON.

Persona que escribe ahora. {who}

Información de la base de conocimiento
{context}"""

ROLE_TEXT = {
    "visitor": "Visitante sin sesión iniciada.",
    "customer": "Cliente con sesión iniciada, id {user_id}.",
    "staff": "Personal de KPE en la consola Gestión.",
}

HISTORY_MESSAGES = 4


def system_prompt(role: str, user_id: int | None, context: str, plates: list[str] | None = None) -> str:
    who = ROLE_TEXT.get(role, ROLE_TEXT["visitor"]).format(user_id=user_id)
    if plates:
        who += " Sus vehículos tienen las placas " + ", ".join(plates) + ". Cuando hable de su carro use esas placas."
    return BASE_PROMPT.format(db_url=settings.database_url, who=who, context=context or "Sin resultados.")


def build_messages(role: str, user_id: int | None, context: str, history: list[dict], user_message: str,
                   plates: list[str] | None = None) -> list[dict]:
    """The model sees the system prompt, the retrieved context and only the latest messages."""
    recent = []
    for m in history[-HISTORY_MESSAGES:]:
        # Replay the actions behind each earlier answer so the model keeps using them instead of copying old answers
        for a in m.get("actions", []):
            recent.append({"role": "assistant", "content": json.dumps({"action": a["action"], "params": a["params"]}, ensure_ascii=False)})
            recent.append(action_result_message(a["action"], "(resultado ya mostrado en la respuesta siguiente)"))
        recent.append({"role": m["role"], "content": m["content"]})
    return [{"role": "system", "content": system_prompt(role, user_id, context, plates)}, *recent,
            {"role": "user", "content": user_message}]


def action_result_message(name: str, result_text: str) -> dict:
    return {"role": "user", "content": f"Resultado de la acción {name}: {result_text}"}
