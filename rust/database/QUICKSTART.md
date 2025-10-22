# Database Module Quick Start

Get up and running with the DuckDB database layer in 5 minutes.

## Installation

The database module is already part of the workspace. Just use it:

```toml
# In your Cargo.toml
[dependencies]
database = { path = "../database" }
```

## 30-Second Example

```rust
use database::{DatabaseManager, MetricRecord};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // 1. Create database
    let db = DatabaseManager::new("metrics.duckdb").await?;
    db.initialize().await?;

    // 2. Insert data
    let metric = MetricRecord::new("price", 50000.0)
        .with_symbol("BTC/USD");
    db.insert_metric(&metric).await?;

    // 3. Query data
    let metrics = db.get_metrics("price", Some("BTC/USD"), None, 10).await?;
    println!("Found {} metrics", metrics.len());

    Ok(())
}
```

## Common Operations

### Insert Single Metric

```rust
let metric = MetricRecord::new("order_latency_ms", 42.5)
    .with_symbol("BTC/USD")
    .add_label("exchange", "alpaca");

db.insert_metric(&metric).await?;
```

### Batch Insert (High Performance)

```rust
let metrics: Vec<MetricRecord> = (0..1000)
    .map(|i| MetricRecord::new("price", 50000.0 + i as f64))
    .collect();

db.insert_metrics(&metrics).await?; // 10,000+ records/sec
```

### Query with Filters

```rust
use chrono::{Utc, Duration};

let hour_ago = Utc::now() - Duration::hours(1);
let metrics = db.get_metrics(
    "price",                    // metric name
    Some("BTC/USD"),           // symbol filter
    Some(hour_ago),            // time filter
    100                        // limit
).await?;
```

### Insert Candles

```rust
use database::CandleRecord;

let candle = CandleRecord::new(
    Utc::now(),
    "ETH/USD",
    3000.0,  // open
    3100.0,  // high
    2900.0,  // low
    3050.0,  // close
    1000000  // volume
);

db.insert_candle(&candle).await?;
```

### Aggregated Metrics

```rust
use database::TimeInterval;

let aggregated = db.get_aggregated_metrics(
    "price",
    TimeInterval::Minute,
    Some(hour_ago),
    "avg"  // avg, sum, min, max, count
).await?;
```

### Log Events

```rust
use database::SystemEvent;

db.log_event(&SystemEvent::info("System started")).await?;
db.log_event(&SystemEvent::warning("High latency detected")).await?;
db.log_event(&SystemEvent::error("Connection failed")).await?;
```

### Database Statistics

```rust
let stats = db.get_table_stats().await?;
for stat in stats {
    println!("{}: {} rows", stat.table_name, stat.row_count);
}
```

### Optimize Database

```rust
// Run periodically (e.g., daily)
db.optimize().await?;
```

## Examples

Run the included examples:

```bash
# Basic usage
cargo run --example basic_usage

# Migration demo
cargo run --example migration_example

# Observability integration
cargo run --example observability_integration
```

## Performance Tips

### ✅ DO THIS

```rust
// Batch inserts
db.insert_metrics(&metrics).await?;

// Reuse connections
let db = DatabaseManager::new("metrics.duckdb").await?;
// Use db for all operations

// Use time filters
db.get_metrics("price", None, Some(hour_ago), 1000).await?;
```

### ❌ DON'T DO THIS

```rust
// Individual inserts (slow)
for metric in metrics {
    db.insert_metric(&metric).await?;
}

// Create new connections (expensive)
for _ in 0..10 {
    let db = DatabaseManager::new("metrics.duckdb").await?;
}

// Unbounded queries (memory issues)
db.get_metrics("price", None, None, 1000000).await?;
```

## Migration from PostgreSQL

```rust
use database::migrations::TimescaleMigrator;

// From CSV export
let count = TimescaleMigrator::migrate_from_csv(
    "postgres_export.csv",
    "trading_metrics",
    &conn
)?;

println!("Migrated {} records", count);
```

## Database Schema

### trading_metrics
- `timestamp`: TIMESTAMP
- `metric_name`: VARCHAR
- `value`: DOUBLE
- `symbol`: VARCHAR (optional)
- `labels`: JSON (optional)

### trading_candles
- `timestamp`: TIMESTAMP
- `symbol`: VARCHAR
- `open`, `high`, `low`, `close`: DOUBLE
- `volume`: BIGINT
- `trade_count`: INTEGER

### system_events
- `id`: BIGINT (auto-increment)
- `timestamp`: TIMESTAMP
- `event_type`: VARCHAR
- `severity`: VARCHAR (info, warning, error, critical)
- `message`: TEXT
- `details`: JSON

## Troubleshooting

### Database Locked
Use connection pooling (DatabaseManager handles this automatically).

### Slow Queries
1. Add time filters
2. Use limits
3. Run `db.optimize()` regularly

### High Memory Usage
Process in batches:
```rust
for chunk in data.chunks(10000) {
    db.insert_metrics(chunk).await?;
}
```

## Next Steps

- Read the full [README.md](README.md)
- Check [examples/](examples/)
- Generate API docs: `cargo doc --open`
- Review [DATABASE_IMPLEMENTATION_SUMMARY.md](../../docs/DATABASE_IMPLEMENTATION_SUMMARY.md)

## Need Help?

- Check inline documentation
- Run examples
- Review tests in `src/tests.rs`
- See integration tests

---

**Happy coding!** 🚀
