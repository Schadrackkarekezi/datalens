"""
Conversation history - what makes /ask support follow-up questions
("now break that down by department") instead of every question starting
from zero. Stored in Postgres (conversation_turns), not per-process
memory: the earlier in-memory dict was fine for a single-instance demo,
but meant a server restart silently forgot every conversation in
progress. This version survives a restart and would be shared correctly
across multiple backend instances too, since every instance reads the
same table instead of its own private memory - the fix that made the
old in-memory limitation a documented tradeoff was moving the storage,
not adding a cache in front of it.
"""

import uuid

from psycopg.types.json import Jsonb

from app.database import get_connection

MAX_TURNS = 6  # how many prior turns get fed back into the prompt


def resolve_conversation_id(conversation_id):
    return conversation_id if conversation_id else str(uuid.uuid4())


def get_history(conversation_id: str) -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT turn FROM conversation_turns
                   WHERE conversation_id = %s
                   ORDER BY turn_id DESC
                   LIMIT %s""",
                (conversation_id, MAX_TURNS),
            )
            rows = cur.fetchall()
    return [row[0] for row in reversed(rows)]


def add_turn(conversation_id: str, question: str, result: dict):
    response_type = result["response_type"]

    if response_type == "sql":
        turn = {
            "type": "sql",
            "question": question,
            "sql": result["generated_sql"],
            "row_count": result["row_count"],
            "columns": result["columns"],
        }
    elif response_type == "hybrid":
        # Keeps both halves - a follow-up like "now break that down by
        # workload" needs the SQL shape to resolve "that" correctly, but
        # collapsing to a chat-shaped turn (question + message only, the
        # non-sql branch below) would lose it and only remember the prose.
        turn = {
            "type": "hybrid",
            "question": question,
            "sql": result["generated_sql"],
            "row_count": result["row_count"],
            "columns": result["columns"],
            "message": result["message"],
        }
    else:
        turn = {
            "type": "chat",
            "question": question,
            "message": result["message"],
        }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversation_turns (conversation_id, turn) VALUES (%s, %s)",
                (conversation_id, Jsonb(turn)),
            )
        conn.commit()


def clear_conversation(conversation_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversation_turns WHERE conversation_id = %s", (conversation_id,))
        conn.commit()
