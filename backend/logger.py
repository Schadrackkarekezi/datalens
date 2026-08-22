"""
Append-only log of every /ask call, for the observability dashboard.

A JSONL file (one JSON object per line) instead of a SQLite table — a log
table would show up in /schema next to the real business tables, which
would be a confusing thing for a demo to explain.
"""

import json
import time
from pathlib import Path

LOG_PATH = Path("query_logs.jsonl")


def log_ask(
    question: str,
    total_latency_ms: float,
    success: bool,
    result: dict = None,
    error: str = None,
    estimated_cost_usd: float = None,
):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "question": question,
        "success": success,
        "total_latency_ms": round(total_latency_ms, 2),
        "response_type": result["response_type"] if result else None,
        "generated_sql": result["generated_sql"] if result else None,
        "verified": result.get("verified") if result else None,
        "attempts": result["attempts"] if result else None,
        "row_count": result["row_count"] if result else None,
        "retrieved_terms": [c["term"] for c in result["retrieved_context"]] if result else [],
        "estimated_cost_usd": result["estimated_cost_usd"] if result else estimated_cost_usd,
        "error": error,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def read_logs(limit: int = 50):
    if not LOG_PATH.exists():
        return []

    with LOG_PATH.open() as f:
        lines = f.readlines()

    entries = [json.loads(line) for line in lines[-limit:]]
    entries.reverse()
    return entries
