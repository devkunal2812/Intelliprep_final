"""
Psycopg2 connection pool for direct Postgres queries.

Used mainly by the question-generation engine which needs efficient
random-sampling SQL that is awkward via the Supabase REST API.
"""

import os
import psycopg2
from psycopg2 import pool
from app.config import DATABASE_URL

_pool: pool.ThreadedConnectionPool | None = None


def _make_pool():
    """
    Try keyword-based connection first (avoids URL-encoding issues with
    special characters in passwords). Falls back to DSN string.
    """
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT", "5432")
    dbname   = os.getenv("DB_NAME")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if host and dbname and user and password:
        return pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=host,
            port=int(port),
            dbname=dbname,
            user=user,
            password=password,
            sslmode="require",
        )

    # Fallback: use DATABASE_URL DSN
    return pool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)


def init_pool():
    global _pool
    _pool = _make_pool()


def get_connection():
    if _pool is None:
        init_pool()
    return _pool.getconn()


def put_connection(conn):
    if _pool is not None:
        _pool.putconn(conn)
