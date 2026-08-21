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


def fetch_foreign_keys(conn):
    """
    Every FK edge in the schema, as (from_table, from_column, to_table, to_column).

    This is what the knowledge graph in knowledge_graph.py is built from — the
    graph's structure is the schema's actual foreign keys, not a hand-maintained
    diagram that can drift from reality.
    """
    cur = conn.cursor()
    table_names = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]

    edges = []
    for table in table_names:
        for row in cur.execute(f"PRAGMA foreign_key_list({table})").fetchall():
            # PRAGMA foreign_key_list columns: id, seq, table, from, to, on_update, on_delete, match
            edges.append({
                "from_table": table,
                "from_column": row[3],
                "to_table": row[2],
                "to_column": row[4],
            })

    return edges
