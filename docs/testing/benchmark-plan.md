# Performance Benchmark Plan
## Rust Algorithmic Trading System

**Document Version:** 1.0
**Last Updated:** 2025-10-14

---

## Executive Summary

This document outlines the performance benchmarking strategy for the algorithmic trading system. Benchmarks validate that latency and throughput requirements are met for production trading operations.

### Performance Targets

| Component              | Latency Target | Throughput Target     |
|------------------------|----------------|-----------------------|
| Order Book Update      | <10 μs         | 100,000 updates/sec   |
| Signal Calculation     | <100 μs        | 10,000 signals/sec    |
| Risk Check             | <50 μs         | 20,000 checks/sec     |
| Order Routing          | <500 μs        | 1,000 orders/sec      |
| End-to-End (Tick→Order)| <5 ms          | 200 round-trips/sec   |

---

## Table of Contents

1. [Benchmarking Framework](#benchmarking-framework)
2. [Component Benchmarks](#component-benchmarks)
3. [Integration Benchmarks](#integration-benchmarks)
4. [Latency Distribution Analysis](#latency-distribution-analysis)
5. [Throughput Testing](#throughput-testing)
6. [Memory & Resource Profiling](#memory--resource-profiling)
7. [Regression Detection](#regression-detection)
8. [Hardware Considerations](#hardware-considerations)

---

## Benchmarking Framework

### Tool: Criterion.rs

Primary benchmarking framework: [Criterion.rs](https://github.com/bheisler/criterion.rs)

**Benefits:**
- Statistical analysis of results
- Automatic outlier detection
- HTML reports with plots
- Comparison between runs
- Warm-up and sampling control

### Benchmark Structure

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};

fn configure_criterion() -> Criterion {
    Criterion::default()
        .sample_size(1000)           // Number of iterations
        .measurement_time(std::time::Duration::from_secs(10))
        .warm_up_time(std::time::Duration::from_secs(3))
        .noise_threshold(0.05)       // 5% noise tolerance
}

criterion_main!(benches);
```

---

## Component Benchmarks

### 1. Order Book Update Benchmark

**File:** `benches/order_book_bench.rs`

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion, BatchSize};
use trading_system::market_data::OrderBook;

fn bench_order_book_single_update(c: &mut Criterion) {
    c.bench_function("orderbook_single_update", |b| {
        b.iter_batched(
            || {
                let mut book = OrderBook::new("AAPL");
                let update = create_test_update();
                (book, update)
            },
            |(mut book, update)| {
                book.apply_update(black_box(&update))
            },
            BatchSize::SmallInput
        );
    });
}

fn bench_order_book_bulk_updates(c: &mut Criterion) {
    let mut group = c.benchmark_group("orderbook_bulk_updates");

    for size in [10, 100, 1000, 10000].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(size),
            size,
            |b, &size| {
                b.iter_batched(
                    || {
                        let mut book = OrderBook::new("AAPL");
                        let updates = create_test_updates(size);
                        (book, updates)
                    },
                    |(mut book, updates)| {
                        for update in updates {
                            book.apply_update(black_box(&update));
                        }
                    },
                    BatchSize::SmallInput
                );
            }
        );
    }
    group.finish();
}

fn bench_order_book_best_bid_ask(c: &mut Criterion) {
    c.bench_function("orderbook_best_bid_ask", |b| {
        let book = create_populated_order_book(100);
        b.iter(|| {
            (black_box(book.best_bid()), black_box(book.best_ask()))
        });
    });
}

criterion_group!(
    name = order_book_benches;
    config = configure_criterion();
    targets =
        bench_order_book_single_update,
        bench_order_book_bulk_updates,
        bench_order_book_best_bid_ask
);
```

**Expected Results:**
- Single update: 2-5 μs (avg 3 μs)
- Bulk 10,000 updates: 30-50 ms (3-5 μs per update)
- Best bid/ask retrieval: <100 ns

---

### 2. Signal Calculation Benchmark

**File:** `benches/signal_bench.rs`

```rust
use criterion::{black_box, criterion_group, Criterion};
use trading_system::signals::{SignalGenerator, FeatureSet};

fn bench_technical_indicators(c: &mut Criterion) {
    let mut group = c.benchmark_group("technical_indicators");

    // RSI calculation
    group.bench_function("rsi_14", |b| {
        let prices = generate_price_series(100);
        b.iter(|| {
            calculate_rsi(black_box(&prices), 14)
        });
    });

    // MACD calculation
    group.bench_function("macd_12_26_9", |b| {
        let prices = generate_price_series(100);
        b.iter(|| {
            calculate_macd(black_box(&prices), 12, 26, 9)
        });
    });

    // Bollinger Bands
    group.bench_function("bollinger_bands_20", |b| {
        let prices = generate_price_series(100);
        b.iter(|| {
            calculate_bollinger_bands(black_box(&prices), 20, 2.0)
        });
    });

    group.finish();
}

fn bench_microstructure_features(c: &mut Criterion) {
    let mut group = c.benchmark_group("microstructure_features");

    // Order book imbalance
    group.bench_function("order_book_imbalance", |b| {
        let book = create_populated_order_book(100);
        b.iter(|| {
            calculate_order_book_imbalance(black_box(&book), 10)
        });
    });

    // Trade flow toxicity
    group.bench_function("trade_flow_toxicity", |b| {
        let trades = generate_trade_sequence(1000);
        b.iter(|| {
            calculate_toxicity(black_box(&trades))
        });
    });

    group.finish();
}

fn bench_full_signal_generation(c: &mut Criterion) {
    c.bench_function("full_signal_pipeline", |b| {
        b.iter_batched(
            || {
                let market_data = create_market_data_snapshot();
                let generator = SignalGenerator::new();
                (market_data, generator)
            },
            |(market_data, mut generator)| {
                generator.generate_signal(black_box(&market_data))
            },
            BatchSize::SmallInput
        );
    });
}

criterion_group!(
    name = signal_benches;
    config = configure_criterion();
    targets =
        bench_technical_indicators,
        bench_microstructure_features,
        bench_full_signal_generation
);
```

**Expected Results:**
- RSI (14 period): 5-10 μs
- MACD: 10-15 μs
- Bollinger Bands: 8-12 μs
- Order book imbalance: 2-5 μs
- Full signal pipeline: 50-100 μs

---

### 3. Risk Check Benchmark

**File:** `benches/risk_bench.rs`

```rust
use criterion::{black_box, criterion_group, Criterion};
use trading_system::risk::{RiskManager, Order};

fn bench_position_limit_check(c: &mut Criterion) {
    c.bench_function("position_limit_check", |b| {
        let risk_manager = create_risk_manager_with_positions(5);
        let order = create_test_order("AAPL", 100);

        b.iter(|| {
            risk_manager.check_position_limits(black_box(&order))
        });
    });
}

fn bench_notional_exposure_check(c: &mut Criterion) {
    c.bench_function("notional_exposure_check", |b| {
        let risk_manager = create_risk_manager_with_positions(10);
        let order = create_test_order("SPY", 1000);

        b.iter(|| {
            risk_manager.check_notional_exposure(black_box(&order))
        });
    });
}

fn bench_pnl_calculation(c: &mut Criterion) {
    let mut group = c.benchmark_group("pnl_calculation");

    for num_positions in [1, 10, 100].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(num_positions),
            num_positions,
            |b, &num_positions| {
                let risk_manager = create_risk_manager_with_positions(num_positions);
                b.iter(|| {
                    risk_manager.calculate_total_pnl()
                });
            }
        );
    }

    group.finish();
}

fn bench_full_risk_check(c: &mut Criterion) {
    c.bench_function("full_risk_check", |b| {
        let risk_manager = create_risk_manager_with_positions(20);
        let order = create_test_order("AAPL", 100);

        b.iter(|| {
            risk_manager.validate_order(black_box(&order))
        });
    });
}

criterion_group!(
    name = risk_benches;
    config = configure_criterion();
    targets =
        bench_position_limit_check,
        bench_notional_exposure_check,
        bench_pnl_calculation,
        bench_full_risk_check
);
```

**Expected Results:**
- Position limit check: 1-2 μs
- Notional exposure check: 2-5 μs
- P&L calculation (10 positions): 5-10 μs
- Full risk check: 20-50 μs

---

### 4. Order Routing Benchmark

**File:** `benches/execution_bench.rs`

```rust
use criterion::{black_box, criterion_group, Criterion, BatchSize};
use trading_system::execution::{ExecutionEngine, MockExchange};

fn bench_order_serialization(c: &mut Criterion) {
    c.bench_function("order_serialization", |b| {
        let order = create_test_order("AAPL", 100);
        b.iter(|| {
            serde_json::to_string(black_box(&order))
        });
    });
}

fn bench_order_routing_no_network(c: &mut Criterion) {
    c.bench_function("order_routing_no_network", |b| {
        b.iter_batched(
            || {
                let engine = ExecutionEngine::new_with_mock();
                let order = create_test_order("AAPL", 100);
                (engine, order)
            },
            |(mut engine, order)| {
                engine.route_order(black_box(order))
            },
            BatchSize::SmallInput
        );
    });
}

fn bench_order_id_generation(c: &mut Criterion) {
    c.bench_function("order_id_generation", |b| {
        b.iter(|| {
            generate_unique_order_id()
        });
    });
}

criterion_group!(
    name = execution_benches;
    config = configure_criterion();
    targets =
        bench_order_serialization,
        bench_order_routing_no_network,
        bench_order_id_generation
);
```

**Expected Results:**
- Order serialization: 1-3 μs
- Order routing (no network): 10-50 μs
- Order ID generation: 50-200 ns

---

## Integration Benchmarks

### 5. End-to-End Latency

**File:** `benches/e2e_bench.rs`

```rust
use criterion::{black_box, criterion_group, Criterion};

fn bench_tick_to_signal(c: &mut Criterion) {
    c.bench_function("tick_to_signal", |b| {
        b.iter_batched(
            || {
                let pipeline = create_e2e_pipeline();
                let tick = generate_test_tick();
                (pipeline, tick)
            },
            |(mut pipeline, tick)| {
                pipeline.process_tick_to_signal(black_box(tick))
            },
            BatchSize::SmallInput
        );
    });
}

fn bench_signal_to_order(c: &mut Criterion) {
    c.bench_function("signal_to_order", |b| {
        b.iter_batched(
            || {
                let pipeline = create_e2e_pipeline();
                let signal = generate_test_signal();
                (pipeline, signal)
            },
            |(mut pipeline, signal)| {
                pipeline.process_signal_to_order(black_box(signal))
            },
            BatchSize::SmallInput
        );
    });
}

fn bench_full_e2e_pipeline(c: &mut Criterion) {
    c.bench_function("full_e2e_tick_to_order", |b| {
        b.iter_batched(
            || {
                let pipeline = create_e2e_pipeline();
                let tick = generate_test_tick();
                (pipeline, tick)
            },
            |(mut pipeline, tick)| {
                pipeline.process_tick_to_order(black_box(tick))
            },
            BatchSize::SmallInput
        );
    });
}

criterion_group!(
    name = e2e_benches;
    config = configure_criterion();
    targets =
        bench_tick_to_signal,
        bench_signal_to_order,
        bench_full_e2e_pipeline
);
```

**Expected Results:**
- Tick → Signal: 500-1000 μs
- Signal → Order (with risk): 200-500 μs
- Full end-to-end: 1-5 ms

---

## Latency Distribution Analysis

### Percentile Tracking

```rust
use criterion::Criterion;
use hdrhistogram::Histogram;

fn bench_with_histogram(c: &mut Criterion) {
    let mut histogram = Histogram::<u64>::new(3).unwrap();

    c.bench_function("component_with_histogram", |b| {
        b.iter_custom(|iters| {
            let mut total_duration = std::time::Duration::from_nanos(0);

            for _ in 0..iters {
                let start = std::time::Instant::now();
                // ... benchmark code ...
                let elapsed = start.elapsed();

                histogram.record(elapsed.as_nanos() as u64).unwrap();
                total_duration += elapsed;
            }

            total_duration
        });
    });

    // Report percentiles
    println!("p50: {} ns", histogram.value_at_quantile(0.50));
    println!("p95: {} ns", histogram.value_at_quantile(0.95));
    println!("p99: {} ns", histogram.value_at_quantile(0.99));
    println!("p99.9: {} ns", histogram.value_at_quantile(0.999));
    println!("max: {} ns", histogram.max());
}
```

### Target Percentiles

| Component        | p50   | p95   | p99   | p99.9 | p99.99 |
|------------------|-------|-------|-------|-------|--------|
| Order Book Update| 3 μs  | 8 μs  | 15 μs | 30 μs | 100 μs |
| Risk Check       | 20 μs | 40 μs | 60 μs | 100 μs| 200 μs |
| Signal Gen       | 80 μs | 150 μs| 250 μs| 500 μs| 1 ms   |
| End-to-End       | 3 ms  | 8 ms  | 15 ms | 30 ms | 100 ms |

---

## Throughput Testing

### Load Testing

**File:** `benches/throughput_bench.rs`

```rust
use std::sync::{Arc, atomic::{AtomicU64, Ordering}};
use std::time::{Duration, Instant};
use tokio::runtime::Runtime;

#[tokio::main]
async fn throughput_test_order_book_updates() {
    let updates_processed = Arc::new(AtomicU64::new(0));
    let duration = Duration::from_secs(10);

    let mut book = OrderBook::new("AAPL");
    let start = Instant::now();

    while start.elapsed() < duration {
        let update = generate_test_update();
        book.apply_update(&update);
        updates_processed.fetch_add(1, Ordering::Relaxed);
    }

    let total = updates_processed.load(Ordering::Relaxed);
    let throughput = total as f64 / duration.as_secs_f64();

    println!("Order book throughput: {:.0} updates/sec", throughput);
    assert!(throughput > 100_000.0, "Throughput below target");
}

#[tokio::main]
async fn throughput_test_concurrent_orders() {
    let num_workers = 4;
    let orders_per_worker = 10_000;

    let start = Instant::now();
    let mut handles = vec![];

    for _ in 0..num_workers {
        let handle = tokio::spawn(async move {
            let mut engine = ExecutionEngine::new_with_mock();
            for _ in 0..orders_per_worker {
                let order = create_test_order("AAPL", 100);
                engine.route_order(order).await.unwrap();
            }
        });
        handles.push(handle);
    }

    futures::future::join_all(handles).await;
    let elapsed = start.elapsed();

    let total_orders = num_workers * orders_per_worker;
    let throughput = total_orders as f64 / elapsed.as_secs_f64();

    println!("Order routing throughput: {:.0} orders/sec", throughput);
    assert!(throughput > 1_000.0, "Throughput below target");
}
```

---

## Memory & Resource Profiling

### Memory Benchmark

**File:** `benches/memory_bench.rs`

```rust
#[test]
fn memory_usage_order_book() {
    let initial = get_process_memory_usage();

    let mut books = Vec::new();
    for i in 0..100 {
        let mut book = OrderBook::new(&format!("SYM{}", i));
        // Populate with 1000 levels
        for j in 0..1000 {
            book.apply_update(&create_test_update());
        }
        books.push(book);
    }

    let final_memory = get_process_memory_usage();
    let memory_per_book = (final_memory - initial) / 100;

    println!("Memory per order book (1000 levels): {} KB", memory_per_book / 1024);
    assert!(memory_per_book < 1_000_000, "Memory usage > 1MB per book");
}

fn get_process_memory_usage() -> usize {
    // Platform-specific memory measurement
    #[cfg(target_os = "linux")]
    {
        use std::fs;
        let status = fs::read_to_string("/proc/self/status").unwrap();
        for line in status.lines() {
            if line.starts_with("VmRSS:") {
                let parts: Vec<&str> = line.split_whitespace().collect();
                return parts[1].parse::<usize>().unwrap() * 1024;
            }
        }
    }
    0
}
```

### CPU Profiling

```bash
# Using perf (Linux)
cargo bench -- --profile-time=5

# Using flamegraph
cargo install flamegraph
cargo flamegraph --bench order_book_bench

# Using valgrind/cachegrind
cargo build --release --bench
valgrind --tool=cachegrind ./target/release/deps/order_book_bench-*
```

---

## Regression Detection

### Baseline Comparison

```bash
# Save current performance as baseline
cargo bench -- --save-baseline master

# After changes, compare to baseline
cargo bench -- --baseline master

# Report differences
criterion-compare master current
```

### CI Integration

**`.github/workflows/benchmark.yml`:**

```yaml
name: Performance Benchmarks

on:
  pull_request:
    branches: [ main ]

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0

    - name: Install Rust
      uses: actions-rs/toolchain@v1
      with:
        toolchain: stable

    - name: Run benchmarks on PR
      run: cargo bench -- --save-baseline pr

    - name: Checkout main branch
      run: git checkout main

    - name: Run benchmarks on main
      run: cargo bench -- --save-baseline main

    - name: Compare results
      run: |
        cargo install cargo-criterion
        cargo criterion --message-format=json > comparison.json

    - name: Check for regression
      run: |
        python scripts/check_benchmark_regression.py comparison.json
```

**Regression Threshold:** Fail if any benchmark is >10% slower

---

## Hardware Considerations

### Target Hardware Specifications

**Development:**
- CPU: Intel i7/i9 or AMD Ryzen 7/9
- RAM: 16GB+
- Storage: NVMe SSD
- Network: 1Gbps+

**Production (Simulated):**
- CPU: Intel Xeon or AMD EPYC (server-grade)
- RAM: 64GB+
- Storage: NVMe RAID
- Network: 10Gbps+

### Platform-Specific Optimizations

```rust
// Cargo.toml
[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
panic = "abort"

[target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "target-cpu=native"]
```

---

## Benchmark Execution

### Running Benchmarks

```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench -- order_book

# Run with HTML report
cargo bench -- --verbose

# Run with increased sample size
cargo bench -- --sample-size 10000

# Save baseline
cargo bench -- --save-baseline baseline-2025-10-14

# Compare to baseline
cargo bench -- --baseline baseline-2025-10-14
```

### Continuous Monitoring

```bash
# Watch for changes and re-run benchmarks
cargo watch -x "bench -- order_book"

# Run benchmarks every hour
while true; do
    cargo bench
    sleep 3600
done
```

---

## Reporting

### HTML Reports

Criterion generates HTML reports in `target/criterion/`:

```
target/criterion/
  order_book_single_update/
    report/
      index.html         # Main report
      violin.svg         # Distribution visualization
      pdf.svg            # Probability density
      regression.svg     # Trend over time
```

### JSON Export

```rust
// Export results as JSON
use criterion::Criterion;

fn custom_criterion() -> Criterion {
    Criterion::default()
        .with_output_color(false)
        .with_plots()
        .save_json()
}
```

---

## Success Criteria

### Benchmark Pass Conditions

1. **All latency targets met** (see table in Executive Summary)
2. **No regression >5%** compared to baseline
3. **Throughput targets achieved** under load
4. **Memory usage <10% growth** per component
5. **p99 latency <2x p50** (reasonable tail behavior)

---

## Appendix: Benchmark Runner Script

**`scripts/run_benchmarks.sh`:**

```bash
#!/bin/bash

set -e

echo "========================================="
echo "Running Performance Benchmark Suite"
echo "========================================="

# Disable CPU frequency scaling for consistent results
echo "Setting CPU governor to performance..."
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Set process priority
echo "Setting high process priority..."
renice -n -10 $$

# Disable swap to prevent paging
echo "Disabling swap..."
sudo swapoff -a

# Run benchmarks
echo "Running benchmarks..."
RUSTFLAGS="-C target-cpu=native" cargo bench --all -- --verbose

# Re-enable swap
echo "Re-enabling swap..."
sudo swapon -a

# Reset CPU governor
echo "Resetting CPU governor..."
echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

echo "========================================="
echo "Benchmark suite complete!"
echo "View results: target/criterion/report/index.html"
echo "========================================="
```

---

**End of Performance Benchmark Plan**
