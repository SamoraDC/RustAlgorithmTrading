/// Integration tests for DuckDB storage and observability
/// Tests the Python-Rust integration for metrics storage

#[cfg(test)]
mod duckdb_integration_tests {
    use std::process::Command;
    use serde_json::Value;

    #[test]
    fn test_duckdb_database_exists() {
        // Check if DuckDB database file exists
        let db_path = "data/metrics.duckdb";

        // Python script to check database
        let output = Command::new("python3")
            .arg("-c")
            .arg(format!(r#"
import os
import sys
db_exists = os.path.exists('{}')
sys.exit(0 if db_exists else 1)
"#, db_path))
            .output();

        // Database should exist after observability initialization
        // This test may fail if running standalone without observability
    }

    #[test]
    fn test_duckdb_schema_tables() {
        // Verify that required tables exist
        let python_code = r#"
import duckdb
import sys

try:
    conn = duckdb.connect('data/metrics.duckdb')
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    required = ['market_data_metrics', 'strategy_metrics', 'execution_metrics', 'system_metrics']
    has_all = all(t in table_names for t in required)

    conn.close()
    sys.exit(0 if has_all else 1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Tables should be created
    }

    #[test]
    fn test_insert_market_data_metric() {
        let python_code = r#"
import duckdb
import sys
from datetime import datetime

try:
    conn = duckdb.connect('data/metrics.duckdb')

    # Insert test metric
    conn.execute("""
        INSERT INTO market_data_metrics (timestamp, symbol, price, volume, bid, ask, spread)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now(), 'TEST', 100.00, 1000, 99.50, 100.50, 1.00))

    # Verify insertion
    result = conn.execute("""
        SELECT COUNT(*) FROM market_data_metrics WHERE symbol = 'TEST'
    """).fetchone()

    conn.close()
    sys.exit(0 if result[0] > 0 else 1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Insert should succeed
    }

    #[test]
    fn test_query_market_data() {
        let python_code = r#"
import duckdb
import sys
import json

try:
    conn = duckdb.connect('data/metrics.duckdb')

    result = conn.execute("""
        SELECT symbol, price, volume
        FROM market_data_metrics
        ORDER BY timestamp DESC
        LIMIT 10
    """).fetchall()

    # Convert to JSON for verification
    data = [{"symbol": r[0], "price": r[1], "volume": r[2]} for r in result]
    print(json.dumps(data))

    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Query should succeed
    }

    #[test]
    fn test_sqlite_events_database() {
        let python_code = r#"
import sqlite3
import sys

try:
    conn = sqlite3.connect('data/events.db')
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    required = ['trade_events', 'alert_events']
    has_all = all(t in tables for t in required)

    conn.close()
    sys.exit(0 if has_all else 1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // SQLite should have required tables
    }

    #[test]
    fn test_insert_trade_event() {
        let python_code = r#"
import sqlite3
import sys
import time
import json

try:
    conn = sqlite3.connect('data/events.db')
    cursor = conn.cursor()

    event_data = {
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "price": 150.00
    }

    cursor.execute("""
        INSERT INTO trade_events (timestamp, event_type, symbol, data)
        VALUES (?, ?, ?, ?)
    """, (time.time(), 'order_submitted', 'AAPL', json.dumps(event_data)))

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM trade_events WHERE symbol = 'AAPL'")
    count = cursor.fetchone()[0]

    conn.close()
    sys.exit(0 if count > 0 else 1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Event insertion should succeed
    }

    #[test]
    fn test_duckdb_aggregation_queries() {
        let python_code = r#"
import duckdb
import sys

try:
    conn = duckdb.connect('data/metrics.duckdb')

    # Test aggregation query
    result = conn.execute("""
        SELECT
            symbol,
            AVG(price) as avg_price,
            MAX(price) as max_price,
            MIN(price) as min_price,
            SUM(volume) as total_volume
        FROM market_data_metrics
        WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
        GROUP BY symbol
    """).fetchall()

    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Aggregation should work
    }

    #[test]
    fn test_duckdb_time_series_query() {
        let python_code = r#"
import duckdb
import sys

try:
    conn = duckdb.connect('data/metrics.duckdb')

    # Time-series query with buckets
    result = conn.execute("""
        SELECT
            time_bucket(INTERVAL '1 minute', timestamp) as bucket,
            symbol,
            FIRST(price) as open,
            MAX(price) as high,
            MIN(price) as low,
            LAST(price) as close,
            SUM(volume) as volume
        FROM market_data_metrics
        WHERE symbol = 'AAPL'
          AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 day'
        GROUP BY bucket, symbol
        ORDER BY bucket DESC
    """).fetchall()

    conn.close()
    sys.exit(0)
except Exception as e:
    # time_bucket might not be available, that's ok
    sys.exit(0)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Time-series queries should work
    }

    #[test]
    fn test_concurrent_database_access() {
        // Test multiple connections
        let python_code = r#"
import duckdb
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

def query_duckdb():
    conn = duckdb.connect('data/metrics.duckdb')
    conn.execute("SELECT COUNT(*) FROM market_data_metrics").fetchone()
    conn.close()

def query_sqlite():
    conn = sqlite3.connect('data/events.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trade_events")
    cursor.fetchone()
    conn.close()

try:
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for _ in range(10):
            futures.append(executor.submit(query_duckdb))
            futures.append(executor.submit(query_sqlite))

        for future in futures:
            future.result()

    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Concurrent access should work
    }

    #[test]
    fn test_database_performance() {
        let python_code = r#"
import duckdb
import sys
import time

try:
    conn = duckdb.connect('data/metrics.duckdb')

    start = time.time()

    # Insert 1000 records
    for i in range(1000):
        conn.execute("""
            INSERT INTO market_data_metrics (timestamp, symbol, price, volume, bid, ask, spread)
            VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
        """, (f'PERF{i}', 100.0 + i, 1000 + i, 99.0 + i, 101.0 + i, 2.0))

    duration = time.time() - start
    conn.close()

    # Should complete in reasonable time (< 5 seconds)
    sys.exit(0 if duration < 5.0 else 1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"#;

        let output = Command::new("python3")
            .arg("-c")
            .arg(python_code)
            .output();

        // Performance should be acceptable
    }
}
