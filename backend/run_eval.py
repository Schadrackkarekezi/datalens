"""
Evaluation harness for the /ask agent.

Calls agent.run_ask() directly (no HTTP hop) for every question in
eval_set.json, checks the result against expectations, and prints an
accuracy report. For "ambiguous" questions (no matching data in the
schema), a *pass* means the agent failed gracefully — raised AgentError —
rather than hallucinating an answer to a question the data can't support.

Usage: python run_eval.py
"""

import json
import time

from agent import run_ask, AgentError

EVAL_SET_PATH = "eval_set.json"
RESULTS_PATH = "eval_results.json"


def check_normal(case: dict, result: dict) -> tuple[bool, str]:
    sql_lower = result["generated_sql"].lower()

    pattern = case.get("expected_sql_pattern")
    if pattern and pattern.lower() not in sql_lower:
        return False, f"expected SQL to contain '{pattern}', got: {result['generated_sql']}"

    expected_rows = case.get("expected_row_count")
    if expected_rows is not None and result["row_count"] != expected_rows:
        return False, f"expected {expected_rows} row(s), got {result['row_count']}"

    return True, "ok"


def run_case(case: dict) -> dict:
    start = time.perf_counter()
    try:
        result = run_ask(case["question"])
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if case.get("expect_failure"):
            return {
                "question": case["question"],
                "category": case["category"],
                "passed": False,
                "reason": f"expected graceful failure, agent answered with: {result['generated_sql']}",
                "latency_ms": latency_ms,
                "attempts": result["attempts"],
            }

        passed, reason = check_normal(case, result)
        return {
            "question": case["question"],
            "category": case["category"],
            "passed": passed,
            "reason": reason,
            "generated_sql": result["generated_sql"],
            "row_count": result["row_count"],
            "attempts": result["attempts"],
            "latency_ms": latency_ms,
        }

    except AgentError as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        passed = bool(case.get("expect_failure"))
        return {
            "question": case["question"],
            "category": case["category"],
            "passed": passed,
            "reason": "failed gracefully as expected" if passed else f"agent error: {e}",
            "latency_ms": latency_ms,
        }


def main():
    with open(EVAL_SET_PATH) as f:
        eval_set = json.load(f)

    results = [run_case(case) for case in eval_set]

    total = len(results)
    passed = sum(r["passed"] for r in results)
    accuracy = round(100 * passed / total, 1)
    avg_latency = round(sum(r["latency_ms"] for r in results) / total, 1)

    print(f"\n{'=' * 60}")
    print(f"DataLens Agent Eval — {passed}/{total} passed ({accuracy}%)")
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

    with open(RESULTS_PATH, "w") as f:
        json.dump(
            {"accuracy": accuracy, "passed": passed, "total": total, "avg_latency_ms": avg_latency, "results": results},
            f,
            indent=2,
        )

    print(f"Full results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
