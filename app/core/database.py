"""SQLAlchemy engine, session factory, and database helpers."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.database_models import Base

logger = logging.getLogger(__name__)

settings = get_settings()

engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _normalize_database_url(url: str) -> str:
    """Ensure SQLAlchemy uses the psycopg (v3) driver."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _init_engine() -> None:
    """Initialize engine and session factory when DATABASE_URL is set."""
    global engine, SessionLocal
    if engine is not None or SessionLocal is not None:
        return
    if not settings.DATABASE_URL:
        return
    try:
        db_url = _normalize_database_url(settings.DATABASE_URL)
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database engine initialized.")
    except Exception as exc:
        logger.warning("Database engine not available: %s", exc)
        engine = None
        SessionLocal = None


_init_engine()


def database_configured() -> bool:
    """Return True when DATABASE_URL is set."""
    return bool(settings.DATABASE_URL)


def database_available() -> bool:
    """Return True when the database engine can execute a simple query."""
    _init_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def anomaly_results_populated() -> bool:
    """Return True when anomaly_results has at least one row."""
    _init_engine()
    if engine is None:
        return False
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT 1 FROM anomaly_results LIMIT 1")
            ).first()
            return row is not None
    except Exception:
        return False


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    _init_engine()
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured or engine failed to start.")
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    _init_engine()
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Create all tables (development helper — prefer Alembic in production)."""
    _init_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    Base.metadata.create_all(bind=engine)
