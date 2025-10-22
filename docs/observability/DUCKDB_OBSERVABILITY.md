# DuckDB Observability Guide

## Overview

This guide covers monitoring, troubleshooting, and optimizing the DuckDB-based observability stack for the py_rt algorithmic trading system.

## Monitoring DuckDB

### Database Health Metrics

```python
# Get database statistics
from src.observability.storage import DuckDBClient
import asyncio

async def check_database_health():
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()

    # Get table statistics
    stats = await client.get_table_stats()

    for table, info in stats.items():
        print(f"{table}:")
        print(f"  Rows: {info['row_count']:,}")
        print(f"  Time range: {info['min_timestamp']} to {info['max_timestamp']}")

    await client.close()

asyncio.run(check_database_health())
```

### Key Metrics to Monitor

| Metric | Target | Alert Threshold | Description |
|--------|--------|-----------------|-------------|
| **Database Size** | <1GB | >5GB | Disk space usage |
| **Query Latency (p50)** | <10ms | >50ms | Median query time |
| **Query Latency (p99)** | <50ms | >200ms | 99th percentile |
| **Insert Throughput** | >1000/s | <100/s | Records per second |
| **Active Connections** | 1-4 | >10 | Connection pool size |
| **Memory Usage** | <500MB | >2GB | In-process memory |

### Prometheus Integration

```python
# src/observability/metrics/duckdb_metrics.py
from prometheus_client import Gauge, Histogram, Counter

# Database size
duckdb_size_bytes = Gauge(
    'duckdb_size_bytes',
    'DuckDB database file size in bytes'
)

# Query performance
duckdb_query_duration = Histogram(
    'duckdb_query_duration_seconds',
    'DuckDB query execution time',
    buckets=[.001, .005, .01, .025, .05, .1, .25, .5, 1.0]
)

# Insert performance
duckdb_insert_duration = Histogram(
    'duckdb_insert_duration_seconds',
    'DuckDB batch insert time',
    buckets=[.0001, .0005, .001, .005, .01, .025, .05]
)

# Record counts
duckdb_records_total = Counter(
    'duckdb_records_total',
    'Total records in DuckDB',
    ['table']
)

# Instrument client methods
class InstrumentedDuckDBClient(DuckDBClient):
    async def insert_metrics(self, metrics):
        with duckdb_insert_duration.time():
            await super().insert_metrics(metrics)
            duckdb_records_total.labels(table="trading_metrics").inc(len(metrics))

    async def get_metrics(self, *args, **kwargs):
        with duckdb_query_duration.time():
            return await super().get_metrics(*args, **kwargs)
```

## Performance Dashboards

### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "DuckDB Observability",
    "panels": [
      {
        "title": "Database Size",
        "targets": [
          {
            "expr": "duckdb_size_bytes / 1024 / 1024 / 1024",
            "legendFormat": "DB Size (GB)"
          }
        ]
      },
      {
        "title": "Query Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, duckdb_query_duration_seconds_bucket)",
            "legendFormat": "p99 latency"
          }
        ]
      },
      {
        "title": "Insert Throughput",
        "targets": [
          {
            "expr": "rate(duckdb_records_total[5m])",
            "legendFormat": "Records/sec"
          }
        ]
      },
      {
        "title": "Table Row Counts",
        "targets": [
          {
            "expr": "duckdb_records_total",
            "legendFormat": "{{table}}"
          }
        ]
      }
    ]
  }
}
```

## Log Aggregation

### Structured Logging for DuckDB Operations

```python
# src/observability/storage/duckdb_client.py
import logging
import structlog

logger = structlog.get_logger()

class DuckDBClient:
    async def insert_metrics(self, metrics):
        logger.info(
            "duckdb_insert_start",
            batch_size=len(metrics),
            db_path=str(self.db_path)
        )

        try:
            await self._execute_sync(self._insert_metrics, metrics)

            logger.info(
                "duckdb_insert_success",
                batch_size=len(metrics),
                duration_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as e:
            logger.error(
                "duckdb_insert_failed",
                batch_size=len(metrics),
                error=str(e),
                exc_info=True
            )
            raise
```

### Log Queries

```bash
# Query DuckDB operation logs
tail -f logs/observability/api.log | jq 'select(.event | startswith("duckdb_"))'

# Find slow queries
tail -f logs/observability/api.log | jq 'select(.event == "duckdb_query_slow" and .duration_ms > 100)'

# Count errors
tail -f logs/observability/api.log | jq -r 'select(.event == "duckdb_insert_failed")' | wc -l
```

## Performance Troubleshooting

### Slow Queries

#### Diagnosis

```python
# Enable query profiling
import duckdb

conn = duckdb.connect("data/metrics.duckdb")
conn.execute("PRAGMA enable_profiling")
conn.execute("PRAGMA profile_output='profile.json'")

# Run slow query
result = conn.execute("""
    SELECT * FROM trading_metrics
    WHERE metric_name = 'slow_query'
    ORDER BY timestamp DESC
    LIMIT 1000
""")

# View profile
import json
with open("profile.json") as f:
    profile = json.load(f)
    print(json.dumps(profile, indent=2))
```

#### Solutions

1. **Add Missing Indexes**

```sql
-- Check if index exists
SELECT * FROM duckdb_indexes();

-- Create index if missing
CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp
    ON trading_metrics(metric_name, timestamp);
```

2. **Use Time Filters**

```python
# Bad: No time filter (full table scan)
results = await client.get_metrics("price")

# Good: Time filter (index scan)
results = await client.get_metrics(
    "price",
    start_time=datetime.utcnow() - timedelta(hours=1)
)
```

3. **Optimize Aggregations**

```sql
-- Slow: Aggregate on raw data
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(value)
FROM trading_metrics
WHERE metric_name = 'price'
GROUP BY hour;

-- Fast: Use time_bucket
SELECT
    time_bucket(INTERVAL '1 hour', timestamp) as hour,
    AVG(value)
FROM trading_metrics
WHERE metric_name = 'price'
GROUP BY hour;
```

### High Memory Usage

#### Diagnosis

```python
import psutil
import os

def check_memory_usage():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    print(f"RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB")

    # DuckDB-specific memory
    conn = duckdb.connect("data/metrics.duckdb")
    result = conn.execute("PRAGMA database_size").fetchone()
    print(f"Database size: {result[0] / 1024 / 1024:.2f} MB")
```

#### Solutions

1. **Limit Memory**

```python
# Configure memory limit
conn = duckdb.connect("data/metrics.duckdb")
conn.execute("PRAGMA memory_limit='2GB'")
```

2. **Use Streaming Queries**

```python
# Bad: Load all results into memory
results = conn.execute("SELECT * FROM huge_table").fetchall()

# Good: Stream results
for row in conn.execute("SELECT * FROM huge_table"):
    process_row(row)
```

3. **Optimize Database**

```python
# Regular optimization
async def optimize_database():
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()
    await client.optimize()  # VACUUM + CHECKPOINT
    await client.close()
```

### Large Database Files

#### Check Size

```bash
# Check database size
du -h data/metrics.duckdb

# Breakdown by table
python3 <<EOF
import duckdb
conn = duckdb.connect("data/metrics.duckdb")

for table in ["trading_metrics", "candles", "performance_history"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count:,} rows")

conn.close()
EOF
```

#### Solutions

1. **Data Retention Policy**

```python
# Delete old data
async def cleanup_old_data(days_to_keep=30):
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()

    cutoff = datetime.utcnow() - timedelta(days=days_to_keep)

    await client._execute_sync(lambda: client._conn.execute("""
        DELETE FROM trading_metrics
        WHERE timestamp < ?
    """, [cutoff]))

    await client.optimize()
    await client.close()
```

2. **Export to Parquet**

```python
# Archive old data to Parquet
import duckdb

conn = duckdb.connect("data/metrics.duckdb")

# Export old data
conn.execute("""
    COPY (
        SELECT * FROM trading_metrics
        WHERE timestamp < current_timestamp - INTERVAL 90 DAYS
    ) TO 'archive/metrics_archive.parquet' (FORMAT PARQUET)
""")

# Delete exported data
conn.execute("""
    DELETE FROM trading_metrics
    WHERE timestamp < current_timestamp - INTERVAL 90 DAYS
""")

# Reclaim space
conn.execute("VACUUM")
conn.close()
```

## Alerting Rules

### Prometheus Alerts

```yaml
# prometheus/rules/duckdb_alerts.yml
groups:
  - name: duckdb
    interval: 30s
    rules:
      - alert: DuckDBSlowQueries
        expr: histogram_quantile(0.99, duckdb_query_duration_seconds_bucket) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "DuckDB queries are slow"
          description: "p99 query latency is {{ $value }}s (threshold: 0.1s)"

      - alert: DuckDBLargeDatabase
        expr: duckdb_size_bytes > 5 * 1024 * 1024 * 1024
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "DuckDB database is large"
          description: "Database size is {{ $value | humanize }}B (threshold: 5GB)"

      - alert: DuckDBLowInsertThroughput
        expr: rate(duckdb_records_total[5m]) < 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "DuckDB insert throughput is low"
          description: "Insert rate is {{ $value }} records/sec (threshold: 100/sec)"
```

## Backup and Recovery

### Automated Backups

```python
# scripts/backup_duckdb.py
#!/usr/bin/env python3
import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    source = Path("data/metrics.duckdb")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"metrics_{timestamp}.duckdb"

    print(f"Backing up {source} to {backup_file}")
    shutil.copy2(source, backup_file)

    # Keep only last 7 days
    for old_backup in sorted(backup_dir.glob("metrics_*.duckdb"))[:-7]:
        print(f"Removing old backup: {old_backup}")
        old_backup.unlink()

if __name__ == "__main__":
    backup_database()
```

```bash
# Schedule daily backups (crontab)
0 2 * * * /usr/bin/python3 /path/to/scripts/backup_duckdb.py
```

### Recovery

```python
# Restore from backup
import shutil
from pathlib import Path

def restore_database(backup_file: str):
    source = Path(backup_file)
    target = Path("data/metrics.duckdb")

    print(f"Restoring {source} to {target}")

    # Stop observability API first!
    # ./scripts/stop_observability.sh

    shutil.copy2(source, target)
    print("Restore complete")

# Usage
restore_database("backups/metrics_20250421_020000.duckdb")
```

## Query Optimization

### Explain Plans

```python
# Analyze query execution
import duckdb

conn = duckdb.connect("data/metrics.duckdb")

# Get query plan
plan = conn.execute("""
    EXPLAIN
    SELECT * FROM trading_metrics
    WHERE metric_name = 'price'
    ORDER BY timestamp DESC
    LIMIT 100
""").fetchall()

for row in plan:
    print(row[0])

# Expected plan should show:
# - INDEX SCAN on idx_metrics_name
# - Filter on metric_name
# - Top-N optimization for LIMIT
```

### Index Analysis

```python
# Check index usage
conn.execute("""
    SELECT
        table_name,
        index_name,
        is_unique,
        sql
    FROM duckdb_indexes()
    ORDER BY table_name
""").fetchall()

# Verify indexes exist for:
# - trading_metrics(timestamp)
# - trading_metrics(metric_name)
# - trading_metrics(symbol)
# - candles(symbol, timestamp)
```

## Best Practices

### 1. Regular Maintenance

```python
# Daily maintenance script
async def daily_maintenance():
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()

    # Optimize database
    await client.optimize()

    # Check statistics
    stats = await client.get_table_stats()
    print(f"Database health: {stats}")

    await client.close()

# Schedule with cron
# 0 3 * * * python3 scripts/daily_maintenance.py
```

### 2. Monitor Key Metrics

```python
# Health check script
async def health_check():
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()

    # Check query performance
    import time
    start = time.perf_counter()

    await client.get_latest_metrics(limit=100)

    latency_ms = (time.perf_counter() - start) * 1000

    if latency_ms > 50:
        print(f"WARNING: Slow query detected ({latency_ms:.1f}ms)")

    await client.close()
```

### 3. Capacity Planning

```python
# Estimate database growth
import duckdb
from datetime import timedelta

conn = duckdb.connect("data/metrics.duckdb")

# Get current size
current_size = Path("data/metrics.duckdb").stat().st_size / 1024 / 1024  # MB

# Get insert rate
result = conn.execute("""
    SELECT
        COUNT(*) / EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) as records_per_sec
    FROM trading_metrics
    WHERE timestamp > current_timestamp - INTERVAL 1 DAY
""").fetchone()

records_per_sec = result[0]

# Estimate growth
bytes_per_record = current_size * 1024 * 1024 / conn.execute("SELECT COUNT(*) FROM trading_metrics").fetchone()[0]
daily_growth_mb = records_per_sec * 86400 * bytes_per_record / 1024 / 1024

print(f"Current size: {current_size:.2f} MB")
print(f"Daily growth: {daily_growth_mb:.2f} MB/day")
print(f"Projected size (30 days): {current_size + daily_growth_mb * 30:.2f} MB")
```

## Summary

### Key Takeaways

1. **Monitor**: Track database size, query latency, and insert throughput
2. **Optimize**: Run VACUUM regularly, add indexes for slow queries
3. **Alert**: Set up Prometheus alerts for performance degradation
4. **Backup**: Automated daily backups with 7-day retention
5. **Maintain**: Regular maintenance scripts for optimization

### Performance Targets

- **Query Latency**: <10ms (p50), <50ms (p99)
- **Insert Throughput**: >1000 records/second
- **Database Size**: <1GB (with retention policies)
- **Memory Usage**: <500MB per process

### Resources

- **DuckDB Documentation**: https://duckdb.org/docs/
- **Performance Guide**: /docs/STORAGE_GUIDE.md
- **API Reference**: /docs/api/DATABASE_MODULE.md
- **Troubleshooting**: /docs/developer/troubleshooting.md
