"""Functional tests for the legitimate flows. They use the scripted mock model, so no GPU is needed.

Run inside the api container:  docker compose -f docker-compose.dev.yml exec api pytest
"""

from app.db import query, query_one
from conftest import login


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_visitor_browses_inventory(client):
    r = client.get("/api/inventory", params={"page_size": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0 and len(data["items"]) <= 5
    vehicle = client.get(f"/api/inventory/{data['items'][0]['id']}").json()
    assert vehicle["price"] > 0


def test_visitor_filters_inventory(client):
    brand = client.get("/api/inventory/filters").json()["brands"][0]
    items = client.get("/api/inventory", params={"brand": brand}).json()["items"]
    assert items and all(v["brand"] == brand for v in items)


def test_visitor_semantic_search(client, mock_llm):
    r = client.get("/api/inventory/search", params={"q": "SUV automática"})
    assert r.status_code == 200
    assert "items" in r.json()


def test_customer_login_and_logout(client, customer):
    login(client, customer["email"], customer["password"])
    assert client.get("/api/auth/me").json()["role"] == "customer"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["role"] == "visitor"


def test_wrong_password_is_rejected(client, customer):
    r = client.post("/api/auth/login", json={"email": customer["email"], "password": "otra"})
    assert r.status_code == 401


def test_customer_sees_history_of_own_vehicle(client, customer, mock_llm):
    login(client, customer["email"], customer["password"])
    mock_llm.queue({"action": "get_service_history", "params": {"plate": customer["plate"]}},
                   {"answer": "Su carro tuvo un cambio de aceite."})
    r = client.post("/api/chat", json={"message": f"¿Cuál es el historial de mi carro placa {customer['plate']}?"})
    assert r.status_code == 200
    body = r.json()
    assert body["actions"][0]["action"] == "get_service_history" and body["actions"][0]["ok"]
    assert "aceite" in body["answer"]
    client.post("/api/auth/logout")


def test_assistant_creates_quote_within_policy(client, mock_llm):
    vehicle = query_one("SELECT id, price FROM inventory_vehicles WHERE published AND status = 'available' LIMIT 1")
    mock_llm.queue({"action": "create_quote", "params": {"vehicle_id": vehicle["id"], "customer_email": "cliente@correo.test",
                                                         "discount_pct": 5}},
                   {"answer": "Listo, le envié la cotización."})
    r = client.post("/api/chat", json={"message": f"Quiero una cotización del {vehicle['id']}"})
    assert r.status_code == 200
    quote = query_one("SELECT discount_pct, final_price FROM quotes WHERE vehicle_id = %s ORDER BY created_at DESC LIMIT 1",
                      (vehicle["id"],))
    assert float(quote["discount_pct"]) == 5
    assert quote["final_price"] == round(vehicle["price"] * 0.95, -3)


def test_customer_can_reserve(client, customer):
    login(client, customer["email"], customer["password"])
    vehicle = query_one("SELECT id FROM inventory_vehicles WHERE published AND status = 'available' LIMIT 1")
    r = client.post("/api/reservations", json={"vehicle_id": vehicle["id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deposit"] == 100000 and body["sinpe_number"] == "8000-0100" and body["status"] == "pending"
    mine = client.get("/api/reservations/mine").json()
    assert any(x["code"] == body["reservation"] for x in mine)
    client.post("/api/auth/logout")


def test_visitor_cannot_reserve(client):
    vehicle = query_one("SELECT id FROM inventory_vehicles WHERE published LIMIT 1")
    client.post("/api/auth/logout")
    assert client.post("/api/reservations", json={"vehicle_id": vehicle["id"]}).status_code == 401


def test_chat_creates_session_and_history(client, mock_llm):
    mock_llm.queue({"answer": "¡Hola! ¿En qué le ayudo?"})
    r = client.post("/api/chat", json={"message": "Hola"}).json()
    history = client.get(f"/api/chat/{r['session_id']}").json()["messages"]
    assert [m["role"] for m in history] == ["user", "assistant"]


def test_staff_sees_conversations_and_reservations(client):
    assert client.post("/api/auth/staff", json={"password": "incorrecta"}).status_code == 401
    from app.auth import STAFF_PASSWORD
    assert client.post("/api/auth/staff", json={"password": STAFF_PASSWORD}).status_code == 200
    assert isinstance(client.get("/api/staff/conversations").json(), list)
    assert isinstance(client.get("/api/staff/reservations").json(), list)
    assert isinstance(client.get("/api/staff/quotes").json(), list)
    for path in ("/api/staff/quotes", "/api/staff/quotes/Q-001/close", "/api/staff/inventory/V-001/price"):
        assert client.post(path).status_code == 503
    client.post("/api/auth/logout")


def test_staff_console_requires_staff(client):
    client.post("/api/auth/logout")
    assert client.get("/api/staff/reservations").status_code == 401


def test_bootstrap_status(client):
    status = client.get("/api/admin/bootstrap/status").json()
    assert {"schema", "load"} <= set(status["stages"])


def test_mcp_endpoint_answers(client):
    r = client.post("/mcp", headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
                    json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "1"}}})
    assert r.status_code == 200
    assert query("SELECT 1 AS ok")


def test_customer_sees_own_reservations_and_vehicles(client, customer, mock_llm):
    login(client, customer["email"], customer["password"])
    mock_llm.queue({"action": "get_my_vehicles", "params": {}}, {"action": "get_my_reservations", "params": {}}, {"answer": "Listo."})
    body = client.post("/api/chat", json={"message": "¿Cuáles son mis carros y mis reservas?"}).json()
    assert [a["action"] for a in body["actions"]] == ["get_my_vehicles", "get_my_reservations"] and all(a["ok"] for a in body["actions"])
    system = mock_llm.calls[0][0]["content"]
    assert customer["plate"] in system
    client.post("/api/auth/logout")


def test_visitor_cannot_use_account_actions(client, mock_llm):
    client.post("/api/auth/logout")
    mock_llm.queue({"action": "get_my_reservations", "params": {}}, {"answer": "Debe iniciar sesión."})
    body = client.post("/api/chat", json={"message": "mis reservas"}).json()
    assert body["actions"][0]["ok"] is False
