# DataLens — Project Plan

A SQL query tool with an AI agent layer (RAG-backed), evaluation framework, and observability.

**Purpose:** Portfolio project demonstrating engineering depth — for founder outreach, AI Engineer / FDE / Data Scientist / Data Engineer roles.

**Stack:** React (frontend) + FastAPI (backend) + SQLite (data) + FAISS (vector DB) + OpenAI API (LLM, model configurable via `OPENAI_MODEL`, default `gpt-4o`) + Render/Railway + Vercel (deployment)

**Time budget:** ~1.5–2 hrs/day. **Rule: if a week runs behind, cut scope for that week — never push the final ship date.**

---

## Current status
✅ Week 1 complete: FastAPI backend (`/schema`, `/query` with SELECT-only safety guard) + React frontend (schema browser, CodeMirror query editor, sortable results, query history) — all tested end to end.

✅ Week 2 built (untested — needs an `OPENAI_API_KEY` to actually run): `POST /ask` is a multi-step pipeline, not a single LLM call — retrieve (FAISS + `glossary.json`) → generate SQL (structured output via `client.chat.completions.parse`) → execute through the *same* safety-checked `query_engine.run_select()` the manual query box uses → on failure, feed the SQLite error back to the model and retry (up to 3 attempts) → return, with a full step-by-step `trace`. `ChatPanel.jsx` is the frontend for it.

✅ Week 3 built (untested): `eval_set.json` (18 questions — simple/join/glossary/ambiguous categories, grounded against the actual seeded data) + `run_eval.py`, which calls `agent.run_ask()` directly and scores accuracy. Seed data is now deterministic (`random.seed(42)` in `seed_db.py`) so eval expectations don't drift on reseed.

✅ Week 4 built (untested): `logger.py` appends every `/ask` call to `query_logs.jsonl` (question, generated SQL, attempts, latency, success/failure) — a JSONL file rather than a SQLite table, so the log doesn't show up as a fake "table" in `/schema`. `GET /logs` + `Dashboard.jsx` render it as a stats row + latency bar chart + log table.

**Not yet done:** running the Week 2-4 eval/logging loop for real (blocked on an OpenAI API key), iterating on eval failures to get a before/after accuracy number, the real portfolio-facing README, and deployment (Day 28-30).

---

## WEEK 1 — SQL Tool Core

### Day 3-4: Backend API (FastAPI)
**File structure to create:**
```
backend/
  main.py          # FastAPI app entrypoint
  database.py      # SQLite connection helper
  models.py        # Pydantic request/response models
  seed_db.py       # (already done)
  requirements.txt
```

**`requirements.txt`:**
```
fastapi
uvicorn
pydantic
```

**Endpoints to build:**

1. `GET /schema`
   - Returns all tables with their columns and types
   - Response shape:
   ```json
   {
     "tables": [
       {
         "name": "deals",
         "columns": [
           {"name": "deal_id", "type": "INTEGER"},
           {"name": "customer_id", "type": "INTEGER"},
           ...
         ]
       }
     ]
   }
   ```
   - Implementation note: SQLite has a built-in `PRAGMA table_info(table_name)` command and `sqlite_master` table you can query to get this programmatically — don't hardcode it.

2. `POST /query`
   - Request body: `{"sql": "SELECT * FROM deals LIMIT 10"}`
   - **Safety: reject any query that isn't a SELECT** (block INSERT/UPDATE/DELETE/DROP) — check the query starts with `SELECT` (case-insensitive, trimmed) before executing. This matters for the "production thinking" story.
   - Response shape:
   ```json
   {
     "columns": ["deal_id", "company_name", "deal_value"],
     "rows": [[1, "Acme Corp", 346629], ...],
     "row_count": 10,
     "execution_time_ms": 4
   }
   ```
   - Wrap execution in try/except — return a clean 400 error with the SQLite error message on bad SQL, not a raw 500 crash.

**Test before moving on:** run `uvicorn main:app --reload`, hit both endpoints with curl or the FastAPI auto-docs at `/docs`, confirm real data comes back.

### Day 5-7: React Frontend
**File structure:**
```
frontend/
  src/
    App.jsx
    components/
      SchemaBrowser.jsx   # sidebar listing tables/columns
      QueryEditor.jsx      # textarea + Run button
      ResultsTable.jsx     # renders query results
    api.js                 # fetch wrappers for backend calls
```

**Build order:**
1. `api.js` — simple fetch functions: `getSchema()`, `runQuery(sql)`
2. `SchemaBrowser.jsx` — calls `/schema` on mount, renders table/column list in sidebar
3. `QueryEditor.jsx` — textarea for SQL input, Run button, calls `/query` on submit
4. `ResultsTable.jsx` — takes `columns` + `rows`, renders an HTML table
5. `App.jsx` — lays out SchemaBrowser (left) + QueryEditor/ResultsTable (right)

**Styling:** keep it simple — a clean two-column layout is enough. Don't over-invest in design polish this week; function first.

**✅ Week 1 checkpoint:** Open the app, see the schema, write `SELECT * FROM deals WHERE stage = 'closed_won' LIMIT 5`, see results in a table. This alone is a demo-able product.

---

## WEEK 2 — AI Agent + RAG

### Day 8-9: Basic agent endpoint
**New file:** `backend/agent.py`

**Endpoint:** `POST /ask`
- Request: `{"question": "What are the top 5 highest value deals?"}`
- **Built as an explicit multi-step pipeline, not one LLM call:** retrieve → generate SQL → execute → on failure, feed the SQLite error back to the model and retry (capped at 3 attempts) → return. Each step is timed and recorded in a `trace` list on the response — this is what makes it a genuine agentic workflow instead of a single API call, and it's also what Week 4's observability layer logs.
- The AI-generated SQL runs through `query_engine.run_select()` — the exact same SELECT-only-guarded function the manual query box uses. The agent gets no special privileges just because it wrote the SQL itself.
- Response shape:
  ```json
  {
    "question": "...",
    "generated_sql": "SELECT ...",
    "columns": [...],
    "rows": [...],
    "attempts": 1,
    "retrieved_context": [...],
    "trace": [...]
  }
  ```

### Day 10-11: Vector DB + business glossary
**New file:** `backend/rag.py`

**Build a small glossary** (`backend/glossary.json`) — 8-10 business term definitions relevant to your schema, e.g.:
```json
[
  {"term": "active deal", "definition": "A deal in 'prospecting' or 'negotiation' stage, not yet closed"},
  {"term": "win rate", "definition": "closed_won deals divided by total closed deals (closed_won + closed_lost)"},
  {"term": "top performer", "definition": "employee with highest total closed_won deal value"}
]
```

**Embed and store:**
- Use FAISS (simpler, no external account needed) to start — `pip install faiss-cpu sentence-transformers`
- Embed each glossary entry's `term + definition` using a sentence-transformer model (e.g., `all-MiniLM-L6-v2` — free, runs locally, no API cost)
- Store embeddings in a FAISS index, keep a parallel list mapping index position → glossary entry

### Day 12-14: Wire RAG into the agent
**Update `/ask` logic:**
1. Embed the incoming question
2. Search FAISS index for top 2-3 most relevant glossary entries
3. Include those definitions in the LLM prompt alongside the schema
4. Generate SQL, execute, return results — now the agent understands business-specific terms like "win rate" correctly

**Frontend addition:** `components/ChatPanel.jsx` — simple chat-style input, shows question → (retrieved context, collapsible) → generated SQL → results table

**✅ Week 2 checkpoint:** Ask "What's our win rate by department?" — agent retrieves the "win rate" definition, generates correct SQL joining deals/employees/departments, returns accurate results.

---

## WEEK 3 — Evaluation Framework

### Day 15-16: Build eval set
**New file:** `backend/eval_set.json` — 15-20 entries:
```json
[
  {
    "question": "How many deals are closed_won?",
    "expected_sql_pattern": "closed_won",
    "expected_row_count": 1
  }
]
```
Mix difficulty: simple counts, joins across 2-3 tables, questions requiring the glossary (win rate, active deals), and 2-3 deliberately ambiguous ones to test failure gracefully.

### Day 17-19: Eval script
**New file:** `backend/run_eval.py`
- Loop through `eval_set.json`, call your `/ask` logic directly (not over HTTP — import the function) for each question
- Compare actual results to expected (exact match where possible, or pattern checks)
- Track: accuracy %, average latency, which questions failed and why
- Print a summary report to console + save results to `eval_results.json`

### Day 20-21: Iterate
- Look at failures — usually prompt wording or missing glossary context
- Adjust the prompt template or add glossary entries
- Re-run eval, record before/after accuracy (e.g., "62% → 87%") — **this number is genuinely valuable to put in your README and mention to the founder**

**✅ Week 3 checkpoint:** a documented, measurable improvement from iterating on eval failures.

---

## WEEK 4 — Observability + Polish + Ship

### Day 22-23: Logging
**New file:** `backend/logger.py`
- Create a `query_logs` table in SQLite (or a simple JSONL log file) recording every `/ask` call: timestamp, question, retrieved context, generated SQL, success/failure, latency_ms
- Wire this into the `/ask` endpoint — log every call automatically

### Day 24-25: Observability dashboard
**New endpoint:** `GET /logs` — returns recent log entries
**New frontend page:** `components/Dashboard.jsx` — simple table showing recent queries, success/fail status, latency. A basic bar chart of latency over time is a nice bonus if time allows (recharts library).

### Day 26-27: Polish + README
**README.md should include:**
- What the project does (2-3 sentences)
- Architecture diagram (can be a simple text/ASCII diagram or drawn in Excalidraw)
- Tech stack and why you chose each piece
- Eval results (before/after accuracy)
- What you learned / what you'd improve with more time
- Screenshots or GIF of it working

### Day 28: Deploy
- Backend → Render or Railway (free tier is fine)
- Frontend → Vercel
- Test the live URL end-to-end before considering it done

### Day 29-30: Wrap up
- Record a 2-3 min Loom/screen recording walking through it
- Finalize founder outreach message with project link + resume attached

---

## Working notes for Claude Code sessions
- Each session, start by running the app locally and confirming last session's work still runs before adding new code
- Commit to Git after each working checkpoint (end of each day's task), not just at week-ends
- If something from this plan turns out to be harder than expected, cut scope (e.g., skip the latency chart, keep the dashboard to a plain table) rather than extending the deadline
