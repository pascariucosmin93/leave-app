import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("UNIT_TESTING", "1")
os.environ.setdefault("DISCORD_WEBHOOK", "")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'test.db'}")
os.environ.setdefault("BOOTSTRAP_DB", "false")


@pytest.fixture
def client():
    from app import app
    from database import AppSetting, Base, engine, session_scope

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with session_scope() as session:
        session.add(AppSetting(key="discord_notifications_enabled", value="true"))
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


@pytest.fixture
def registered_user(client):
    payload = {
        "name": "Tester",
        "email": "tester@example.com",
        "password": "secret123",
        "department": "Finance",
    }
    response = client.post("/api/register", json=payload)
    data = response.get_json()
    return {"response": response, "payload": payload, "user_id": data["user_id"]}
