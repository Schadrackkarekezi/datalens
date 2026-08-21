"""
Tests run against a throwaway SQLite file, not the real datalens.db —
so a test asserting a write gets blocked doesn't also risk being the thing
that corrupts real seed data if the assertion is ever wrong.
"""

import sqlite3

import pytest

import database


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT, price INTEGER);
        INSERT INTO widgets (id, name, price) VALUES (1, 'gadget', 100);
        INSERT INTO widgets (id, name, price) VALUES (2, 'gizmo', 250);
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    return db_path
