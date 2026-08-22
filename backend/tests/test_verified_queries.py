"""
Verified-query matching is a real correctness risk, not just a cache: a
false-positive match silently serves the wrong SQL for a question that
only sounds similar. These tests pin the threshold behavior down so a
future change to MATCH_THRESHOLD or the embedding model can't quietly
break it.
"""

import verified_queries


def test_exact_match_hits():
    result = verified_queries.find_verified_match("What is our win rate?")
    assert result is not None
    assert "win_rate" in result["sql"].lower() or "closed_won" in result["sql"].lower()


def test_paraphrase_hits():
    result = verified_queries.find_verified_match("Can you tell me our win rate")
    assert result is not None


def test_unrelated_question_misses():
    result = verified_queries.find_verified_match("What's the weather like today?")
    assert result is None


def test_adjacent_but_different_question_does_not_false_positive():
    # Scoped to one department — a real, different query from the generic
    # "win rate" verified entry. Must NOT match just because it's topically close.
    result = verified_queries.find_verified_match("What is the win rate for just the Sales department?")
    assert result is None
