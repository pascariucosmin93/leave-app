import os
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    return str(
        URL.create(
            "postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "concedii"),
            password=os.getenv("POSTGRES_PASSWORD", "concedii"),
            host=os.getenv("POSTGRES_HOST", "postgres.postgress.svc.cluster.local"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "concedii"),
        )
    )


DATABASE_URL = build_database_url()


class Base(DeclarativeBase):
    pass


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow_naive)

    leaves: Mapped[list["LeaveRequest"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow_naive)

    user: Mapped[User] = relationship(back_populates="leaves")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


def _engine_kwargs() -> dict:
    if DATABASE_URL.startswith("sqlite"):
        kwargs = {"future": True}
        if ":memory:" in DATABASE_URL:
            kwargs["poolclass"] = StaticPool
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["connect_args"] = {"check_same_thread": False}
        return kwargs
    return {"future": True, "pool_pre_ping": True, "connect_args": {"connect_timeout": 3}}


engine = create_engine(DATABASE_URL, **_engine_kwargs())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _is_duplicate_postgres_object_error(exc: DBAPIError) -> bool:
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
    return sqlstate in {"42710", "42P04", "23505"}


def bootstrap_postgres_if_needed() -> None:
    if DATABASE_URL.startswith("sqlite"):
        return
    if not _bool_env("BOOTSTRAP_DB", default=False):
        return

    url = make_url(DATABASE_URL)
    target_database = url.database
    target_user = url.username
    target_password = url.password or ""

    admin_url = URL.create(
        "postgresql+psycopg",
        username=os.getenv("BOOTSTRAP_POSTGRES_ADMIN_USER", "devops"),
        password=os.getenv("BOOTSTRAP_POSTGRES_ADMIN_PASSWORD", ""),
        host=os.getenv("BOOTSTRAP_POSTGRES_HOST", url.host or "postgres.postgress.svc.cluster.local"),
        port=int(os.getenv("BOOTSTRAP_POSTGRES_PORT", str(url.port or 5432))),
        database=os.getenv("BOOTSTRAP_POSTGRES_ADMIN_DB", "postgres"),
    )
    admin_engine = create_engine(
        admin_url,
        future=True,
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 3},
    )

    try:
        with admin_engine.connect() as conn:
            conn.execute(sa.text("SELECT pg_advisory_lock(2147483001)"))

            role_exists = conn.execute(
                sa.text("SELECT 1 FROM pg_roles WHERE rolname = :username"),
                {"username": target_user},
            ).scalar()
            if not role_exists:
                try:
                    conn.execute(
                        sa.text(
                            f"CREATE ROLE {_quote_ident(target_user)} LOGIN PASSWORD {_quote_literal(target_password)}"
                        )
                    )
                except DBAPIError as exc:
                    if not _is_duplicate_postgres_object_error(exc):
                        raise

            db_exists = conn.execute(
                sa.text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": target_database},
            ).scalar()
            if not db_exists:
                try:
                    conn.execute(
                        sa.text(f"CREATE DATABASE {_quote_ident(target_database)} OWNER {_quote_ident(target_user)}")
                    )
                except DBAPIError as exc:
                    if not _is_duplicate_postgres_object_error(exc):
                        raise
    finally:
        admin_engine.dispose()


def init_database() -> None:
    bootstrap_postgres_if_needed()
    Base.metadata.create_all(bind=engine)

    with session_scope() as session:
        if session.get(AppSetting, "discord_notifications_enabled") is None:
            session.add(AppSetting(key="discord_notifications_enabled", value="true"))


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True
    except OperationalError:
        return False


def store_reset_token(user_id: int, token: str, ttl_minutes: int = 30) -> None:
    expires_at = utcnow_naive() + timedelta(minutes=ttl_minutes)
    with session_scope() as session:
        session.merge(PasswordResetToken(token=token, user_id=user_id, expires_at=expires_at))


def consume_reset_token(token: str) -> PasswordResetToken | None:
    with session_scope() as session:
        record = session.get(PasswordResetToken, token)
        if record is None:
            return None
        if record.expires_at <= utcnow_naive():
            session.delete(record)
            return None

        data = PasswordResetToken(token=record.token, user_id=record.user_id, expires_at=record.expires_at)
        session.delete(record)
        return data
