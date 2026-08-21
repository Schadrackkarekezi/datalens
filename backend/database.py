"""
SQLite connection helper.

sqlite3 connections aren't safe to share across threads by default, and
FastAPI can serve requests on different threads — so instead of one global
connection, we open a fresh one per request and close it when done.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "datalens.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def fetch_schema(conn):
    """Introspect the DB via sqlite_master/PRAGMA — shared by /schema and the agent's prompt building."""
    cur = conn.cursor()
    table_names = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]

    tables = []
    for name in table_names:
        columns = [
            {"name": col[1], "type": col[2]}
            for col in cur.execute(f"PRAGMA table_info({name})").fetchall()
        ]
        tables.append({"name": name, "columns": columns})

    return tables
