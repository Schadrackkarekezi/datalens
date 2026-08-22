"""
Verified query repository — a small set of question -> SQL pairs that have
already passed both the deterministic checks and the LLM judge in the eval
suite (see verified_queries.json's "verified_via" field, and eval_set.json).
"Verified" means "passed the eval suite," not "someone eyeballed it once."

On /ask, if the incoming question closely matches one of these, the agent
skips LLM generation entirely and runs the pre-verified SQL directly —
still through the exact same query_engine.run_select() safety guard as
every other query, just skipping the (cost- and latency-incurring)
generation step. This is a real optimization, not just a trust badge: a
verified match costs $0 and runs in milliseconds instead of a few cents
and a couple of seconds.

Threshold calibration matters more here than in rag.py's glossary search,
because a false-positive match means silently serving the WRONG cached
answer instead of just missing a retrieval. Empirically (see git history
for the calibration script): true paraphrases of the same question score
0.92-1.0 cosine similarity; a *related but meaningfully different*
question — "what is our win rate" vs "what is our win rate BY
DEPARTMENT" — still scores 0.80, since embedding models cluster on
topic, not exact scope. MATCH_THRESHOLD is set well above that gap.
"""

import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

VERIFIED_QUERIES_PATH = "verified_queries.json"
MODEL_NAME = "all-MiniLM-L6-v2"
MATCH_THRESHOLD = 0.92

_model = None
_index = None
_entries = None


def _load():
    global _model, _index, _entries

    with open(VERIFIED_QUERIES_PATH) as f:
        _entries = json.load(f)

    _model = SentenceTransformer(MODEL_NAME)

    embeddings = _model.encode([e["question"] for e in _entries], convert_to_numpy=True)
    faiss.normalize_L2(embeddings)

    _index = faiss.IndexFlatIP(embeddings.shape[1])
    _index.add(embeddings)


def find_verified_match(question: str):
    if _model is None:
        _load()

    if len(_entries) == 0:
        return None

    query_vec = _model.encode([question], convert_to_numpy=True)
    faiss.normalize_L2(query_vec)

    scores, indices = _index.search(query_vec, 1)
    score, idx = float(scores[0][0]), int(indices[0][0])

    if idx == -1 or score < MATCH_THRESHOLD:
        return None

    entry = _entries[idx]
    return {"question": entry["question"], "sql": entry["sql"], "score": score}
