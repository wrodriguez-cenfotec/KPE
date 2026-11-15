from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..auth import COOKIE_NAME, STAFF_PASSWORD, create_session, current_session, verify_password
from ..db import query, query_one
from ..logs import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])


class CustomerLogin(BaseModel):
    email: str
    password: str


class StaffLogin(BaseModel):
    password: str


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, httponly=False, samesite="lax", path="/")


@router.post("/login")
def login(body: CustomerLogin, response: Response):
    user = query_one("SELECT id, full_name, password_hash FROM users WHERE role = 'customer' AND lower(email) = lower(%s)",
                     (body.email.strip(),))
    if not user or not verify_password(body.password, user["password_hash"]):
        log_event("login_failed", detail=body.email)
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
    _set_cookie(response, create_session("customer", user["id"]))
    log_event("login", detail="customer", user_id=user["id"], role="customer")
    return {"role": "customer", "user_id": user["id"], "name": user["full_name"]}


@router.post("/staff")
def staff_login(body: StaffLogin, request: Request, response: Response):
    if body.password != STAFF_PASSWORD:
        log_event("login_failed", detail="staff")
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    _set_cookie(response, create_session("staff", None))
    query("INSERT INTO audit_log (ts_naive, event, detail, subject_text) VALUES (now()::timestamp, %s, %s, %s)",
          ("staff_login", "Ingreso a Gestión", f"usuario gestion desde {request.client.host if request.client else ''}"))
    log_event("login", detail="staff", role="staff")
    return {"role": "staff"}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        query("DELETE FROM web_sessions WHERE token = %s", (token,))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    sess = current_session(request)
    out = {"role": sess["role"], "user_id": sess["user_id"]}
    if sess["role"] == "customer":
        u = query_one("SELECT full_name, email FROM users WHERE id = %s", (sess["user_id"],))
        out.update(name=u["full_name"], email=u["email"])
    return out
