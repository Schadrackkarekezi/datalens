"""
Pydantic models define the request/response shapes for the API.

FastAPI uses these for three things at once: validating incoming JSON,
serializing outgoing JSON, and generating the OpenAPI docs at /docs —
one class definition drives all three.
"""

from typing import Any
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
