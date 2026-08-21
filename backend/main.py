import sqlite3
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection
from models import ColumnInfo, TableInfo, SchemaResponse, QueryRequest, QueryResponse

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
        cur = conn.cursor()
        table_names = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]

        tables = []
        for name in table_names:
            columns = [
                ColumnInfo(name=col[1], type=col[2])
                for col in cur.execute(f"PRAGMA table_info({name})").fetchall()
            ]
            tables.append(TableInfo(name=name, columns=columns))

    return SchemaResponse(tables=tables)


@app.post("/query", response_model=QueryResponse)
def run_query(request: QueryRequest):
    sql = request.sql.strip()

    if not sql.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    with get_connection() as conn:
        cur = conn.cursor()
        try:
            start = time.perf_counter()
            cur.execute(sql)
            rows = cur.fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000
        except sqlite3.Error as e:
            raise HTTPException(status_code=400, detail=str(e))

        columns = [desc[0] for desc in cur.description] if cur.description else []

    return QueryResponse(
        columns=columns,
        rows=[list(row) for row in rows],
        row_count=len(rows),
        execution_time_ms=round(elapsed_ms, 2),
    )
