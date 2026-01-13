from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from app.config import DATABASE_URL

_POOL = None

POOL_MIN = 1
POOL_MAX = 10

def init_pool():
    global _POOL
    if _POOL is None:
        _POOL = SimpleConnectionPool(
            POOL_MIN,
            POOL_MAX,
            dsn=DATABASE_URL
        )

def get_connection():
    if _POOL is None:
        init_pool()
    return _POOL.getconn()

def put_connection(conn):
    _POOL.putconn(conn)

@contextmanager
def get_db_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_connection(conn)

def close_all():
    global _POOL
    if _POOL:
        _POOL.closeall()
        _POOL = None
