"""Optional SQLAlchemy database layer for future Neon integration."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = None
SessionLocal: sessionmaker[Session] | None = None
Base = declarative_base()

if settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session when DATABASE_URL is configured."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_available() -> bool:
    """Return True when a database connection can be established."""
    return engine is not None
