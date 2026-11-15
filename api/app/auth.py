import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request

from .db import query, query_one

COOKIE_NAME = "kpe_session"
STAFF_PASSWORD = "KPE-Gestion-2026"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        algo, iterations, salt, digest = (stored or "").split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def create_session(role: str, user_id: int | None) -> str:
    token = secrets.token_hex(24)
    query("INSERT INTO web_sessions (token, user_id, role) VALUES (%s, %s, %s)", (token, user_id, role))
    return token


def session_from_token(token: str | None) -> dict:
    if not token:
        return {"role": "visitor", "user_id": None}
    try:
        row = query_one("SELECT role, user_id FROM web_sessions WHERE token = %s", (token,))
    except Exception:
        row = None
    return row or {"role": "visitor", "user_id": None}


def current_session(request: Request) -> dict:
    return getattr(request.state, "session", None) or session_from_token(request.cookies.get(COOKIE_NAME))


def require_staff(request: Request) -> dict:
    sess = current_session(request)
    if sess["role"] != "staff":
        raise HTTPException(status_code=401, detail="Debe ingresar a Gestión.")
    return sess


def require_customer(request: Request) -> dict:
    sess = current_session(request)
    if sess["role"] != "customer":
        raise HTTPException(status_code=401, detail="Debe iniciar sesión.")
    return sess
