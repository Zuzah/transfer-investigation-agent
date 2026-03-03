"""
Database layer — SQLAlchemy async engine + Case ORM model.

Supports two backends:
  Postgres (Neon): set DATABASE_URL to a postgresql:// connection string.
    asyncpg is used as the async driver; the prefix is normalised automatically.
  SQLite (local dev fallback): if DATABASE_URL is unset, uses cases.db in the
    repo root. No Postgres account needed for local development.

Tables are created automatically on FastAPI startup via create_tables().
"""

import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import JSON, DateTime, String, Text, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _build_database_url() -> str:
    """
    Resolve the database URL from the environment.

    Two normalisations are applied for asyncpg compatibility:
      1. Driver prefix: postgresql:// → postgresql+asyncpg://
      2. All query parameters are stripped from the URL.
         asyncpg does not accept libpq-style parameters such as sslmode=,
         channel_binding=, or others that managed providers (Neon, Supabase)
         append by default. SSL is handled separately via connect_args.

    Falls back to a local SQLite file when DATABASE_URL is not set.
    """
    raw = os.getenv("DATABASE_URL", "")
    if raw:
        # Normalise driver prefix so asyncpg is always used for Postgres
        if raw.startswith("postgresql://"):
            raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif raw.startswith("postgres://"):  # older Heroku / Render format
            raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
        # Strip all query parameters — libpq params confuse asyncpg.
        # SSL is passed through _connect_args below instead.
        parsed = urlparse(raw)
        return urlunparse(parsed._replace(query=""))
    # Local dev fallback — SQLite, no Postgres credentials required
    return "sqlite+aiosqlite:///./cases.db"


DATABASE_URL = _build_database_url()

if DATABASE_URL.startswith("sqlite"):
    # check_same_thread is SQLite-specific
    _connect_args: dict = {"check_same_thread": False}
else:
    # Neon and most managed Postgres providers require SSL.
    # Passed here rather than as a URL param because asyncpg uses 'ssl', not 'sslmode'.
    _connect_args = {"ssl": "require"}

engine = create_async_engine(DATABASE_URL, connect_args=_connect_args, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class Case(Base):
    """
    A transfer complaint case record.

    Lifecycle: open → investigated (once AI analysis runs) → resolved | escalated.
    result_json stores the full serialised InvestigationResult dict.
    """

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    checklist_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    department: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


# ---------------------------------------------------------------------------
# Session dependency (FastAPI Depends)
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession.

    Commits on success, rolls back on any exception, always closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def _apply_schema_migrations(conn) -> None:
    """
    Code-first schema reconciliation.

    Inspects the live database columns for each ORM table and adds any columns
    that exist in the ORM model but are missing from the actual table. This
    runs after create_all so new tables are always fully created on first start.

    Adding a column to the ORM model is the only change needed — this function
    detects and applies it automatically without try/except error-swallowing.
    """
    inspector = inspect(conn)

    # Guard: table may not exist yet on very first startup (create_all handles it)
    if "cases" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_columns("cases")}
    if "checklist_json" not in existing:
        conn.execute(text("ALTER TABLE cases ADD COLUMN checklist_json JSON"))


async def create_tables() -> None:
    """
    Create all ORM tables if they do not yet exist, then reconcile the live
    schema with the current ORM model.

    Called once during FastAPI lifespan startup. Safe to call repeatedly —
    SQLAlchemy uses CREATE TABLE IF NOT EXISTS semantics.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_schema_migrations)
