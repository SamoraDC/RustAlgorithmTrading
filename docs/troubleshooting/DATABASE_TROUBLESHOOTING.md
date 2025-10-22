# Database Troubleshooting Guide

## Quick Diagnostics

```bash
# Run comprehensive diagnostic
./scripts/check_dependencies.sh

# Check database files
ls -lh data/*.duckdb data/*.db

# Test database connection
python3 <<EOF
from src.observability.storage import DuckDBClient
import asyncio

async def test():
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()
    stats = await client.get_table_stats()
    print(f"Database OK: {stats}")
    await client.close()

asyncio.run(test())
EOF
```

## Common Issues

### 1. Database Lock Errors

**Symptom**:
```
DatabaseError: database is locked
```

**Causes**:
- Multiple processes accessing database
- Unclosed connections
- SQLite WAL mode not enabled

**Solutions**:

```python
# Solution 1: Use context managers
async with duckdb_session("data/metrics.duckdb") as client:
    await client.insert_metric(...)
# Automatically closes connection

# Solution 2: Ensure connections are closed
client = DuckDBClient("data/metrics.duckdb")
try:
    await client.initialize()
    # ... operations ...
finally:
    await client.close()  # Always close

# Solution 3: Enable WAL mode (SQLite)
import sqlite3
conn = sqlite3.connect("data/events.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.close()
```

### 2. Slow Query Performance

**Symptom**:
```
Query taking >100ms
```

**Diagnosis**:

```python
# Profile query
import duckdb
import time

conn = duckdb.connect("data/metrics.duckdb")
conn.execute("PRAGMA enable_profiling")

start = time.perf_counter()
result = conn.execute("SELECT * FROM trading_metrics WHERE metric_name = 'slow'")
elapsed = (time.perf_counter() - start) * 1000

print(f"Query took {elapsed:.2f}ms")

# View execution plan
plan = conn.execute("EXPLAIN SELECT ...").fetchall()
for row in plan:
    print(row[0])
```

**Solutions**:

```python
# Solution 1: Add indexes
conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp
        ON trading_metrics(metric_name, timestamp)
""")

# Solution 2: Use time filters
# Bad
metrics = await client.get_metrics("price")

# Good
metrics = await client.get_metrics(
    "price",
    start_time=datetime.now() - timedelta(hours=1)
)

# Solution 3: Optimize database
await client.optimize()  # VACUUM + CHECKPOINT

# Solution 4: Use aggregations
# Instead of fetching all data and aggregating in Python
aggregated = await client.get_aggregated_metrics(
    "price",
    interval=TimeInterval.HOUR,
    aggregation="avg"
)
```

### 3. Large Database Files

**Symptom**:
```
metrics.duckdb is >5GB
```

**Diagnosis**:

```bash
# Check size
du -h data/metrics.duckdb

# Check row counts
python3 <<EOF
import duckdb
conn = duckdb.connect("data/metrics.duckdb")

for table in ["trading_metrics", "candles", "performance_history"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    min_ts = conn.execute(f"SELECT MIN(timestamp) FROM {table}").fetchone()[0]
    max_ts = conn.execute(f"SELECT MAX(timestamp) FROM {table}").fetchone()[0]
    print(f"{table}: {count:,} rows ({min_ts} to {max_ts})")

conn.close()
EOF
```

**Solutions**:

```python
# Solution 1: Implement data retention
async def cleanup_old_data(days_to_keep=30):
    client = DuckDBClient("data/metrics.duckdb")
    await client.initialize()

    cutoff = datetime.utcnow() - timedelta(days=days_to_keep)

    await client._execute_sync(lambda: client._conn.execute("""
        DELETE FROM trading_metrics WHERE timestamp < ?
    """, [cutoff]))

    await client.optimize()  # Reclaim space
    await client.close()

# Solution 2: Archive to Parquet
import duckdb
conn = duckdb.connect("data/metrics.duckdb")

# Export old data
conn.execute("""
    COPY (
        SELECT * FROM trading_metrics
        WHERE timestamp < current_timestamp - INTERVAL 90 DAYS
    ) TO 'archive/metrics_old.parquet' (FORMAT PARQUET)
""")

# Delete archived data
conn.execute("""
    DELETE FROM trading_metrics
    WHERE timestamp < current_timestamp - INTERVAL 90 DAYS
""")

conn.execute("VACUUM")
conn.close()

# Solution 3: Compress database
conn.execute("PRAGMA force_compression='lz4'")
```

### 4. High Memory Usage

**Symptom**:
```
Python process using >2GB RAM
```

**Diagnosis**:

```python
import psutil
import os

process = psutil.Process(os.getpid())
mem_info = process.memory_info()

print(f"RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
print(f"VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
```

**Solutions**:

```python
# Solution 1: Limit DuckDB memory
client._conn.execute("PRAGMA memory_limit='2GB'")

# Solution 2: Stream results instead of loading all
# Bad
results = conn.execute("SELECT * FROM huge_table").fetchall()

# Good
for row in conn.execute("SELECT * FROM huge_table"):
    process_row(row)

# Solution 3: Use query limits
metrics = await client.get_metrics(
    "price",
    start_time=...,
    limit=10000  # Prevent OOM
)

# Solution 4: Reduce batch sizes
# Instead of 10,000 at once
for i in range(0, len(all_metrics), 1000):
    batch = all_metrics[i:i+1000]
    await client.insert_metrics(batch)
```

### 5. Missing Data After Migration

**Symptom**:
```
Metrics showing up as empty after migration
```

**Diagnosis**:

```bash
# Check if data was migrated
python3 <<EOF
import duckdb

conn = duckdb.connect("data/metrics.duckdb")

# Verify tables exist
tables = conn.execute("SHOW TABLES").fetchall()
print(f"Tables: {tables}")

# Check row counts
for table in ["trading_metrics", "candles", "performance_history"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count} rows")

conn.close()
EOF
```

**Solutions**:

```python
# Solution 1: Verify migration script ran
# Check logs in logs/observability/

# Solution 2: Re-run migration
from scripts.migrate_timescale_to_duckdb import migrate

asyncio.run(migrate(
    "postgresql://trading@localhost/trading_metrics"
))

# Solution 3: Import from backup
import duckdb
import pandas as pd

conn = duckdb.connect("data/metrics.duckdb")
df = pd.read_csv("backup_metrics.csv")

conn.register('df', df)
conn.execute("""
    INSERT INTO trading_metrics
    SELECT * FROM df
""")

print(f"Imported {len(df)} records")
conn.close()
```

### 6. WebSocket Connection Failures

**Symptom**:
```
WebSocket connection refused or dropping
```

**Diagnosis**:

```bash
# Check if API is running
curl http://localhost:8000/health

# Check WebSocket endpoint
wscat -c ws://localhost:8000/ws/metrics

# Check logs
tail -f logs/observability/api.log | grep -i websocket
```

**Solutions**:

```bash
# Solution 1: Restart observability API
./scripts/stop_observability.sh
./scripts/start_observability.sh

# Solution 2: Check port availability
lsof -i :8000

# Solution 3: Increase connection limits
# Edit src/observability/api/main.py
# MAX_CONNECTIONS = 1000  # Increase if needed

# Solution 4: Check CORS settings
# Ensure frontend URL is allowed in main.py
```

### 7. Observability API Not Starting

**Symptom**:
```
API fails to start or crashes immediately
```

**Diagnosis**:

```bash
# Check Python dependencies
pip list | grep -E "(fastapi|uvicorn|duckdb)"

# Check database file permissions
ls -la data/metrics.duckdb

# Check logs
tail -n 50 logs/observability/api.log

# Test manually
python3 src/observability/server.py
```

**Solutions**:

```bash
# Solution 1: Install missing dependencies
pip install fastapi uvicorn duckdb websockets pydantic

# Solution 2: Fix permissions
chmod 644 data/metrics.duckdb
chmod 755 data/

# Solution 3: Reinitialize database
rm data/metrics.duckdb
python3 -c "
from src.observability.storage import DuckDBClient
import asyncio

async def init():
    client = DuckDBClient('data/metrics.duckdb')
    await client.initialize()
    await client.close()

asyncio.run(init())
"

# Solution 4: Check port conflicts
lsof -ti :8000 | xargs kill -9
```

### 8. Query Returns Empty Results

**Symptom**:
```
Query executes but returns []
```

**Diagnosis**:

```python
# Check if data exists
import duckdb

conn = duckdb.connect("data/metrics.duckdb")

# Verify table has data
count = conn.execute("SELECT COUNT(*) FROM trading_metrics").fetchone()[0]
print(f"Total metrics: {count}")

# Check time range
result = conn.execute("""
    SELECT MIN(timestamp), MAX(timestamp)
    FROM trading_metrics
""").fetchone()
print(f"Time range: {result[0]} to {result[1]}")

# Verify metric names
metrics = conn.execute("""
    SELECT DISTINCT metric_name FROM trading_metrics
""").fetchall()
print(f"Available metrics: {[m[0] for m in metrics]}")

conn.close()
```

**Solutions**:

```python
# Solution 1: Check time range
# Your query might be outside data range
metrics = await client.get_metrics(
    "price",
    start_time=datetime.utcnow() - timedelta(days=365),  # Wider range
    end_time=datetime.utcnow()
)

# Solution 2: Check metric name
# Metric name is case-sensitive
# Use: "order_latency_ms" not "Order_Latency_MS"

# Solution 3: Check symbol filter
# Remove symbol filter to see if data exists
metrics = await client.get_metrics(
    "price",
    start_time=...,
    symbol=None  # Remove filter
)

# Solution 4: Verify data was inserted
# Check insert logs for errors
tail -f logs/observability/api.log | grep insert
```

### 9. Backup/Restore Failures

**Symptom**:
```
Backup or restore fails with errors
```

**Diagnosis**:

```bash
# Check disk space
df -h

# Check file permissions
ls -la data/ backups/

# Test backup manually
cp data/metrics.duckdb /tmp/test_backup.duckdb
```

**Solutions**:

```bash
# Solution 1: Ensure directories exist
mkdir -p backups/

# Solution 2: Stop API before backup
./scripts/stop_observability.sh
cp data/metrics.duckdb backups/metrics_$(date +%Y%m%d_%H%M%S).duckdb
./scripts/start_observability.sh

# Solution 3: Use export instead of copy
python3 <<EOF
import duckdb

conn = duckdb.connect("data/metrics.duckdb")
conn.execute("""
    COPY trading_metrics TO 'backups/metrics_export.parquet' (FORMAT PARQUET)
""")
conn.close()
EOF

# Solution 4: For large databases, use compression
tar -czf backups/metrics_backup.tar.gz data/metrics.duckdb
```

## Performance Optimization Checklist

- [ ] Run `OPTIMIZE` daily
- [ ] Add indexes for frequently queried columns
- [ ] Implement data retention policies
- [ ] Use batch inserts instead of individual inserts
- [ ] Always use time range filters in queries
- [ ] Limit result sets to prevent OOM
- [ ] Monitor query latency with Prometheus
- [ ] Archive old data to Parquet files
- [ ] Configure memory limits appropriately
- [ ] Use time-bucketed aggregations

## Emergency Procedures

### Database Corruption

```bash
# 1. Stop all services
./scripts/stop_observability.sh

# 2. Backup corrupted database
cp data/metrics.duckdb data/metrics_corrupted_$(date +%Y%m%d).duckdb

# 3. Try to recover
python3 <<EOF
import duckdb

conn = duckdb.connect("data/metrics.duckdb")
conn.execute("PRAGMA integrity_check")
conn.close()
EOF

# 4. If recovery fails, restore from backup
cp backups/metrics_latest.duckdb data/metrics.duckdb

# 5. Restart services
./scripts/start_observability.sh
```

### Complete System Reset

```bash
# WARNING: This deletes all data!

# 1. Stop services
./scripts/stop_observability.sh

# 2. Backup current data (optional)
cp data/metrics.duckdb backups/metrics_pre_reset_$(date +%Y%m%d).duckdb

# 3. Remove databases
rm data/metrics.duckdb data/events.db

# 4. Reinitialize
python3 <<EOF
from src.observability.storage import DuckDBClient, SQLiteClient
import asyncio

async def reset():
    duckdb = DuckDBClient("data/metrics.duckdb")
    await duckdb.initialize()
    await duckdb.close()

    sqlite = SQLiteClient("data/events.db")
    await sqlite.initialize()
    await sqlite.close()

    print("Databases reinitialized")

asyncio.run(reset())
EOF

# 5. Restart services
./scripts/start_observability.sh
```

## Getting Help

### Diagnostic Information to Collect

```bash
# System information
uname -a
python3 --version
pip list | grep -E "(duckdb|fastapi|uvicorn)"

# Database status
ls -lh data/
python3 -c "from src.observability.storage import DuckDBClient; import asyncio; asyncio.run(DuckDBClient('data/metrics.duckdb').get_table_stats())"

# API logs
tail -n 100 logs/observability/api.log

# Process information
ps aux | grep -E "(python|uvicorn)"
lsof -i :8000
```

### Support Channels

- **Documentation**: /docs/README.md
- **API Reference**: /docs/api/DATABASE_MODULE.md
- **Migration Guide**: /docs/migration/DUCKDB_MIGRATION.md
- **Observability Guide**: /docs/observability/DUCKDB_OBSERVABILITY.md
- **GitHub Issues**: https://github.com/SamoraDC/RustAlgorithmTrading/issues

### Reporting Issues

When reporting issues, include:
1. Error message (full stack trace)
2. Steps to reproduce
3. System information (OS, Python version)
4. Database statistics
5. Relevant log excerpts
6. Configuration files (sanitized)

## Summary

Most database issues can be resolved by:
1. Using connection context managers
2. Implementing proper error handling
3. Regular database optimization
4. Monitoring performance metrics
5. Maintaining proper backups

For persistent issues, review logs and run diagnostic scripts before seeking support.
