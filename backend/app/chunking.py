"""
Shared word-based chunker - used both by seed_unstructured.py (bulk
authoring) and the live /upload endpoint (one document at a time), so
there's exactly one chunking implementation to keep consistent rather
than two copies that could quietly drift apart.
"""

CHUNK_SIZE = 120  # words
CHUNK_OVERLAP = 20


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks
