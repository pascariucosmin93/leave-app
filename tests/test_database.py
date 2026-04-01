import importlib
import os
from datetime import timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

import database


def test_bool_env_parsing(monkeypatch):
    monkeypatch.delenv("FLAG", raising=False)
    assert database._bool_env("FLAG", default=True) is True

    monkeypatch.setenv("FLAG", "yes")
    assert database._bool_env("FLAG") is True

    monkeypatch.setenv("FLAG", "off")
    assert database._bool_env("FLAG") is False


def test_build_database_url_from_explicit_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///explicit.db")
    assert database.build_database_url() == "sqlite:///explicit.db"


def test_build_database_url_from_postgres_parts(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "user1")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass1")
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "leave")

    url = database.build_database_url()
    assert url == "postgresql+psycopg://user1:***@db.internal:5433/leave"


def test_quote_helpers():
    assert database._quote_ident('a"b') == '"a""b"'
    assert database._quote_literal("o'hara") == "'o''hara'"


def test_engine_kwargs_for_sqlite(monkeypatch):
    monkeypatch.setattr(database, "DATABASE_URL", "sqlite:///:memory:")
    kwargs = database._engine_kwargs()
    assert kwargs["poolclass"] is database.StaticPool
    assert kwargs["connect_args"]["check_same_thread"] is False


def test_duplicate_postgres_object_error_helper():
    class FakeOrig:
        sqlstate = "42P04"

    class FakeDBAPIError(Exception):
        orig = FakeOrig()

    assert database._is_duplicate_postgres_object_error(FakeDBAPIError()) is True


def test_session_scope_rolls_back_on_error():
    with pytest.raises(RuntimeError):
        with database.session_scope() as session:
            session.add(database.AppSetting(key="rollback-key", value="x"))
            raise RuntimeError("boom")

    with database.session_scope() as session:
        assert session.get(database.AppSetting, "rollback-key") is None


def test_check_database_health_false(monkeypatch):
    class BrokenConnection:
        def __enter__(self):
            raise OperationalError("SELECT 1", {}, Exception("db down"))

        def __exit__(self, exc_type, exc, tb):
            return False

    class BrokenEngine:
        def connect(self):
            return BrokenConnection()

    monkeypatch.setattr(database, "engine", BrokenEngine())
    assert database.check_database_health() is False


def test_store_and_consume_reset_token():
    database.store_reset_token(7, "token-123", ttl_minutes=30)
    record = database.consume_reset_token("token-123")
    assert record is not None
    assert record.user_id == 7
    assert database.consume_reset_token("token-123") is None


def test_consume_expired_reset_token():
    expired = database.utcnow_naive() - timedelta(minutes=1)
    with database.session_scope() as session:
        session.merge(database.PasswordResetToken(token="expired", user_id=1, expires_at=expired))

    assert database.consume_reset_token("expired") is None


def test_bootstrap_postgres_noop_for_sqlite(monkeypatch):
    monkeypatch.setattr(database, "DATABASE_URL", "sqlite:///unit.db")
    database.bootstrap_postgres_if_needed()


def test_init_database_adds_default_setting():
    database.init_database()
    with database.session_scope() as session:
        setting = session.get(database.AppSetting, "discord_notifications_enabled")
        assert setting is not None
        assert setting.value == "true"


def test_gunicorn_conf_reads_environment(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("GUNICORN_WORKERS", "4")
    monkeypatch.setenv("GUNICORN_THREADS", "8")
    monkeypatch.setenv("GUNICORN_TIMEOUT", "120")
    monkeypatch.setenv("GUNICORN_WORKER_CLASS", "gthread")

    import gunicorn_conf

    module = importlib.reload(gunicorn_conf)
    assert module.bind == "0.0.0.0:9000"
    assert module.workers == 4
    assert module.threads == 8
    assert module.timeout == 120
    assert module.worker_class == "gthread"
