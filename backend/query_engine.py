"""
The single place that actually executes SQL against the database.

Both the manual query box (/query) and the AI agent (/ask) call run_select()
— the AI never gets a shortcut around the SELECT-only safety guard just
because it generated the SQL itself instead of a human typing it.
"""

import sqlite3
import time

from database import get_connection


class QueryError(Exception):
    pass


def run_select(sql: str):
    stripped = sql.strip()

    if not stripped.lower().startswith("select"):
        raise QueryError("Only SELECT queries are allowed")

    with get_connection() as conn:
        cur = conn.cursor()
        try:
            start = time.perf_counter()
            cur.execute(stripped)
            rows = cur.fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000
        except sqlite3.Error as e:
            raise QueryError(str(e))

        columns = [desc[0] for desc in cur.description] if cur.description else []

    return columns, [list(row) for row in rows], round(elapsed_ms, 2)
