import secrets
from datetime import datetime

import os
import sqlalchemy as sa
from flask import Flask, jsonify, request
from flask_cors import CORS
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from werkzeug.security import check_password_hash, generate_password_hash

from database import AppSetting, LeaveRequest, User, check_database_health, init_database, session_scope, store_reset_token, consume_reset_token


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

app = Flask(__name__)
CORS(app)
init_database()


def _days_between(start: str, end: str) -> int:
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()
    return (end_date - start_date).days + 1


def _leave_to_dict(leave: LeaveRequest) -> dict:
    return {
        "id": leave.id,
        "user_id": leave.user_id,
        "name": leave.user.name,
        "email": leave.user.email,
        "department": leave.user.department,
        "start": leave.start_date.isoformat(),
        "end": leave.end_date.isoformat(),
        "days": leave.days,
        "reason": leave.reason,
        "type": leave.leave_type,
        "status": leave.status,
        "created_at": leave.created_at.isoformat() + "Z",
    }


def _get_discord_enabled(session) -> bool:
    setting = session.get(AppSetting, "discord_notifications_enabled")
    if setting is None:
        setting = AppSetting(key="discord_notifications_enabled", value="true")
        session.add(setting)
        session.flush()
    return setting.value.lower() == "true"


@app.before_request
def before_request():
    REQUEST_COUNTER.labels(request.method, request.path).inc()


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/api/healthz")
def healthz():
    return jsonify({"status": "ok" if check_database_health() else "degraded"})


@app.get("/api/healthz/live")
def healthz_live():
    return jsonify({"status": "ok"})


@app.get("/api/healthz/ready")
def healthz_ready():
    return jsonify({"status": "ok" if check_database_health() else "degraded"})


@app.post("/api/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    department = payload.get("department", "").strip()

    if not name or not email or not password or not department:
        return jsonify({"error": "Missing required fields"}), 400
    if department not in DEPARTMENTS:
        return jsonify({"error": "Invalid department"}), 400

    with session_scope() as session:
        existing = session.execute(sa.select(User).where(User.email == email)).scalar_one_or_none()
        if existing:
            return jsonify({"error": "User already exists"}), 409

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            department=department,
            is_admin=False,
        )
        session.add(user)
        session.flush()
        return jsonify({"msg": "registered", "user_id": user.id}), 201


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

    with session_scope() as session:
        user = session.execute(sa.select(User).where(User.email == email.lower())).scalar_one_or_none()
        if user is None or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid login"}), 401

        return jsonify(
            {
                "msg": "ok",
                "admin": bool(user.is_admin),
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "department": user.department,
            }
        )


@app.get("/api/balance/<int:user_id>")
def balance(user_id: int):
    with session_scope() as session:
        allowances = {}
        for reason, meta in LEAVE_ALLOWANCES.items():
            used = session.execute(
                sa.select(sa.func.coalesce(sa.func.sum(LeaveRequest.days), 0)).where(
                    LeaveRequest.user_id == user_id,
                    LeaveRequest.reason == reason,
                    LeaveRequest.status == "approved",
                )
            ).scalar_one()
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
    with session_scope() as session:
        items = session.execute(
            sa.select(LeaveRequest).where(LeaveRequest.user_id == user_id).order_by(LeaveRequest.created_at.desc())
        ).scalars().all()
        return jsonify([_leave_to_dict(item) for item in items])


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
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        days = _days_between(start, end)
    except ValueError:
        return jsonify({"error": "Invalid leave date range"}), 400

    if days <= 0:
        return jsonify({"error": "Invalid leave date range"}), 400

    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        leave = LeaveRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=reason,
            leave_type=leave_type,
            status="pending",
        )
        session.add(leave)
        session.flush()
        return jsonify({"msg": "Request submitted!", "id": leave.id}), 201


@app.get("/api/admin/leaves")
def admin_leaves():
    with session_scope() as session:
        items = session.execute(sa.select(LeaveRequest).order_by(LeaveRequest.created_at.desc())).scalars().all()
        return jsonify([_leave_to_dict(item) for item in items])


@app.post("/api/admin/leaves/<int:leave_id>/<action>")
def admin_update_leave(leave_id: int, action: str):
    if action not in {"approved", "rejected"}:
        return jsonify({"error": "Invalid action"}), 400

    with session_scope() as session:
        leave = session.get(LeaveRequest, leave_id)
        if leave is None:
            return jsonify({"error": "Leave not found"}), 404
        leave.status = action
        return jsonify({"msg": "updated"})


@app.post("/api/admin/leaves/bulk")
def admin_bulk_update():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action")
    if action not in {"approved", "rejected"}:
        return jsonify({"error": "Invalid action"}), 400

    with session_scope() as session:
        items = session.execute(sa.select(LeaveRequest).where(LeaveRequest.status == "pending")).scalars().all()
        for leave in items:
            leave.status = action
        return jsonify({"msg": f"{len(items)} requests updated.", "processed": len(items)})


@app.get("/api/admin/settings/discord")
@app.get("/api/admin/notifications/discord")
def admin_get_discord_setting():
    with session_scope() as session:
        return jsonify({"enabled": _get_discord_enabled(session)})


@app.post("/api/admin/settings/discord")
@app.post("/api/admin/notifications/discord")
def admin_set_discord_setting():
    payload = request.get_json(silent=True) or {}
    enabled = bool(payload.get("enabled"))
    with session_scope() as session:
        setting = session.get(AppSetting, "discord_notifications_enabled")
        if setting is None:
            setting = AppSetting(key="discord_notifications_enabled", value="true")
            session.add(setting)
        setting.value = "true" if enabled else "false"
        return jsonify({"enabled": enabled})


@app.post("/api/password/reset/request")
def password_reset_request():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "").strip().lower()
    return_link = bool(payload.get("return_link"))

    with session_scope() as session:
        user = session.execute(sa.select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            return jsonify({"msg": "If the email exists, you will receive a link on Discord."})

        token = secrets.token_urlsafe(24)
        store_reset_token(user.id, token)
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

    record = consume_reset_token(token)
    if record is None:
        return jsonify({"error": "Invalid or expired token"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400

    with session_scope() as session:
        user = session.get(User, record.user_id)
        if user:
            user.password_hash = generate_password_hash(password)
    return jsonify({"msg": "Password reset completed"})


if __name__ == "__main__":
    app.run(
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=bool(os.getenv("UNIT_TESTING")),
    )
