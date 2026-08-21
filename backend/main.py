import time

import openai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection, fetch_schema
from query_engine import run_select, QueryError
from agent import run_ask, AgentError
from logger import log_ask, read_logs
from models import (
    ColumnInfo,
    TableInfo,
    SchemaResponse,
    QueryRequest,
    QueryResponse,
    AskRequest,
    AskResponse,
    LogsResponse,
)

app = FastAPI(title="DataLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/schema", response_model=SchemaResponse)
def get_schema():
    with get_connection() as conn:
        tables = fetch_schema(conn)

    return SchemaResponse(
        tables=[
            TableInfo(
                name=t["name"],
                columns=[ColumnInfo(name=c["name"], type=c["type"]) for c in t["columns"]],
            )
            for t in tables
        ]
    )


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        columns, rows, elapsed_ms = run_select(request.sql)
    except QueryError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return QueryResponse(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=elapsed_ms,
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    start = time.perf_counter()
    try:
        result = run_ask(request.question)
    except AgentError as e:
        log_ask(request.question, (time.perf_counter() - start) * 1000, success=False, error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except openai.AuthenticationError:
        detail = "OPENAI_API_KEY is missing or invalid — set it in backend/.env"
        log_ask(request.question, (time.perf_counter() - start) * 1000, success=False, error=detail)
        raise HTTPException(status_code=500, detail=detail)
    except openai.RateLimitError:
        detail = "OpenAI API rate limit hit — try again shortly"
        log_ask(request.question, (time.perf_counter() - start) * 1000, success=False, error=detail)
        raise HTTPException(status_code=429, detail=detail)
    except openai.APIStatusError as e:
        detail = f"OpenAI API error: {e.message}"
        log_ask(request.question, (time.perf_counter() - start) * 1000, success=False, error=detail)
        raise HTTPException(status_code=502, detail=detail)
    except openai.OpenAIError as e:
        detail = f"OPENAI_API_KEY is missing or invalid — set it in backend/.env ({e})"
        log_ask(request.question, (time.perf_counter() - start) * 1000, success=False, error=detail)
        raise HTTPException(status_code=500, detail=detail)

    log_ask(request.question, (time.perf_counter() - start) * 1000, success=True, result=result)
    return AskResponse(**result)


@app.get("/logs", response_model=LogsResponse)
def logs(limit: int = 50):
    return LogsResponse(entries=read_logs(limit))
