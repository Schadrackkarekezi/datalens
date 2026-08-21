"""
LLM-as-judge: scores whether generated SQL actually answers the question,
not just whether it looks plausible.

Pattern/row-count checks in run_eval.py catch obviously wrong SQL, but
they're a weak proxy — a query can contain the right keyword and return
the right number of rows while still answering the wrong question (wrong
join direction, a missing filter, inverted logic). The judge is a second,
independent model call that sees the question, the SQL, and the actual
result, and verifies the semantics — the same technique used to eval LLM
outputs across the industry, not something bespoke to this project.

Runs on a separate, cheaper model by default (OPENAI_JUDGE_MODEL) — the
judge's job is narrow (verify one query against one question), so it
doesn't need the same model tier as generation. Using a cheaper model for
verification instead of defaulting everything to the expensive one is a
deliberate cost decision, not an oversight.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

JUDGE_MODEL = os.environ.get("OPENAI_JUDGE_MODEL", "gpt-4o-mini")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


class JudgeVerdict(BaseModel):
    correct: bool
    reasoning: str


def judge_sql_answer(
    question: str,
    sql: str,
    columns: list,
    rows: list,
    glossary_context: list = None,
    history: list = None,
) -> JudgeVerdict:
    """
    glossary_context and history must be the SAME grounding the agent had
    when it wrote the SQL (agent.run_ask()'s retrieved_context and the
    conversation history passed in) — a judge given less context than the
    generator will flag context-dependent correct answers as wrong. This
    isn't a hypothetical: without glossary_context, this judge failed
    "active deals" (correctly filtered to prospecting/negotiation per the
    project's own glossary) because it didn't know that definition existed.
    """
    preview_rows = rows[:5]

    glossary_text = "(none retrieved)"
    if glossary_context:
        glossary_text = "\n".join(f"- {c['term']}: {c['definition']}" for c in glossary_context)

    history_text = "(none — this is the first turn)"
    if history:
        parts = []
        for turn in history:
            if turn["type"] == "sql":
                parts.append(f"Q: {turn['question']}\nSQL: {turn['sql']}")
            else:
                parts.append(f"Q: {turn['question']}\nA: {turn['message']}")
        history_text = "\n\n".join(parts)

    prompt = f"""Question: {question}

Business term definitions the agent had access to (use these to judge
whether it correctly applied project-specific meanings, e.g. "active deal"
has a specific definition here, not a generic one):
{glossary_text}

Prior conversation turns the agent had access to (relevant if the question
uses "that", "those", or otherwise refers back to a previous turn):
{history_text}

SQL query the agent wrote:
{sql}

Result columns: {columns}
Result rows (first 5): {preview_rows}

Does this SQL query correctly answer the question, given the definitions
and conversation context above? A query can look plausible and still be
wrong (e.g. counting all deals when the question asked only about closed
ones, or joining the wrong foreign key) — but it can also look
"incomplete" to someone without this context while actually being exactly
right (e.g. filtering to specific stages because that's this project's
definition of "active"). Judge using the context given, not generic
assumptions about what these terms usually mean elsewhere. Set correct to
true only if you're confident the logic is right; briefly explain your
reasoning."""

    response = _get_client().chat.completions.parse(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format=JudgeVerdict,
    )
    return response.choices[0].message.parsed
