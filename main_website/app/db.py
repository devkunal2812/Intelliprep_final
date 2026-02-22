"""
Psycopg2 connection pool for direct Postgres queries.

Used mainly by the question-generation engine which needs efficient
random-sampling SQL that is awkward via the Supabase REST API.
"""

import psycopg2
from psycopg2 import pool
from app.config import DATABASE_URL

_pool: pool.ThreadedConnectionPool | None = None


def init_pool():
    global _pool
    _pool = pool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)


def get_connection():
    if _pool is None:
        init_pool()
    return _pool.getconn()


def put_connection(conn):
    if _pool is not None:
        _pool.putconn(conn)
