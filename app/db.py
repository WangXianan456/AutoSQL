from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    if not settings.database_url:
        raise RuntimeError("AUTOSQL_DATABASE_URL is not configured.")
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
