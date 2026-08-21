"""
Pydantic models define the request/response shapes for the API.

FastAPI uses these for three things at once: validating incoming JSON,
serializing outgoing JSON, and generating the OpenAPI docs at /docs —
one class definition drives all three.
"""

from typing import Any, Optional
from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    type: str


class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]


class SchemaResponse(BaseModel):
    tables: list[TableInfo]


class QueryRequest(BaseModel):
    sql: str


class QueryResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float


class GlossaryHit(BaseModel):
    term: str
    definition: str
    score: float


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    generated_sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    attempts: int
    retrieved_context: list[GlossaryHit]
    trace: list[dict[str, Any]]


class LogEntry(BaseModel):
    timestamp: str
    question: str
    success: bool
    total_latency_ms: float
    generated_sql: Optional[str]
    attempts: Optional[int]
    row_count: Optional[int]
    retrieved_terms: list[str]
    error: Optional[str]


class LogsResponse(BaseModel):
    entries: list[LogEntry]
