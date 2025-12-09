"""Database session helpers."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from sensorpi.config.settings import Settings

_settings = Settings()
_engine = create_engine(
    _settings.database.dsn,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)
_SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)


@contextmanager
def get_session() -> Iterator[Session]:
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - pass-through
        session.rollback()
        raise
    finally:
        session.close()
