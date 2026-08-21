"""
The agent behind POST /ask.

This is a multi-step pipeline, not a single LLM call:

  retrieve (RAG) -> graph lookup -> respond, where "respond" is one of two
  modes the model itself chooses per turn:

    - "sql":  the question asks for data. Generate a query, execute it,
              and on failure retry with the error fed back to the model
              (up to MAX_ATTEMPTS).
    - "chat": anything else — a greeting, a meta-question about a previous
              answer ("are you sure?", "why did you write it that way?"),
              a clarifying question the model needs to ask back, or an
              honest explanation of why this schema can't answer something.
              No SQL, no execution — just a reply.

Mixing these into one Pydantic response type (rather than always forcing
SQL) is what makes "can't answer this" a normal conversational turn
instead of an error: previously every non-SQL response was an exception
that surfaced in the UI as a red failure banner, which was wrong — the
agent hadn't failed, it had correctly declined to invent a query.
AgentError is now reserved for genuine failures: SQL that keeps erroring
out after every retry.

Each step is timed and recorded in `trace`, so the same data that answers
the question also documents exactly what the agent did to get there —
this trace is what Week 4's observability layer logs and displays.
"""

import os
import time
from typing import Literal, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from costs import estimate_cost_usd
from database import get_connection, fetch_schema
from knowledge_graph import find_relevant_entities, find_join_paths
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


class AgentResponse(BaseModel):
    response_type: Literal["sql", "chat"]
    message: Optional[str] = None  # chat mode: the reply text
    sql: Optional[str] = None  # sql mode: the query


class AgentError(Exception):
    def __init__(self, message, prompt_tokens=0, completion_tokens=0):
        super().__init__(message)
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


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


def _format_history(history) -> str:
    if not history:
        return ""
    turns = []
    for turn in history:
        if turn["type"] == "sql":
            turns.append(
                f"Q: {turn['question']}\nSQL: {turn['sql']}\n"
                f"(returned {turn['row_count']} row(s); columns: {', '.join(turn['columns'])})"
            )
        else:
            turns.append(f"Q: {turn['question']}\nA: {turn['message']}")
    return (
        "\n\nPrevious turns in this conversation — use these to resolve follow-ups "
        "(\"that\", \"those\", \"now filter by...\") and to answer meta-questions about "
        "what you just said (\"are you sure?\", \"why?\", \"what does that mean?\"):\n\n"
        + "\n\n".join(turns)
    )


def _generate(system_prompt: str, messages: list):
    response = _get_client().chat.completions.parse(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        response_format=AgentResponse,
    )
    parsed = response.choices[0].message.parsed
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }
    return parsed, usage


def run_ask(question: str, history: list = None):
    trace = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    t0 = time.perf_counter()
    context = retrieve(question, top_k=3)
    trace.append({
        "step": "retrieve",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "retrieved_terms": [c["term"] for c in context],
        "history_turns_used": len(history) if history else 0,
    })

    t_graph = time.perf_counter()
    relevant_entities = find_relevant_entities(question)
    join_paths = find_join_paths(relevant_entities)
    trace.append({
        "step": "graph_lookup",
        "latency_ms": round((time.perf_counter() - t_graph) * 1000, 2),
        "relevant_entities": relevant_entities,
        "join_paths": join_paths,
    })

    with get_connection() as conn:
        tables = fetch_schema(conn)

    join_hint = ""
    if join_paths:
        join_hint = "\n\nRelevant table relationships (use these exact join paths):\n" + "\n".join(
            f"- {p}" for p in join_paths
        )

    system_prompt = f"""You are a friendly, sharp data analyst assistant for a business database.
You have two response modes, chosen per turn:

- "sql": the question genuinely asks for data or analysis this schema can
  answer. Set response_type to "sql" and write a single SQLite SELECT query
  in sql — no markdown fences, no explanation, leave message empty.
- "chat": everything else — greetings, small talk, meta-questions about a
  previous answer ("are you sure?", "why did you write it that way?",
  "what does that mean?"), a clarifying question you need to ask back
  because the request is ambiguous, or an honest explanation when this
  schema genuinely has no data for what's being asked (forecasts,
  satisfaction scores, churn, external data, etc). Set response_type to
  "chat" and write a natural, concise, warm reply in message — leave sql
  empty. When explaining a previous SQL query or declining a question, be
  specific about why, using the schema and conversation history below.

Never guess or approximate a data answer with unrelated columns just to
have something in sql — an honest chat reply is correct; a plausible-
looking wrong query is not.

Schema:
{_format_schema(tables)}

Relevant business term definitions:
{_format_glossary(context)}
{join_hint}
{_format_history(history)}"""

    messages = [{"role": "user", "content": question}]
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        t1 = time.perf_counter()
        parsed, usage = _generate(system_prompt, messages)
        gen_latency = round((time.perf_counter() - t1) * 1000, 2)
        total_prompt_tokens += usage["prompt_tokens"]
        total_completion_tokens += usage["completion_tokens"]

        if parsed.response_type == "chat":
            trace.append({
                "step": "respond",
                "attempt": attempt,
                "generate_latency_ms": gen_latency,
                "tokens": usage,
                "status": "chat",
            })
            estimated_cost = estimate_cost_usd(MODEL, total_prompt_tokens, total_completion_tokens)
            return {
                "response_type": "chat",
                "question": question,
                "message": parsed.message,
                "generated_sql": None,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
                "attempts": attempt,
                "retrieved_context": context,
                "trace": trace,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "estimated_cost_usd": estimated_cost,
            }

        sql = parsed.sql.strip()
        messages.append({"role": "assistant", "content": sql})

        try:
            columns, rows, exec_latency, truncated = run_select(sql)
        except QueryError as e:
            last_error = str(e)
            trace.append({
                "step": "respond",
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
            "step": "respond",
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
            "response_type": "sql",
            "question": question,
            "message": None,
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

    raise AgentError(
        f"Agent failed after {MAX_ATTEMPTS} attempts. Last error: {last_error}",
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
    )
