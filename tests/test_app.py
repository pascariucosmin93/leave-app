def test_register_requires_fields(client):
    resp = client.post("/api/register", json={"name": "Test"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Missing required fields"


def test_register_invalid_department(client):
    payload = {
        "name": "Tester",
        "email": "tester@example.com",
        "password": "secret",
        "department": "Unknown",
    }
    resp = client.post("/api/register", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Invalid department"


def test_leave_invalid_interval(client):
    register_payload = {
        "name": "Tester",
        "email": "tester@example.com",
        "password": "secret",
        "department": "Finance",
    }
    register_resp = client.post("/api/register", json=register_payload)
    user_id = register_resp.get_json()["user_id"]
    payload = {
        "user_id": user_id,
        "start": "2024-10-02",
        "end": "2024-10-01",
        "type": "normal",
        "reason": "Annual leave",
    }
    resp = client.post("/api/leave", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Invalid leave date range"


def test_healthz(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"

