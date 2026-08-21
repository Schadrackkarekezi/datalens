"""
Evaluation harness for the /ask agent.

Two suites, run together:

  1. Single-turn (eval_set.json) — one question each, checked three ways:
     deterministic pattern/row-count checks (fast, free, catch obviously
     wrong SQL) AND an LLM-as-judge semantic check (judge.py — catches SQL
     that looks plausible but answers the wrong question). For "ambiguous"
     questions, a pass means the agent replied in chat mode instead of
     hallucinating a query the data can't support.

  2. Multi-turn (eval_conversations.json) — sequences of questions run
     through run_ask() with accumulating history, exactly like a real
     conversation. This is what regression-tests follow-up resolution
     ("now break that down by department") instead of relying on a single
     manual spot-check.

AgentError (retries exhausted on genuinely broken SQL) always counts as a
failure — that's a real bug, not a valid outcome for any eval case.

Usage: python run_eval.py
"""

import json
import time

from agent import run_ask, AgentError
from judge import judge_sql_answer

EVAL_SET_PATH = "eval_set.json"
EVAL_CONVERSATIONS_PATH = "eval_conversations.json"
RESULTS_PATH = "eval_results.json"


def _history_turn(question: str, result: dict) -> dict:
    if result["response_type"] == "sql":
        return {
            "type": "sql",
            "question": question,
            "sql": result["generated_sql"],
            "row_count": result["row_count"],
            "columns": result["columns"],
        }
    return {"type": "chat", "question": question, "message": result["message"]}


def check_sql_case(case: dict, result: dict, history: list = None) -> tuple[bool, str]:
    if result["response_type"] != "sql":
        return False, f"expected a SQL answer, agent replied in chat mode: {result['message']}"

    sql_lower = result["generated_sql"].lower()

    pattern = case.get("expected_sql_pattern")
    if pattern and pattern.lower() not in sql_lower:
        return False, f"expected SQL to contain '{pattern}', got: {result['generated_sql']}"

    expected_rows = case.get("expected_row_count")
    if expected_rows is not None and result["row_count"] != expected_rows:
        return False, f"expected {expected_rows} row(s), got {result['row_count']}"

    verdict = judge_sql_answer(
        case["question"],
        result["generated_sql"],
        result["columns"],
        result["rows"],
        glossary_context=result["retrieved_context"],
        history=history,
    )
    if not verdict.correct:
        return False, f"judge flagged as semantically wrong: {verdict.reasoning}"

    return True, f"ok — judge: {verdict.reasoning}"


def run_case(case: dict) -> dict:
    start = time.perf_counter()
    try:
        result = run_ask(case["question"])
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if case.get("expect_failure"):
            passed = result["response_type"] == "chat"
            return {
                "question": case["question"],
                "category": case["category"],
                "passed": passed,
                "reason": "declined gracefully as expected" if passed
                else f"expected a chat decline, agent answered with: {result['generated_sql']}",
                "latency_ms": latency_ms,
                "attempts": result["attempts"],
            }

        passed, reason = check_sql_case(case, result)
        return {
            "question": case["question"],
            "category": case["category"],
            "passed": passed,
            "reason": reason,
            "generated_sql": result.get("generated_sql"),
            "row_count": result["row_count"],
            "attempts": result["attempts"],
            "latency_ms": latency_ms,
        }

    except AgentError as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "question": case["question"],
            "category": case["category"],
            "passed": False,
            "reason": f"agent error: {e}",
            "latency_ms": latency_ms,
        }


def run_conversation_case(scenario: dict) -> dict:
    history = []
    turn_results = []
    all_passed = True

    for turn in scenario["turns"]:
        start = time.perf_counter()
        try:
            result = run_ask(turn["question"], history=history)
        except AgentError as e:
            all_passed = False
            turn_results.append({"question": turn["question"], "passed": False, "reason": f"agent error: {e}"})
            break

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        history_before_this_turn = list(history)  # same context the agent itself saw
        history.append(_history_turn(turn["question"], result))

        if turn.get("expect_chat"):
            passed = result["response_type"] == "chat"
            reason = "ok" if passed else f"expected a chat reply, got SQL: {result.get('generated_sql')}"
        else:
            passed, reason = check_sql_case(turn, result, history=history_before_this_turn)

        if not passed:
            all_passed = False
        turn_results.append({
            "question": turn["question"],
            "passed": passed,
            "reason": reason,
            "latency_ms": latency_ms,
        })

    return {"name": scenario["name"], "passed": all_passed, "turns": turn_results}


def main():
    with open(EVAL_SET_PATH) as f:
        eval_set = json.load(f)
    with open(EVAL_CONVERSATIONS_PATH) as f:
        conversations = json.load(f)

    results = [run_case(case) for case in eval_set]
    conversation_results = [run_conversation_case(scenario) for scenario in conversations]

    total = len(results)
    passed = sum(r["passed"] for r in results)
    accuracy = round(100 * passed / total, 1)
    avg_latency = round(sum(r["latency_ms"] for r in results) / total, 1)

    convo_total = len(conversation_results)
    convo_passed = sum(c["passed"] for c in conversation_results)

    print(f"\n{'=' * 60}")
    print(f"DataLens Agent Eval — {passed}/{total} single-turn passed ({accuracy}%)")
    print(f"Conversations — {convo_passed}/{convo_total} passed")
    print(f"Average latency: {avg_latency} ms")
    print(f"{'=' * 60}\n")

    by_category = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    for category, cases in by_category.items():
        cat_passed = sum(c["passed"] for c in cases)
        print(f"[{category}] {cat_passed}/{len(cases)}")
        for c in cases:
            mark = "✅" if c["passed"] else "❌"
            print(f"  {mark} {c['question']}")
            if not c["passed"]:
                print(f"      -> {c['reason']}")
        print()

    print("[conversations]")
    for c in conversation_results:
        mark = "✅" if c["passed"] else "❌"
        print(f"  {mark} {c['name']}")
        for t in c["turns"]:
            tmark = "✅" if t["passed"] else "❌"
            print(f"      {tmark} {t['question']}")
            if not t["passed"]:
                print(f"          -> {t['reason']}")
    print()

    with open(RESULTS_PATH, "w") as f:
        json.dump(
            {
                "accuracy": accuracy,
                "passed": passed,
                "total": total,
                "avg_latency_ms": avg_latency,
                "conversations_passed": convo_passed,
                "conversations_total": convo_total,
                "results": results,
                "conversation_results": conversation_results,
            },
            f,
            indent=2,
        )

    print(f"Full results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
