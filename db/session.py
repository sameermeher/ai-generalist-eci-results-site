"""Async and sync SQLAlchemy engine/session factories."""

from typing import AsyncGenerator
from urllib.parse import urlparse, urlunparse, parse_qs

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from config import settings


def _as_asyncpg_url(url: str) -> tuple[str, dict]:
    """Normalise a postgres URL to use the asyncpg driver.

    asyncpg does not accept any libpq/psycopg2 query-string params.
    Strip them all; pass ssl=True via connect_args when the URL had
    sslmode=require / verify-full / verify-ca.
    """
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    # Detect SSL requirement before stripping
    sslmode = params.get("sslmode", [None])[0]
    needs_ssl = sslmode and sslmode not in ("disable", "allow", "prefer")

    # asyncpg accepts no query-string params — strip everything
    url = urlunparse(parsed._replace(query=""))

    connect_args: dict = {}
    if needs_ssl:
        connect_args["ssl"] = True

    return url, connect_args


def _as_psycopg2_url(url: str) -> str:
    """Normalise a postgres URL to use the psycopg2 driver."""
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


# ---------------------------------------------------------------------------
# Async engine (used by FastAPI)
# ---------------------------------------------------------------------------

_async_url, _async_connect_args = _as_asyncpg_url(settings.database_url)

async_engine = create_async_engine(
    _async_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_async_connect_args,
)

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Sync engine (used by Alembic migrations and ETL loaders)
# ---------------------------------------------------------------------------

sync_engine = create_engine(
    _as_psycopg2_url(settings.database_url_sync),
    echo=settings.app_env == "development",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SyncSessionFactory: sessionmaker[Session] = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


def get_sync_session() -> Session:
    """Return a sync session (caller must close it)."""
    return SyncSessionFactory()
