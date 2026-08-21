"""
Retrieval over the business glossary.

We embed each glossary entry once at startup with a small local sentence-
transformer model (no API calls, no cost) and store the vectors in a FAISS
index. At query time we embed the incoming question the same way and pull
back the top-k nearest glossary entries by cosine similarity, so the LLM
gets business-specific definitions (e.g. "win rate") instead of guessing.
"""

import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

GLOSSARY_PATH = "glossary.json"
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_index = None
_entries = None


def _load():
    global _model, _index, _entries

    with open(GLOSSARY_PATH) as f:
        _entries = json.load(f)

    _model = SentenceTransformer(MODEL_NAME)

    texts = [f"{e['term']}: {e['definition']}" for e in _entries]
    embeddings = _model.encode(texts, convert_to_numpy=True)
    faiss.normalize_L2(embeddings)

    _index = faiss.IndexFlatIP(embeddings.shape[1])
    _index.add(embeddings)


def retrieve(question: str, top_k: int = 3):
    if _model is None:
        _load()

    query_vec = _model.encode([question], convert_to_numpy=True)
    faiss.normalize_L2(query_vec)

    scores, indices = _index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        entry = _entries[idx]
        results.append({"term": entry["term"], "definition": entry["definition"], "score": float(score)})

    return results
