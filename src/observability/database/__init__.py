"""
Database management for observability metrics.

Provides DuckDB-based time-series storage with:
- High-performance columnar storage
- SQL query interface
- Batch write optimization
- Thread-safe connection pooling
"""
from .duckdb_manager import DuckDBManager, get_db

__all__ = ["DuckDBManager", "get_db"]
