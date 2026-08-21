"""
In-memory, per-session conversation history — what makes /ask support
follow-up questions ("now break that down by department") instead of every
question starting from zero.

In-memory and per-process, like rate_limit.py — fine for a single-instance
demo. A multi-instance production deployment would move this to
Redis/a database so history survives restarts and is shared across
processes.
"""

import time
import uuid
from collections import defaultdict

MAX_TURNS = 6  # how many prior turns get fed back into the prompt

_sessions = defaultdict(list)
_last_active = {}


def resolve_conversation_id(conversation_id):
    return conversation_id if conversation_id else str(uuid.uuid4())


def get_history(conversation_id: str) -> list:
    return _sessions[conversation_id][-MAX_TURNS:]


def add_turn(conversation_id: str, question: str, result: dict):
    if result["response_type"] == "sql":
        turn = {
            "type": "sql",
            "question": question,
            "sql": result["generated_sql"],
            "row_count": result["row_count"],
            "columns": result["columns"],
        }
    else:
        turn = {
            "type": "chat",
            "question": question,
            "message": result["message"],
        }
    _sessions[conversation_id].append(turn)
    _last_active[conversation_id] = time.time()


def clear_conversation(conversation_id: str):
    _sessions.pop(conversation_id, None)
    _last_active.pop(conversation_id, None)
