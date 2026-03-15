"""Sync SQLAlchemy session management for scraper — equivalent to sports-data-admin scraper db.py."""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the sync engine."""
    global _engine
    if _engine is None:
        database_url = os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql://postgres:postgres@localhost:5432/findata",
        )
        _engine = create_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_db_session() -> Session:
    """Context manager for a sync database session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
