"""
Tests run against the real local Postgres instance (docker-compose's db
service must be up), using a disposable `widgets` table created and
dropped per test - not a mock. This is what lets test_query_engine.py
exercise the actual datalens_readonly role's actual Postgres-enforced
privileges, not a simulation of them.
"""

import psycopg
import pytest

import app.database as database


@pytest.fixture
def test_db():
    with psycopg.connect(database.DATABASE_URL) as conn:
        conn.execute("DROP TABLE IF EXISTS widgets")
        conn.execute("CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
        conn.execute(
            "INSERT INTO widgets (id, name, price) VALUES (1, 'gadget', 100), (2, 'gizmo', 250)"
        )
        conn.commit()

    yield

    with psycopg.connect(database.DATABASE_URL) as conn:
        conn.execute("DROP TABLE IF EXISTS widgets")
        conn.commit()
