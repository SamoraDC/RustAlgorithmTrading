"""
Observability Storage Module

Provides high-performance time-series and operational data storage:
- DuckDB: Analytics and time-series data (OLAP)
- SQLite: Operational data and metadata (OLTP)
"""

from .duckdb_client import DuckDBClient
from .sqlite_client import SQLiteClient
from .schemas import (
    MetricRecord,
    CandleRecord,
    PerformanceRecord,
    TimeInterval,
)

__all__ = [
    "DuckDBClient",
    "SQLiteClient",
    "MetricRecord",
    "CandleRecord",
    "PerformanceRecord",
    "TimeInterval",
]
