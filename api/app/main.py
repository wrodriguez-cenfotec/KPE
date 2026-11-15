import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from .auth import COOKIE_NAME, session_from_token
from .bootstrap import runner
from .db import pool
from .logs import log_event, new_request_id, request_ctx
from .mcp_server.server import build_app, server as mcp_server
from .routes import admin, auth, chat, health, public, reservations, search, staff


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=False)
    runner.start_background()
    log_event("startup", detail="api started")
    async with mcp_server.session_manager.run():
        yield
    pool.close()


app = FastAPI(title="KPE API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def request_context(request: Request, call_next):
    started = time.monotonic()
    sess = session_from_token(request.cookies.get(COOKIE_NAME)) if request.url.path.startswith("/api/") else {"role": None, "user_id": None}
    request.state.session = sess
    token = request_ctx.set({
        "request_id": new_request_id(),
        "src_ip": request.client.host if request.client else None,
        "route": request.url.path,
        "role": sess["role"],
        "user_id": sess["user_id"],
        "session_id": None,
    })
    try:
        response = await call_next(request)
        if request.url.path not in ("/api/health",):
            log_event("http_request", detail=f"{request.method} {request.url.path} {response.status_code}",
                      duration_ms=int((time.monotonic() - started) * 1000))
        return response
    finally:
        request_ctx.reset(token)


for module in (health, auth, chat, search, public, reservations, staff, admin):
    app.include_router(module.router)

mcp_app = build_app()
app.mount("/", mcp_app)
