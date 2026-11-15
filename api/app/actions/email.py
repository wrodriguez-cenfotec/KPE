from ..db import query_one

SENDER = "ventas@kpe.test"


# The model sometimes names parameters in Spanish
def send_email(params: dict, ctx) -> dict:
    to = str(params.get("to") or params.get("para") or "").strip()
    subject = str(params.get("subject") or params.get("asunto") or "Kilometreados Pero Enteritos").strip()
    body = str(params.get("body") or params.get("cuerpo") or "").strip()
    row = query_one("INSERT INTO outbox (ts, sender, recipient, subject, body, source_action_id) "
                    "VALUES (now(), %s, %s, %s, %s, %s) RETURNING id", (SENDER, to, subject, body, ctx.action_id))
    return {"status": "sent", "to": to, "subject": subject, "id": row["id"]}
