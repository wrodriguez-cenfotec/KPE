import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hashlib
import secrets

import pytest
from fastapi.testclient import TestClient

from app.db import pool, query, query_one
from app.llm.mock_provider import MockProvider
from app.llm.provider import set_provider
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def mock_llm():
    provider = MockProvider()
    set_provider(provider)
    yield provider
    set_provider(None)


def _hash(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"pbkdf2_sha256$100000${salt}${digest}"


@pytest.fixture()
def customer():
    """A throwaway customer with one vehicle and one service record."""
    if pool.closed:
        pool.open()
    suffix = secrets.token_hex(3)
    email, password = f"prueba.{suffix}@correo.test", "Prueba123"
    user = query_one(
        "INSERT INTO users (role, full_name, national_id, phone, email, password_hash, created_at) "
        "VALUES ('customer', 'Cliente de Prueba', '1-0000-0000', '8000-0000', %s, %s, now()) RETURNING id",
        (email, _hash(password, suffix)))
    plate = f"TST-{secrets.randbelow(900) + 100}"
    query("INSERT INTO customer_vehicles (plate, owner_user_id, brand, model, year) VALUES (%s, %s, 'Toyota', 'Yaris', 2019)",
          (plate, user["id"]))
    query("INSERT INTO service_records (plate, service_date, km, notes) VALUES (%s, current_date, 50000, 'Cambio de aceite.')", (plate,))
    yield {"id": user["id"], "email": email, "password": password, "plate": plate}
    query("DELETE FROM web_sessions WHERE user_id = %s", (user["id"],))
    query("DELETE FROM reservations WHERE customer_id = %s", (user["id"],))
    query("UPDATE chat_sessions SET user_id = NULL WHERE user_id = %s", (user["id"],))
    query("UPDATE assistant_actions SET actor_user_id = NULL WHERE actor_user_id = %s", (user["id"],))
    query("DELETE FROM service_records WHERE plate = %s", (plate,))
    query("DELETE FROM customer_vehicles WHERE plate = %s", (plate,))
    query("DELETE FROM users WHERE id = %s", (user["id"],))


def login(client: TestClient, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
