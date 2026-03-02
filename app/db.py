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

from dotenv import load_dotenv
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _build_database_url() -> str:
    """
    Resolve the database URL from the environment.

    Normalises the driver prefix so asyncpg is always used for Postgres.
    Falls back to a local SQLite file when DATABASE_URL is not set.
    """
    raw = os.getenv("DATABASE_URL", "")
    if raw:
        # Neon (and most providers) give postgresql:// — asyncpg requires postgresql+asyncpg://
        if raw.startswith("postgresql://"):
            return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
        if raw.startswith("postgres://"):  # older Heroku / Render format
            return raw.replace("postgres://", "postgresql+asyncpg://", 1)
        return raw  # already has the correct driver prefix
    # Local dev fallback — SQLite, no Postgres credentials required
    return "sqlite+aiosqlite:///./cases.db"


DATABASE_URL = _build_database_url()

# check_same_thread is a SQLite-only option; Postgres ignores it
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

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

async def create_tables() -> None:
    """
    Create all ORM tables if they do not yet exist.

    Called once during FastAPI lifespan startup. Safe to call repeatedly —
    SQLAlchemy uses CREATE TABLE IF NOT EXISTS semantics.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
