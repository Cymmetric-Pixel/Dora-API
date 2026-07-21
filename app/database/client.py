"""Postgres connection pool via psycopg2."""

from collections.abc import Generator
from contextlib import contextmanager

from psycopg2.extensions import connection
from psycopg2.pool import ThreadedConnectionPool

from app.config import settings

_pool: ThreadedConnectionPool | None = None


def init_db() -> None:
    """Create the connection pool on app startup."""
    global _pool
    _pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=settings.database_url,
    )


def close_db() -> None:
    """Close all pooled connections on app shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


@contextmanager
def database_session() -> Generator[connection]:
    """Borrow a connection from the pool for the duration of the block."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized")

    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
