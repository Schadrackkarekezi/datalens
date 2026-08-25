"""
Handles POST /upload - adds a new account note or piece of enablement
content, chunks it with the same chunker seed_unstructured.py uses, and
embeds the new chunks immediately (embedding.py) so they're retrievable
right away instead of waiting for a batch job to notice them.

account_id is the actual isolation boundary retrieval.py enforces, and
this is where that boundary either holds or doesn't at ingestion time:
an account note always carries a real account_id, resolved from a
validated foreign key (_require_account below raises if the account
doesn't exist - never silently proceeds with a bad or missing one), and
enablement content never carries an account_id at all. There's no
in-between state where a chunk could end up ambiguously scoped.
"""

from datetime import date

from app.chunking import chunk_text
from app.database import get_connection, DATABASE_URL
from app.embedding import embed_pending_chunks

import psycopg


class UploadError(Exception):
    pass


def _require_account(conn, account_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM accounts WHERE account_id = %s", (account_id,))
        if cur.fetchone() is None:
            raise UploadError(f"No account with account_id={account_id} - check the ID and try again.")


def _insert_chunks(cur, source_type: str, source_id: int, account_id, content: str) -> int:
    chunks = chunk_text(content)
    rows = [(source_type, source_id, account_id, i, c) for i, c in enumerate(chunks)]
    cur.executemany(
        """INSERT INTO document_chunks (source_type, source_id, account_id, chunk_index, chunk_text)
           VALUES (%s, %s, %s, %s, %s)""",
        rows,
    )
    return len(chunks)


def upload_account_note(account_id: int, content: str, author_role: str) -> dict:
    if not content.strip():
        raise UploadError("Note content can't be empty.")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                _require_account(conn, account_id)
                cur.execute(
                    """INSERT INTO account_notes (account_id, author_role, note_date, content)
                       VALUES (%s, %s, %s, %s) RETURNING note_id""",
                    (account_id, author_role, date.today(), content.strip()),
                )
                note_id = cur.fetchone()[0]
                chunks_created = _insert_chunks(cur, "account_note", note_id, account_id, content.strip())
            conn.commit()
    except psycopg.Error as e:
        raise UploadError(str(e).strip()) from e

    chunks_embedded = embed_pending_chunks(DATABASE_URL)
    return {"id": note_id, "chunks_created": chunks_created, "chunks_embedded": chunks_embedded}


def upload_enablement_content(title: str, category: str, content: str) -> dict:
    if not content.strip():
        raise UploadError("Content can't be empty.")
    if not title.strip():
        raise UploadError("Title can't be empty.")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO enablement_content (title, category, content)
                       VALUES (%s, %s, %s) RETURNING content_id""",
                    (title.strip(), category, content.strip()),
                )
                content_id = cur.fetchone()[0]
                chunks_created = _insert_chunks(cur, "enablement_content", content_id, None, content.strip())
            conn.commit()
    except psycopg.Error as e:
        raise UploadError(str(e).strip()) from e

    chunks_embedded = embed_pending_chunks(DATABASE_URL)
    return {"id": content_id, "chunks_created": chunks_created, "chunks_embedded": chunks_embedded}
