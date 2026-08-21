"""
The text-to-SQL agent behind POST /ask.

This is a multi-step pipeline, not a single LLM call:

  retrieve (RAG) -> generate SQL -> execute -> [on failure: retry with the
  error fed back to the model, up to MAX_ATTEMPTS] -> return

Each step is timed and recorded in `trace`, so the same data that answers
the question also documents exactly what the agent did to get there —
this trace is what Week 4's observability layer logs and displays.
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from costs import estimate_cost_usd
from database import get_connection, fetch_schema
from query_engine import run_select, QueryError
from rag import retrieve

load_dotenv()

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
MAX_ATTEMPTS = 3

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


class SQLGeneration(BaseModel):
    sql: str


class AgentError(Exception):
    pass


def _format_schema(tables) -> str:
    lines = []
    for t in tables:
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        lines.append(f"- {t['name']}: {cols}")
    return "\n".join(lines)


def _format_glossary(entries) -> str:
    if not entries:
        return "(no relevant business terms found)"
    return "\n".join(f"- {e['term']}: {e['definition']}" for e in entries)


def _generate_sql(system_prompt: str, messages: list):
    response = _get_client().chat.completions.parse(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        response_format=SQLGeneration,
    )
    sql = response.choices[0].message.parsed.sql.strip()
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }
    return sql, usage


def run_ask(question: str):
    trace = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    t0 = time.perf_counter()
    context = retrieve(question, top_k=3)
    trace.append({
        "step": "retrieve",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "retrieved_terms": [c["term"] for c in context],
    })

    with get_connection() as conn:
        tables = fetch_schema(conn)

    system_prompt = f"""You are a SQLite expert helping analyze a business database.

Schema:
{_format_schema(tables)}

Relevant business term definitions:
{_format_glossary(context)}

Write a single SQLite SELECT query that answers the user's question. Use the
business term definitions above when the question uses those terms. Return
only the SQL query — no markdown fences, no explanation."""

    messages = [{"role": "user", "content": question}]
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        t1 = time.perf_counter()
        sql, usage = _generate_sql(system_prompt, messages)
        gen_latency = round((time.perf_counter() - t1) * 1000, 2)
        total_prompt_tokens += usage["prompt_tokens"]
        total_completion_tokens += usage["completion_tokens"]
        messages.append({"role": "assistant", "content": sql})

        try:
            columns, rows, exec_latency, truncated = run_select(sql)
        except QueryError as e:
            last_error = str(e)
            trace.append({
                "step": "generate_and_execute",
                "attempt": attempt,
                "sql": sql,
                "generate_latency_ms": gen_latency,
                "tokens": usage,
                "status": "error",
                "error": last_error,
            })
            messages.append({
                "role": "user",
                "content": f"That query failed with error: {last_error}. Fix it and return only the corrected SQL.",
            })
            continue

        trace.append({
            "step": "generate_and_execute",
            "attempt": attempt,
            "sql": sql,
            "generate_latency_ms": gen_latency,
            "execute_latency_ms": exec_latency,
            "tokens": usage,
            "status": "success",
            "row_count": len(rows),
            "truncated": truncated,
        })

        estimated_cost = estimate_cost_usd(MODEL, total_prompt_tokens, total_completion_tokens)

        return {
            "question": question,
            "generated_sql": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "attempts": attempt,
            "retrieved_context": context,
            "trace": trace,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "estimated_cost_usd": estimated_cost,
        }

    raise AgentError(f"Agent failed after {MAX_ATTEMPTS} attempts. Last error: {last_error}")
