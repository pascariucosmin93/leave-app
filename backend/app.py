import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest


DEPARTMENTS = {
    "Human Resources",
    "Finance",
    "Information Technology",
    "Marketing",
    "Sales",
    "Operations",
    "Customer Support",
    "Legal",
    "Procurement",
    "Research & Development",
}

LEAVE_ALLOWANCES = {
    "Annual leave": {"type": "normal", "allocation": 21},
    "Unpaid leave": {"type": "special", "allocation": 30},
    "Employee's wedding": {"type": "special", "allocation": 5},
    "Child's wedding": {"type": "special", "allocation": 2},
    "Birth of a child": {"type": "special", "allocation": 5},
    "Paternity leave": {"type": "special", "allocation": 10},
    "Care for a sick child": {"type": "special", "allocation": 5},
    "Family bereavement (spouse, child, parents, in-laws)": {"type": "special", "allocation": 3},
    "Family bereavement (grandparents, siblings)": {"type": "special", "allocation": 1},
    "Blood donation": {"type": "special", "allocation": 1},
}

REQUEST_COUNTER = Counter("employee_leave_http_requests_total", "HTTP requests", ["method", "path"])


def _days_between(start: str, end: str) -> int:
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    return (end_date - start_date).days + 1


@dataclass
class MemoryStore:
    users: dict[int, dict] = field(default_factory=dict)
    users_by_email: dict[str, int] = field(default_factory=dict)
    leaves: list[dict] = field(default_factory=list)
    reset_tokens: dict[str, str] = field(default_factory=dict)
    next_user_id: int = 1
    next_leave_id: int = 1
    discord_notifications_enabled: bool = True

    def create_user(self, name: str, email: str, password: str, department: str) -> dict:
        user = {
            "user_id": self.next_user_id,
            "name": name,
            "email": email,
            "password": password,
            "department": department,
            "admin": False,
        }
        self.users[self.next_user_id] = user
        self.users_by_email[email.lower()] = self.next_user_id
        self.next_user_id += 1
        return user

    def get_user_by_email(self, email: str) -> dict | None:
        user_id = self.users_by_email.get(email.lower())
        if not user_id:
            return None
        return self.users[user_id]


store = MemoryStore()
app = Flask(__name__)
CORS(app)


@app.before_request
def before_request():
    REQUEST_COUNTER.labels(request.method, request.path).inc()


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/api/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.post("/api/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip()
    password = payload.get("password", "")
    department = payload.get("department", "").strip()

    if not name or not email or not password or not department:
        return jsonify({"error": "Missing required fields"}), 400
    if department not in DEPARTMENTS:
        return jsonify({"error": "Invalid department"}), 400
    if store.get_user_by_email(email):
        return jsonify({"error": "User already exists"}), 409

    user = store.create_user(name, email, password, department)
    return jsonify({"msg": "registered", "user_id": user["user_id"]}), 201


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    password = payload.get("password", "")

    admin_email = os.getenv("ADMIN_EMAIL", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if email == admin_email and password == admin_password:
        return jsonify(
            {
                "msg": "ok",
                "admin": True,
                "user_id": 0,
                "name": "Administrator",
                "email": admin_email,
                "department": "Administration",
            }
        )

    user = store.get_user_by_email(email)
    if not user or user["password"] != password:
        return jsonify({"error": "Invalid login"}), 401

    return jsonify(
        {
            "msg": "ok",
            "admin": False,
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "department": user["department"],
        }
    )


@app.get("/api/balance/<int:user_id>")
def balance(user_id: int):
    allowances = {}
    for reason, meta in LEAVE_ALLOWANCES.items():
        used = sum(
            leave["days"]
            for leave in store.leaves
            if leave["user_id"] == user_id and leave["reason"] == reason and leave["status"] == "approved"
        )
        total = meta["allocation"]
        allowances[reason] = {"total": total, "remaining": max(total - used, 0)}

    return jsonify(
        {
            "normal_days": allowances["Annual leave"]["remaining"],
            "special_days": sum(value["remaining"] for key, value in allowances.items() if key != "Annual leave"),
            "allowances": allowances,
        }
    )


@app.get("/api/leaves/<int:user_id>")
def user_leaves(user_id: int):
    items = [leave for leave in store.leaves if leave["user_id"] == user_id]
    return jsonify(items)


@app.post("/api/leave")
def create_leave():
    payload = request.get_json(silent=True) or {}
    try:
        user_id = int(payload.get("user_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Missing required fields"}), 400

    start = payload.get("start")
    end = payload.get("end")
    reason = payload.get("reason")
    leave_type = payload.get("type", "special")

    if not start or not end or not reason:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        days = _days_between(start, end)
    except ValueError:
        return jsonify({"error": "Invalid leave date range"}), 400

    if days <= 0:
        return jsonify({"error": "Invalid leave date range"}), 400

    leave = {
        "id": store.next_leave_id,
        "user_id": user_id,
        "name": store.users.get(user_id, {}).get("name", "Unknown"),
        "email": store.users.get(user_id, {}).get("email", ""),
        "department": store.users.get(user_id, {}).get("department", "General"),
        "start": start,
        "end": end,
        "days": days,
        "reason": reason,
        "type": leave_type,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    store.next_leave_id += 1
    store.leaves.append(leave)
    return jsonify({"msg": "Request submitted!", "id": leave["id"]}), 201


@app.get("/api/admin/leaves")
def admin_leaves():
    return jsonify(store.leaves)


@app.post("/api/admin/leaves/<int:leave_id>/<action>")
def admin_update_leave(leave_id: int, action: str):
    if action not in {"approved", "rejected"}:
        return jsonify({"error": "Invalid action"}), 400
    for leave in store.leaves:
        if leave["id"] == leave_id:
            leave["status"] = action
            return jsonify({"msg": "updated"})
    return jsonify({"error": "Leave not found"}), 404


@app.post("/api/admin/leaves/bulk")
def admin_bulk_update():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    if action not in {"approved", "rejected"}:
        return jsonify({"error": "Invalid action"}), 400

    processed = 0
    for leave in store.leaves:
        if leave["status"] == "pending":
            leave["status"] = action
            processed += 1
    return jsonify({"msg": f"{processed} requests updated.", "processed": processed})


@app.get("/api/admin/settings/discord")
def admin_get_discord_setting():
    return jsonify({"enabled": store.discord_notifications_enabled})


@app.post("/api/admin/settings/discord")
def admin_set_discord_setting():
    payload = request.get_json(silent=True) or {}
    store.discord_notifications_enabled = bool(payload.get("enabled"))
    return jsonify({"enabled": store.discord_notifications_enabled})


@app.post("/api/password/reset/request")
def password_reset_request():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip()
    return_link = bool(payload.get("return_link"))
    user = store.get_user_by_email(email)

    if not user:
        return jsonify({"msg": "If the email exists, you will receive a link on Discord."})

    token = secrets.token_urlsafe(24)
    store.reset_tokens[token] = user["email"]
    response = {"msg": "Reset request accepted"}
    if return_link:
        base_url = os.getenv("RESET_PASSWORD_BASE_URL", "http://localhost/reset.html")
        response["reset_link"] = f"{base_url}?token={token}"
    return jsonify(response)


@app.post("/api/password/reset/confirm")
def password_reset_confirm():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    password = payload.get("password")
    email = store.reset_tokens.pop(token, None)
    if not email:
        return jsonify({"error": "Invalid or expired token"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400

    user = store.get_user_by_email(email)
    if user:
        user["password"] = password
    return jsonify({"msg": "Password reset completed"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=bool(os.getenv("UNIT_TESTING")))

