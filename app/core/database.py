"""
Async database engine and session factory.
Also provides sync sessions for Celery workers.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from contextlib import contextmanager
from app.core.config import settings


# ── Async (FastAPI) ───────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=300,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency: yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Sync (Celery workers) ─────────────────────────────
# Lazy init — only create sync engine when first needed

_sync_engine = None
_SyncSessionFactory = None


def _get_sync_engine():
    global _sync_engine, _SyncSessionFactory
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.database_url_sync,
            echo=False,
            pool_size=5,
            max_overflow=3,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        _SyncSessionFactory = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _sync_engine, _SyncSessionFactory


@contextmanager
def get_sync_db():
    """Context manager: yields a sync DB session for Celery tasks."""
    _, factory = _get_sync_engine()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
