"""
SQLite connection manager with context manager support.
"""
import sqlite3
from contextlib import contextmanager
import config


@contextmanager
def get_connection():
    """Yield a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(query, params=(), fetchone=False, fetchall=False):
    """Execute a query and optionally fetch results."""
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        return cursor.lastrowid
