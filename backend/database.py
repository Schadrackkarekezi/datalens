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
