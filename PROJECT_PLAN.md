# DataLens — Project Plan

A SQL query tool with an AI agent layer (RAG-backed), evaluation framework, and observability.

**Purpose:** Portfolio project demonstrating engineering depth — for founder outreach, AI Engineer / FDE / Data Scientist / Data Engineer roles.

**Stack:** React (frontend) + FastAPI (backend) + SQLite (data) + FAISS or Pinecone (vector DB) + GPT-4o or Claude API (LLM) + Render/Railway + Vercel (deployment)

**Time budget:** ~1.5–2 hrs/day. **Rule: if a week runs behind, cut scope for that week — never push the final ship date.**

---

## Current status
✅ Day 1-2 complete: `backend/seed_db.py` creates `datalens.db` with 4 tables (`departments`, `employees`, `customers`, `deals`) and realistic sample data (30 employees, 25 customers, 120 deals). Verified working with join queries.

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
- Logic:
  1. Send the question + full schema (from `/schema` logic) to the LLM
  2. Prompt: "Given this schema: {schema}. Write a SQLite SELECT query to answer: {question}. Return ONLY the SQL, no explanation."
  3. Execute the returned SQL against the database (reuse `/query` logic)
  4. Return both the generated SQL and the results
- Response shape:
  ```json
  {
    "question": "...",
    "generated_sql": "SELECT ...",
    "columns": [...],
    "rows": [...]
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
