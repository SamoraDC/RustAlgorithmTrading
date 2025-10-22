#!/usr/bin/env python3
"""
Quick validation script for storage implementation

Run without dependencies to check imports and basic structure.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_imports():
    """Validate all imports work"""
    print("Validating imports...")

    try:
        from src.observability.storage import (
            DuckDBClient,
            SQLiteClient,
            MetricRecord,
            CandleRecord,
            PerformanceRecord,
            TimeInterval,
        )
        print("✓ Core storage imports OK")
    except ImportError as e:
        print(f"✗ Core imports failed: {e}")
        return False

    try:
        from src.observability.storage.integration import (
            StorageManager,
            get_storage_manager,
            storage_lifespan,
            get_storage,
        )
        print("✓ Integration imports OK")
    except ImportError as e:
        print(f"✗ Integration imports failed: {e}")
        return False

    return True


def validate_schemas():
    """Validate schema definitions"""
    print("\nValidating schemas...")

    from src.observability.storage.schemas import (
        DUCKDB_SCHEMAS,
        SQLITE_SCHEMAS,
        TimeInterval,
    )

    # Check DuckDB schemas
    required_tables = ["trading_metrics", "candles", "performance_history"]
    for table in required_tables:
        if table not in DUCKDB_SCHEMAS:
            print(f"✗ Missing DuckDB schema: {table}")
            return False
    print(f"✓ DuckDB schemas complete ({len(DUCKDB_SCHEMAS)} tables)")

    # Check SQLite schemas
    required_tables = ["trade_log", "system_events"]
    for table in required_tables:
        if table not in SQLITE_SCHEMAS:
            print(f"✗ Missing SQLite schema: {table}")
            return False
    print(f"✓ SQLite schemas complete ({len(SQLITE_SCHEMAS)} tables)")

    # Check time intervals
    intervals = [e.value for e in TimeInterval]
    print(f"✓ Time intervals: {', '.join(intervals)}")

    return True


def validate_client_structure():
    """Validate client class structure"""
    print("\nValidating client structure...")

    from src.observability.storage.duckdb_client import DuckDBClient
    from src.observability.storage.sqlite_client import SQLiteClient

    # Check DuckDB methods
    duckdb_methods = [
        "initialize", "close", "insert_metric", "insert_metrics",
        "insert_candle", "insert_candles", "insert_performance",
        "get_metrics", "get_candles", "get_performance_summary",
        "get_aggregated_metrics", "optimize", "get_table_stats"
    ]

    for method in duckdb_methods:
        if not hasattr(DuckDBClient, method):
            print(f"✗ DuckDBClient missing method: {method}")
            return False
    print(f"✓ DuckDBClient methods complete ({len(duckdb_methods)} methods)")

    # Check SQLite methods
    sqlite_methods = [
        "initialize", "close", "log_trade", "get_trades",
        "get_trade_stats", "log_event", "get_events",
        "get_event_counts", "vacuum", "get_db_size"
    ]

    for method in sqlite_methods:
        if not hasattr(SQLiteClient, method):
            print(f"✗ SQLiteClient missing method: {method}")
            return False
    print(f"✓ SQLiteClient methods complete ({len(sqlite_methods)} methods)")

    return True


def validate_integration():
    """Validate integration layer"""
    print("\nValidating integration layer...")

    from src.observability.storage.integration import StorageManager

    manager_methods = [
        "initialize", "close", "record_metric", "get_recent_metrics",
        "get_market_data", "log_trade_execution", "get_trading_summary",
        "get_system_health"
    ]

    for method in manager_methods:
        if not hasattr(StorageManager, method):
            print(f"✗ StorageManager missing method: {method}")
            return False
    print(f"✓ StorageManager methods complete ({len(manager_methods)} methods)")

    return True


def validate_file_structure():
    """Validate file structure"""
    print("\nValidating file structure...")

    base_path = Path(__file__).parent.parent

    required_files = [
        "src/observability/storage/__init__.py",
        "src/observability/storage/schemas.py",
        "src/observability/storage/duckdb_client.py",
        "src/observability/storage/sqlite_client.py",
        "src/observability/storage/integration.py",
        "tests/observability/test_duckdb_client.py",
        "tests/observability/test_sqlite_client.py",
        "docs/STORAGE_GUIDE.md",
        "examples/storage_demo.py",
    ]

    all_exist = True
    for file in required_files:
        path = base_path / file
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"✓ {file} ({size_kb:.1f} KB)")
        else:
            print(f"✗ Missing: {file}")
            all_exist = False

    return all_exist


def main():
    """Run all validations"""
    print("="*60)
    print("STORAGE IMPLEMENTATION VALIDATION")
    print("="*60)

    results = {
        "Imports": validate_imports(),
        "Schemas": validate_schemas(),
        "Client Structure": validate_client_structure(),
        "Integration": validate_integration(),
        "File Structure": validate_file_structure(),
    }

    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)

    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run tests: pytest tests/observability/")
        print("  3. Run demo: python examples/storage_demo.py")
        print("  4. Read guide: docs/STORAGE_GUIDE.md")
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("\nPlease fix the issues above.")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
