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
    truncated: bool


class GlossaryHit(BaseModel):
    term: str
    definition: str
    score: float


class AskRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class AskResponse(BaseModel):
    response_type: str  # "sql" | "chat"
    question: str
    message: Optional[str] = None
    generated_sql: Optional[str] = None
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    attempts: int
    verified: bool
    retrieved_context: list[GlossaryHit]
    trace: list[dict[str, Any]]
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    conversation_id: str


class LogEntry(BaseModel):
    timestamp: str
    question: str
    success: bool
    total_latency_ms: float
    response_type: Optional[str] = None
    generated_sql: Optional[str] = None
    verified: Optional[bool] = None
    attempts: Optional[int] = None
    row_count: Optional[int] = None
    retrieved_terms: list[str] = []
    estimated_cost_usd: Optional[float] = None
    error: Optional[str] = None


class LogsResponse(BaseModel):
    entries: list[LogEntry]
