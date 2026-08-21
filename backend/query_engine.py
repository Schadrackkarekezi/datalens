"""
The single place that actually executes SQL against the database.

Both the manual query box (/query) and the AI agent (/ask) call run_select()
— the AI never gets a shortcut around the safety guard just because it
generated the SQL itself instead of a human typing it.

The safety guard is SQLite's own authorizer hook (conn.set_authorizer),
not a string prefix check. A `.startswith("select")` check is easy to get
wrong in ways that matter: it rejects legitimate `WITH ... SELECT` CTEs
(no "select" prefix), and more importantly it can't actually stop a write
hidden behind a CTE — SQLite allows `WITH x AS (...) DELETE FROM ...`,
which still starts with neither "select" nor anything a prefix check would
catch. The authorizer runs during query *compilation* and sees every
action the engine is about to take (read a column, call a function, write
a table, attach a database, ...) — we allow-list only the actions a
read-only query needs and deny everything else, so the enforcement can't
be bypassed by clever SQL phrasing.

Two more guards live here: a hard row cap (so `SELECT * FROM deals CROSS
JOIN deals CROSS JOIN deals` can't return millions of rows) and a
wall-clock query timeout (so a pathological query can't hang the process).
Both matter more once an LLM is the one writing the SQL — it won't
intentionally write a bad query, but it also has no sense of how
expensive one might be.
"""

import os
import sqlite3
import time

from database import get_connection

MAX_ROWS = int(os.environ.get("QUERY_MAX_ROWS", "500"))
TIMEOUT_SECONDS = float(os.environ.get("QUERY_TIMEOUT_SECONDS", "5"))

_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}


def _read_only_authorizer(action, arg1, arg2, db_name, trigger_name):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


class QueryError(Exception):
    pass


def run_select(sql: str):
    stripped = sql.strip().rstrip(";")
    if not stripped:
        raise QueryError("Empty query")

    # Wrap in a subquery with LIMIT so we cap rows regardless of what the
    # inner query does — and asking for one extra row tells us whether the
    # result was actually truncated.
    capped_sql = f"SELECT * FROM (\n{stripped}\n) LIMIT {MAX_ROWS + 1}"

    with get_connection() as conn:
        conn.set_authorizer(_read_only_authorizer)

        deadline = time.perf_counter() + TIMEOUT_SECONDS

        def _abort_if_over_deadline():
            return 1 if time.perf_counter() > deadline else 0

        conn.set_progress_handler(_abort_if_over_deadline, 1000)

        cur = conn.cursor()
        try:
            start = time.perf_counter()
            cur.execute(capped_sql)
            rows = cur.fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000
        except sqlite3.OperationalError as e:
            if "interrupted" in str(e).lower():
                raise QueryError(f"Query exceeded the {TIMEOUT_SECONDS}s timeout")
            raise QueryError(str(e))
        except sqlite3.DatabaseError as e:
            if "not authorized" in str(e).lower():
                raise QueryError("Only read-only SELECT queries are allowed")
            raise QueryError(str(e))
        except sqlite3.Error as e:
            raise QueryError(str(e))
        finally:
            conn.set_progress_handler(None, 0)
            conn.set_authorizer(None)

        columns = [desc[0] for desc in cur.description] if cur.description else []

    truncated = len(rows) > MAX_ROWS
    if truncated:
        rows = rows[:MAX_ROWS]

    return columns, [list(row) for row in rows], round(elapsed_ms, 2), truncated
