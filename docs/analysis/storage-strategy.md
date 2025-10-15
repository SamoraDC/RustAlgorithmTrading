# Storage Strategy Document

## Executive Summary

This document defines the storage architecture for the Rust algorithmic trading system, covering hot path (in-memory), warm path (local disk), and cold path (archival) storage strategies. The design optimizes for sub-millisecond latency on critical paths while ensuring data durability and efficient historical analysis.

## 1. Storage Tiers

### 1.1 Tier Overview

| Tier | Purpose | Technology | Latency | Retention |
|------|---------|------------|---------|-----------|
| **Hot** | Real-time trading state | In-memory | <1μs | Minutes |
| **Warm** | Intraday history | Local SSD (Parquet) | <1ms | Days |
| **Cold** | Long-term backtest data | Compressed Parquet | <100ms | Years |

### 1.2 Data Flow

```
WebSocket → Hot (RAM) → Warm (SSD) → Cold (Archive)
              ↓
         Trading Engine
              ↓
         Metrics/Logs
```

## 2. Hot Path Storage (In-Memory)

### 2.1 Design Principles

1. **Lock-free data structures** for concurrent access
2. **Cache-aligned memory** to avoid false sharing
3. **Zero-copy serialization** where possible
4. **Bounded memory usage** to prevent OOM

### 2.2 Order Book Storage

**Data Structure**
```rust
use dashmap::DashMap;
use parking_lot::RwLock;
use std::sync::Arc;

/// Thread-safe order book cache
pub struct OrderBookCache {
    /// Symbol → OrderBook mapping (read-heavy)
    books: DashMap<String, Arc<RwLock<OrderBook>>>,

    /// Maximum symbols to track
    max_symbols: usize,
}

impl OrderBookCache {
    /// Get or create order book for symbol
    pub fn get_or_create(&self, symbol: &str) -> Arc<RwLock<OrderBook>> {
        self.books
            .entry(symbol.to_string())
            .or_insert_with(|| {
                Arc::new(RwLock::new(OrderBook::new(symbol)))
            })
            .clone()
    }

    /// Update order book from quote
    pub fn update_from_quote(&self, quote: &Quote) {
        if let Some(book) = self.books.get(&quote.symbol) {
            let mut book = book.write();
            book.update_from_quote(quote);
        }
    }

    /// Memory usage estimate
    pub fn memory_usage_mb(&self) -> f64 {
        let book_size = std::mem::size_of::<OrderBook>();
        (self.books.len() * book_size) as f64 / 1024.0 / 1024.0
    }
}
```

**Memory Budget**
- 10 symbols × 128 bytes/book = 1.28 KB
- Safety factor 10x = ~13 KB for order books

### 2.3 Event Ring Buffers

**Trade Buffer**
```rust
use crossbeam::queue::ArrayQueue;

/// Lock-free ring buffer for recent trades
pub struct TradeBuffer {
    /// Circular buffer (lock-free)
    buffer: ArrayQueue<Trade>,

    /// Buffer capacity
    capacity: usize,
}

impl TradeBuffer {
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: ArrayQueue::new(capacity),
            capacity,
        }
    }

    /// Push trade (drops oldest if full)
    pub fn push(&self, trade: Trade) {
        if self.buffer.is_full() {
            let _ = self.buffer.pop(); // Drop oldest
        }
        let _ = self.buffer.push(trade);
    }

    /// Get recent trades
    pub fn recent_trades(&self, n: usize) -> Vec<Trade> {
        let mut trades = Vec::with_capacity(n);
        // Snapshot without lock
        while let Some(trade) = self.buffer.pop() {
            trades.push(trade);
            if trades.len() >= n {
                break;
            }
        }
        trades.reverse(); // Newest first
        trades
    }
}
```

**Buffer Sizing**
- 60-second window at 1000 trades/sec = 60,000 trades
- Trade size: 96 bytes
- Memory: 60,000 × 96 = 5.76 MB per symbol
- 10 symbols = ~60 MB total

### 2.4 Position and Order State

**Portfolio State**
```rust
use dashmap::DashMap;
use parking_lot::Mutex;

/// Thread-safe portfolio state
pub struct PortfolioState {
    /// Current positions by symbol
    positions: DashMap<String, Position>,

    /// Pending orders by order ID
    orders: DashMap<Uuid, Order>,

    /// Cash balance (protected by mutex)
    cash: Mutex<f64>,
}

impl PortfolioState {
    /// Apply fill to portfolio
    pub fn apply_fill(&self, order_id: Uuid, fill: &Fill) {
        // Update order
        if let Some(mut order) = self.orders.get_mut(&order_id) {
            order.filled_quantity += fill.quantity;
            order.filled_avg_price = Some(fill.price);

            if order.remaining_quantity() == 0 {
                order.status = OrderStatus::Filled;
            }
        }

        // Update position
        let mut position = self.positions
            .entry(fill.symbol.clone())
            .or_insert_with(|| Position::new(&fill.symbol));

        position.apply_fill(fill.side, fill.quantity, fill.price);

        // Update cash
        let mut cash = self.cash.lock();
        let cost = fill.price * fill.quantity as f64;
        *cash -= match fill.side {
            Side::Buy => cost,
            Side::Sell => -cost,
        };
    }

    /// Get current equity
    pub fn equity(&self, prices: &DashMap<String, f64>) -> f64 {
        let cash = *self.cash.lock();
        let position_value: f64 = self.positions
            .iter()
            .filter_map(|entry| {
                let position = entry.value();
                prices.get(&position.symbol).map(|p| {
                    *p * position.quantity.abs() as f64
                })
            })
            .sum();

        cash + position_value
    }
}
```

**Memory Budget**
- 10 positions × 128 bytes = 1.28 KB
- 100 orders × 256 bytes = 25.6 KB
- Total: ~27 KB

### 2.5 Feature Cache

**Recent Features for Signal Generation**
```rust
use std::collections::VecDeque;

/// Cache of computed features
#[repr(align(64))] // Cache line alignment
pub struct FeatureCache {
    /// Symbol identifier
    symbol: String,

    /// Sliding window of features
    features: VecDeque<FeatureVector>,

    /// Window size (e.g., 60 seconds)
    window_size: usize,
}

#[derive(Clone)]
pub struct FeatureVector {
    pub timestamp: i64,
    pub rsi_14: f64,
    pub macd: f64,
    pub macd_signal: f64,
    pub bb_upper: f64,
    pub bb_lower: f64,
    pub volume_ratio: f64,
    pub order_book_imbalance: f64,
}

impl FeatureCache {
    /// Add new feature vector
    pub fn push(&mut self, features: FeatureVector) {
        if self.features.len() >= self.window_size {
            self.features.pop_front();
        }
        self.features.push_back(features);
    }

    /// Get features for model input
    pub fn get_window(&self, n: usize) -> Vec<FeatureVector> {
        self.features
            .iter()
            .rev()
            .take(n)
            .cloned()
            .collect()
    }
}
```

**Memory Budget**
- 10 symbols × 60s window × 8 features × 8 bytes = 38.4 KB
- Negligible compared to trade buffers

### 2.6 Total Hot Memory Budget

| Component | Memory per Symbol | 10 Symbols Total |
|-----------|-------------------|------------------|
| Order Book | 128 B | 1.28 KB |
| Trade Buffer (60s) | 5.76 MB | 57.6 MB |
| Quote Buffer (60s) | 6.72 MB | 67.2 MB |
| Feature Cache | 3.84 KB | 38.4 KB |
| **Total** | **~12.5 MB** | **~125 MB** |

Add 100 MB for runtime, total: **~225 MB in-memory**

## 3. Warm Path Storage (Local SSD)

### 3.1 Parquet File Format

**Why Parquet?**
- Columnar storage (efficient compression)
- Fast query performance
- Schema evolution support
- Industry standard for financial data

**Write Strategy**
- Buffer events in memory
- Flush to Parquet every 5 minutes
- Partition by date and symbol

### 3.2 Directory Structure

```
data/
  warm/
    trades/
      date=2025-10-14/
        symbol=AAPL/
          part-000.parquet  # 14:00-14:05
          part-001.parquet  # 14:05-14:10
          ...
        symbol=SPY/
          part-000.parquet
          ...
    quotes/
      date=2025-10-14/
        symbol=AAPL/
          part-000.parquet
        symbol=SPY/
          part-000.parquet
    bars/
      timeframe=1m/
        date=2025-10-14/
          symbol=AAPL/
            part-000.parquet
      timeframe=5m/
        date=2025-10-14/
          symbol=AAPL/
            part-000.parquet
```

### 3.3 Parquet Schema

**Trade Schema**
```rust
use parquet::{
    schema::types::Type,
    basic::Repetition,
};

pub fn trade_schema() -> Type {
    Type::group_type_builder("Trade")
        .with_fields(&mut vec![
            Arc::new(
                Type::primitive_type_builder("timestamp", PhysicalType::INT64)
                    .with_repetition(Repetition::REQUIRED)
                    .with_logical_type(Some(LogicalType::Timestamp {
                        is_adjusted_to_u_t_c: true,
                        unit: TimeUnit::NANOS(Default::default()),
                    }))
                    .build().unwrap()
            ),
            Arc::new(
                Type::primitive_type_builder("symbol", PhysicalType::BYTE_ARRAY)
                    .with_repetition(Repetition::REQUIRED)
                    .with_logical_type(Some(LogicalType::String))
                    .build().unwrap()
            ),
            Arc::new(
                Type::primitive_type_builder("trade_id", PhysicalType::INT64)
                    .with_repetition(Repetition::REQUIRED)
                    .build().unwrap()
            ),
            Arc::new(
                Type::primitive_type_builder("price", PhysicalType::DOUBLE)
                    .with_repetition(Repetition::REQUIRED)
                    .build().unwrap()
            ),
            Arc::new(
                Type::primitive_type_builder("size", PhysicalType::INT32)
                    .with_repetition(Repetition::REQUIRED)
                    .build().unwrap()
            ),
            Arc::new(
                Type::primitive_type_builder("exchange", PhysicalType::BYTE_ARRAY)
                    .with_repetition(Repetition::REQUIRED)
                    .with_logical_type(Some(LogicalType::String))
                    .build().unwrap()
            ),
        ])
        .build().unwrap()
}
```

### 3.4 Writer Implementation

```rust
use parquet::file::writer::SerializedFileWriter;
use parquet::record::RecordWriter;
use std::sync::Arc;

pub struct ParquetTradeWriter {
    writer: SerializedFileWriter<File>,
    buffer: Vec<Trade>,
    buffer_size: usize,
}

impl ParquetTradeWriter {
    pub fn new(path: &Path, buffer_size: usize) -> Result<Self> {
        let file = File::create(path)?;
        let schema = Arc::new(trade_schema());
        let props = Arc::new(
            WriterProperties::builder()
                .set_compression(Compression::SNAPPY)
                .set_dictionary_enabled(true)
                .build()
        );

        let writer = SerializedFileWriter::new(file, schema, props)?;

        Ok(Self {
            writer,
            buffer: Vec::with_capacity(buffer_size),
            buffer_size,
        })
    }

    pub fn write(&mut self, trade: Trade) -> Result<()> {
        self.buffer.push(trade);

        if self.buffer.len() >= self.buffer_size {
            self.flush()?;
        }

        Ok(())
    }

    pub fn flush(&mut self) -> Result<()> {
        if self.buffer.is_empty() {
            return Ok(());
        }

        let mut row_group = self.writer.next_row_group()?;

        // Write timestamp column
        let timestamps: Vec<i64> = self.buffer
            .iter()
            .map(|t| t.timestamp.timestamp_nanos())
            .collect();
        row_group.get_column_writer(0)?.write_batch(&timestamps, None, None)?;

        // Write other columns similarly...

        row_group.close()?;
        self.buffer.clear();

        Ok(())
    }

    pub fn close(mut self) -> Result<()> {
        self.flush()?;
        self.writer.close()?;
        Ok(())
    }
}
```

### 3.5 Compression and Size Estimates

**Compression Ratios (Snappy)**
- Trades: 4:1 (96 bytes → 24 bytes)
- Quotes: 5:1 (112 bytes → 22 bytes)
- Bars: 3:1 (88 bytes → 29 bytes)

**Daily Storage Estimates (10 symbols)**
- Trades: 10M trades × 24 bytes = 240 MB
- Quotes: 20M quotes × 22 bytes = 440 MB
- Bars (1m): 3,900 bars × 29 bytes = 113 KB
- **Total per day: ~680 MB**

### 3.6 Retention Policy

**Warm Storage Retention**
- Keep last 7 days on SSD
- Total: 680 MB × 7 = ~4.76 GB
- Auto-cleanup older than 7 days

**Implementation**
```rust
use std::time::{SystemTime, UNIX_EPOCH, Duration};
use std::fs;

pub fn cleanup_old_files(data_dir: &Path, retention_days: u64) -> Result<()> {
    let cutoff = SystemTime::now() - Duration::from_secs(retention_days * 86400);
    let cutoff_timestamp = cutoff.duration_since(UNIX_EPOCH)?.as_secs();

    for entry in fs::read_dir(data_dir)? {
        let entry = entry?;
        let metadata = entry.metadata()?;

        if metadata.is_file() {
            let modified = metadata.modified()?;
            let modified_timestamp = modified.duration_since(UNIX_EPOCH)?.as_secs();

            if modified_timestamp < cutoff_timestamp {
                fs::remove_file(entry.path())?;
                tracing::info!("Deleted old file: {:?}", entry.path());
            }
        }
    }

    Ok(())
}
```

## 4. Cold Path Storage (Archive)

### 4.1 Archive Strategy

**Purpose**
- Long-term backtesting data
- Regulatory compliance (if needed)
- Historical analysis

**Format**
- Parquet with Snappy compression
- Monthly partitions
- Deduplicated and validated

### 4.2 Directory Structure

```
data/
  cold/
    trades/
      year=2024/
        month=01/
          AAPL.parquet
          SPY.parquet
          ...
        month=02/
          AAPL.parquet
          ...
    bars/
      timeframe=1d/
        year=2024/
          AAPL.parquet  # All 2024 daily bars
          SPY.parquet
      timeframe=1m/
        year=2024/
          month=01/
            AAPL.parquet
```

### 4.3 Archival Process

**Monthly Archive Job**
```rust
pub async fn archive_month(
    warm_dir: &Path,
    cold_dir: &Path,
    year: u32,
    month: u32,
) -> Result<()> {
    // 1. Read all daily files for the month
    let mut monthly_trades = Vec::new();

    for day in 1..=31 {
        let date = format!("{:04}-{:02}-{:02}", year, month, day);
        let day_path = warm_dir.join(format!("date={}/", date));

        if !day_path.exists() {
            continue;
        }

        // Read all symbols for this day
        for symbol_dir in fs::read_dir(day_path)? {
            let trades = read_parquet_trades(symbol_dir?.path())?;
            monthly_trades.extend(trades);
        }
    }

    // 2. Sort by timestamp
    monthly_trades.sort_by_key(|t| t.timestamp);

    // 3. Deduplicate by trade_id
    monthly_trades.dedup_by_key(|t| t.trade_id);

    // 4. Group by symbol
    let mut by_symbol: HashMap<String, Vec<Trade>> = HashMap::new();
    for trade in monthly_trades {
        by_symbol.entry(trade.symbol.clone())
            .or_default()
            .push(trade);
    }

    // 5. Write monthly files
    for (symbol, trades) in by_symbol {
        let output_path = cold_dir.join(format!(
            "year={}/month={:02}/{}.parquet",
            year, month, symbol
        ));

        fs::create_dir_all(output_path.parent().unwrap())?;

        let mut writer = ParquetTradeWriter::new(&output_path, 10000)?;
        for trade in trades {
            writer.write(trade)?;
        }
        writer.close()?;
    }

    tracing::info!("Archived {}/{} to cold storage", year, month);
    Ok(())
}
```

### 4.4 Cold Storage Optimization

**Dictionary Encoding**
- Symbol names (repeated strings)
- Exchange codes
- Condition codes

**Delta Encoding**
- Timestamps (sequential)
- Prices (small changes)

**Run-Length Encoding**
- Repeated values in sorted data

**Size Reduction**
- Raw: 96 bytes/trade
- Warm (Snappy): 24 bytes/trade (4:1)
- Cold (Snappy + optimization): ~15 bytes/trade (6.4:1)

**Annual Storage (10 symbols)**
- 2.5B trades/year × 15 bytes = 37.5 GB/year

## 5. Query Optimization

### 5.1 Read Patterns

**Pattern 1: Recent Trades (Hot)**
```rust
// From in-memory ring buffer
let trades = trade_buffer.recent_trades(100);
```

**Pattern 2: Intraday History (Warm)**
```rust
use polars::prelude::*;

pub fn query_trades(
    symbol: &str,
    start: DateTime<Utc>,
    end: DateTime<Utc>,
) -> Result<Vec<Trade>> {
    let path = format!("data/warm/trades/date={}/symbol={}/",
        start.format("%Y-%m-%d"), symbol);

    let df = LazyFrame::scan_parquet(path, Default::default())?
        .filter(
            col("timestamp")
                .gt_eq(lit(start.timestamp_nanos()))
                .and(col("timestamp").lt(lit(end.timestamp_nanos())))
        )
        .collect()?;

    // Convert DataFrame to Vec<Trade>
    parse_trades_from_df(df)
}
```

**Pattern 3: Historical Backtest (Cold)**
```rust
pub fn query_monthly_bars(
    symbol: &str,
    year: u32,
    month: u32,
) -> Result<Vec<Bar>> {
    let path = format!(
        "data/cold/bars/timeframe=1d/year={}/month={:02}/{}.parquet",
        year, month, symbol
    );

    let df = LazyFrame::scan_parquet(path, Default::default())?
        .collect()?;

    parse_bars_from_df(df)
}
```

### 5.2 Indexing Strategy

**Partitioning Keys**
- Date (for time-series queries)
- Symbol (for per-ticker queries)

**Sort Order**
- Primary: Timestamp ascending
- Secondary: Symbol

**Bloom Filters**
- Enable for symbol column
- Reduces I/O for symbol lookups

## 6. Backup and Disaster Recovery

### 6.1 Backup Strategy

**Hot Data**
- Snapshot every 5 minutes
- Keep last 12 snapshots (1 hour)
- Store in warm storage

**Warm Data**
- Already persisted to disk
- RAID mirror or cloud sync

**Cold Data**
- Replicate to S3/GCS monthly
- 3-2-1 rule: 3 copies, 2 media, 1 offsite

### 6.2 Recovery Procedures

**Scenario 1: Process Crash**
- Restore from latest snapshot
- Replay events from warm storage
- Resume from last checkpoint

**Scenario 2: Data Corruption**
- Validate with checksums
- Restore from previous snapshot
- Reprocess from source (Alpaca API)

**Scenario 3: Disk Failure**
- Fail over to RAID mirror
- Restore cold data from cloud
- No data loss (all persisted)

## 7. Performance Benchmarks

### 7.1 Write Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Hot write (in-memory) | <1μs | 1M ops/sec |
| Warm write (buffered) | ~5μs | 200K ops/sec |
| Parquet flush | ~100ms | 100K rows/flush |

### 7.2 Read Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Hot read (order book) | <1μs | Lock-free read |
| Warm read (1 day) | ~10ms | Parquet scan |
| Cold read (1 month) | ~100ms | Compressed |

### 7.3 Compression Benchmarks

| Format | Compression Ratio | Decompress Speed |
|--------|-------------------|------------------|
| Snappy | 4:1 | 500 MB/s |
| Zstd (level 3) | 6:1 | 400 MB/s |
| LZ4 | 3:1 | 800 MB/s |

**Choice: Snappy** for balance of speed and compression

## 8. Monitoring and Maintenance

### 8.1 Storage Metrics

```rust
metrics::gauge!("storage.hot_memory_mb").set(hot_memory_mb);
metrics::gauge!("storage.warm_disk_gb").set(warm_disk_gb);
metrics::gauge!("storage.cold_disk_gb").set(cold_disk_gb);

metrics::counter!("storage.parquet_writes").increment(1);
metrics::histogram!("storage.parquet_write_us").record(elapsed_micros);
```

### 8.2 Health Checks

**Disk Space**
```rust
pub fn check_disk_space(path: &Path) -> Result<f64> {
    let stats = fs::metadata(path)?;
    let available = stats.len() as f64 / 1024.0 / 1024.0 / 1024.0; // GB

    if available < 10.0 {
        tracing::warn!("Low disk space: {:.2} GB remaining", available);
    }

    Ok(available)
}
```

**Data Integrity**
```rust
pub fn validate_parquet_file(path: &Path) -> Result<bool> {
    let file = File::open(path)?;
    let reader = SerializedFileReader::new(file)?;

    // Check row count matches metadata
    let metadata = reader.metadata();
    let row_count: i64 = metadata.row_groups()
        .iter()
        .map(|rg| rg.num_rows())
        .sum();

    Ok(row_count > 0)
}
```

## 9. Future Enhancements

### 9.1 Potential Optimizations

1. **Shared Memory IPC**: Use `shared_memory` crate for zero-copy between processes
2. **Memory-Mapped Files**: Use `memmap2` for warm data access
3. **GPU Acceleration**: Use `cudf` for fast Parquet queries
4. **Time-Series Database**: Consider TimescaleDB for queries

### 9.2 Scalability Considerations

**Beyond 10 Symbols**
- Implement LRU eviction for hot cache
- Shard data across multiple disks
- Use distributed storage (HDFS, S3)

**High-Frequency Data**
- Increase buffer sizes proportionally
- More aggressive compression
- Sample historical data (1% tick data)

## Summary

This storage strategy provides:
- **Sub-microsecond** hot path latency
- **~225 MB** total memory footprint
- **~680 MB/day** warm storage
- **~37 GB/year** cold storage
- **Zero data loss** with proper backups
- **Efficient queries** for backtesting

The architecture scales from development (10 symbols) to production (1000+ symbols) with minimal changes.

## References

- Parquet Format: https://parquet.apache.org/
- Polars DataFrame: https://pola.rs/
- DashMap: https://docs.rs/dashmap/
- Crossbeam: https://docs.rs/crossbeam/
