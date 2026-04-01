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


def test_register_success(client):
    payload = {
        "name": "Tester",
        "email": "tester@example.com",
        "password": "secret123",
        "department": "Finance",
    }
    resp = client.post("/api/register", json=payload)
    assert resp.status_code == 201
    assert resp.get_json()["msg"] == "registered"


def test_register_duplicate_email(client, registered_user):
    resp = client.post("/api/register", json=registered_user["payload"])
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "User already exists"


def test_login_success(client, registered_user):
    resp = client.post(
        "/api/login",
        json={"email": registered_user["payload"]["email"], "password": registered_user["payload"]["password"]},
    )
    assert resp.status_code == 200
    assert resp.get_json()["msg"] == "ok"
    assert resp.get_json()["admin"] is False


def test_login_invalid_password(client, registered_user):
    resp = client.post("/api/login", json={"email": registered_user["payload"]["email"], "password": "wrong"})
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "Invalid login"


def test_leave_invalid_interval(client, registered_user):
    payload = {
        "user_id": registered_user["user_id"],
        "start": "2024-10-02",
        "end": "2024-10-01",
        "type": "normal",
        "reason": "Annual leave",
    }
    resp = client.post("/api/leave", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Invalid leave date range"


def test_leave_create_and_list(client, registered_user):
    payload = {
        "user_id": registered_user["user_id"],
        "start": "2024-10-01",
        "end": "2024-10-03",
        "type": "normal",
        "reason": "Annual leave",
    }
    create_resp = client.post("/api/leave", json=payload)
    assert create_resp.status_code == 201

    list_resp = client.get(f"/api/leaves/{registered_user['user_id']}")
    data = list_resp.get_json()
    assert list_resp.status_code == 200
    assert len(data) == 1
    assert data[0]["days"] == 3
    assert data[0]["status"] == "pending"


def test_balance_after_approval(client, registered_user):
    payload = {
        "user_id": registered_user["user_id"],
        "start": "2024-10-01",
        "end": "2024-10-03",
        "type": "normal",
        "reason": "Annual leave",
    }
    leave_id = client.post("/api/leave", json=payload).get_json()["id"]
    approve_resp = client.post(f"/api/admin/leaves/{leave_id}/approved")
    assert approve_resp.status_code == 200

    balance_resp = client.get(f"/api/balance/{registered_user['user_id']}")
    balance = balance_resp.get_json()
    assert balance_resp.status_code == 200
    assert balance["allowances"]["Annual leave"]["remaining"] == 18


def test_admin_bulk_update(client, registered_user):
    for start, end in [("2024-10-01", "2024-10-02"), ("2024-10-05", "2024-10-05")]:
        client.post(
            "/api/leave",
            json={
                "user_id": registered_user["user_id"],
                "start": start,
                "end": end,
                "type": "normal",
                "reason": "Annual leave",
            },
        )

    bulk_resp = client.post("/api/admin/leaves/bulk", json={"action": "approved"})
    all_resp = client.get("/api/admin/leaves")
    assert bulk_resp.status_code == 200
    assert bulk_resp.get_json()["processed"] == 2
    assert all(item["status"] == "approved" for item in all_resp.get_json())


def test_discord_toggle(client):
    get_resp = client.get("/api/admin/notifications/discord")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["enabled"] is True

    set_resp = client.post("/api/admin/notifications/discord", json={"enabled": False})
    assert set_resp.status_code == 200
    assert set_resp.get_json()["enabled"] is False


def test_password_reset_flow(client, registered_user):
    request_resp = client.post(
        "/api/password/reset/request",
        json={"email": registered_user["payload"]["email"], "return_link": True},
    )
    reset_link = request_resp.get_json()["reset_link"]
    token = reset_link.split("token=")[1]

    confirm_resp = client.post(
        "/api/password/reset/confirm",
        json={"token": token, "password": "newsecret"},
    )
    login_resp = client.post(
        "/api/login",
        json={"email": registered_user["payload"]["email"], "password": "newsecret"},
    )

    assert confirm_resp.status_code == 200
    assert login_resp.status_code == 200
    assert login_resp.get_json()["msg"] == "ok"


def test_password_reset_invalid_token(client):
    resp = client.post("/api/password/reset/confirm", json={"token": "bad", "password": "newsecret"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "Invalid or expired token"


def test_healthz(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
