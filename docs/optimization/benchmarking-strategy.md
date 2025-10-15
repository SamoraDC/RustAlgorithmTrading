# Benchmarking Strategy
## Rust Algorithmic Trading System

**Document Version:** 1.0
**Last Updated:** 2025-10-14
**Agent:** Performance Analyzer

---

## Executive Summary

This document extends the benchmark plan with advanced benchmarking strategies, focusing on realistic workloads, regression prevention, and continuous performance monitoring. It complements the existing benchmark-plan.md with production-grade testing approaches.

---

## 1. Realistic Workload Simulation

### 1.1 Market Data Replay Benchmarks

**Problem:** Synthetic data doesn't capture real market behavior.

**Solution:** Replay historical market data for realistic benchmarks.

```rust
use std::fs::File;
use std::io::{BufReader, BufRead};

/// Benchmark with real historical data
pub struct MarketDataReplay {
    trades: Vec<Trade>,
    quotes: Vec<Quote>,
}

impl MarketDataReplay {
    /// Load historical data from CSV
    pub fn from_csv(path: &str) -> Result<Self, Error> {
        let file = File::open(path)?;
        let reader = BufReader::new(file);

        let mut trades = Vec::new();

        for line in reader.lines() {
            let line = line?;
            let trade = parse_trade_csv(&line)?;
            trades.push(trade);
        }

        Ok(Self { trades, quotes: Vec::new() })
    }

    /// Replay data at realistic rate
    pub async fn replay_with_timing(&self, mut handler: impl FnMut(&Trade)) {
        for window in self.trades.windows(2) {
            let curr = &window[0];
            let next = &window[1];

            handler(curr);

            // Sleep until next message (realistic timing)
            let delay = Duration::from_micros(
                (next.timestamp - curr.timestamp) as u64
            );
            tokio::time::sleep(delay).await;
        }
    }
}

/// Benchmark with historical replay
#[tokio::test]
async fn bench_realistic_market_data() {
    let replay = MarketDataReplay::from_csv("data/AAPL_20250114.csv").unwrap();
    let mut book = OrderBook::new("AAPL");

    let start = Instant::now();
    let mut count = 0;

    replay.replay_with_timing(|trade| {
        book.apply_trade(trade);
        count += 1;
    }).await;

    let elapsed = start.elapsed();
    let throughput = count as f64 / elapsed.as_secs_f64();

    println!("Processed {} trades in {:?}", count, elapsed);
    println!("Throughput: {:.0} trades/sec", throughput);

    assert!(throughput > 10_000.0, "Throughput below target");
}
```

### 1.2 Multi-Symbol Concurrent Benchmarks

```rust
use tokio::task;
use futures::future::join_all;

#[tokio::test]
async fn bench_multi_symbol_concurrent() {
    let symbols = vec!["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"];
    let trades_per_symbol = 10_000;

    let start = Instant::now();

    // Spawn concurrent tasks for each symbol
    let handles: Vec<_> = symbols.iter().map(|&symbol| {
        task::spawn(async move {
            let mut book = OrderBook::new(symbol);

            for _ in 0..trades_per_symbol {
                let trade = generate_realistic_trade(symbol);
                book.apply_trade(&trade);
            }
        })
    }).collect();

    // Wait for all tasks
    join_all(handles).await;

    let elapsed = start.elapsed();
    let total_trades = symbols.len() * trades_per_symbol;
    let throughput = total_trades as f64 / elapsed.as_secs_f64();

    println!("Multi-symbol throughput: {:.0} trades/sec", throughput);
    assert!(throughput > 50_000.0, "Multi-symbol throughput below target");
}
```

### 1.3 Stress Testing Under Load

```rust
/// Stress test with bursts and sustained load
#[tokio::test]
async fn stress_test_order_book() {
    let mut book = OrderBook::new("AAPL");
    let duration = Duration::from_secs(60);
    let start = Instant::now();

    let mut latencies = Histogram::<u64>::new(3).unwrap();

    while start.elapsed() < duration {
        // Simulate burst (100 updates)
        for _ in 0..100 {
            let t0 = Instant::now();
            let update = generate_random_update();
            book.apply_update(&update);
            latencies.record(t0.elapsed().as_nanos() as u64).unwrap();
        }

        // Brief pause
        tokio::time::sleep(Duration::from_millis(10)).await;
    }

    // Report stress test results
    println!("=== Stress Test Results ===");
    println!("Duration: 60s");
    println!("Total updates: {}", latencies.len());
    println!("p50:   {} ns", latencies.value_at_quantile(0.50));
    println!("p95:   {} ns", latencies.value_at_quantile(0.95));
    println!("p99:   {} ns", latencies.value_at_quantile(0.99));
    println!("p99.9: {} ns", latencies.value_at_quantile(0.999));
    println!("Max:   {} ns", latencies.max());

    // Verify performance under stress
    assert!(latencies.value_at_quantile(0.99) < 50_000, "p99 latency too high under stress");
}
```

---

## 2. Advanced Criterion Configuration

### 2.1 Custom Measurement Precision

```rust
use criterion::{
    Criterion, BenchmarkId, BatchSize, Throughput,
    measurement::WallTime, PlotConfiguration, AxisScale
};

fn configure_precise_criterion() -> Criterion {
    Criterion::default()
        .sample_size(2000)                                    // More samples
        .measurement_time(Duration::from_secs(20))            // Longer measurement
        .warm_up_time(Duration::from_secs(5))                 // Thorough warm-up
        .noise_threshold(0.03)                                // 3% noise tolerance
        .significance_level(0.01)                             // 99% confidence
        .confidence_level(0.99)
        .plotting_backend(PlotConfiguration::default())
}

/// Benchmark with throughput measurement
fn bench_with_throughput(c: &mut Criterion) {
    let mut group = c.benchmark_group("throughput_sensitive");
    group.throughput(Throughput::Elements(1));  // Per-element throughput

    for size in [100, 1000, 10000, 100000].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(size),
            size,
            |b, &size| {
                b.iter_batched(
                    || generate_test_data(size),
                    |data| process_batch(data),
                    BatchSize::SmallInput
                );
            }
        );
    }

    group.finish();
}
```

### 2.2 Comparative Benchmarks

```rust
/// Compare different implementations
fn bench_implementations_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("order_book_implementations");

    // Baseline: Mutex-based
    group.bench_function("mutex_based", |b| {
        let book = MutexOrderBook::new("AAPL");
        b.iter(|| book.apply_update(&create_test_update()));
    });

    // Optimized: Lock-free
    group.bench_function("lock_free", |b| {
        let book = LockFreeOrderBook::new("AAPL");
        b.iter(|| book.apply_update(&create_test_update()));
    });

    // Future: WASM SIMD
    group.bench_function("wasm_simd", |b| {
        let book = WasmSIMDOrderBook::new("AAPL");
        b.iter(|| book.apply_update(&create_test_update()));
    });

    group.finish();
}
```

---

## 3. Regression Prevention

### 3.1 Automated Performance Bounds

```rust
use assert2::assert;

#[test]
fn performance_bounds_order_book_update() {
    let mut book = OrderBook::new("AAPL");
    let update = create_test_update();

    let mut latencies = Vec::with_capacity(1000);

    for _ in 0..1000 {
        let start = Instant::now();
        book.apply_update(&update);
        latencies.push(start.elapsed().as_nanos());
    }

    latencies.sort_unstable();
    let p99 = latencies[990];

    // Enforce strict performance bounds
    assert!(p99 < 10_000, "p99 latency {} ns exceeds 10,000 ns bound", p99);
}

#[test]
fn memory_bounds_order_book() {
    let initial_mem = get_process_memory();

    let mut books = Vec::new();
    for i in 0..100 {
        let mut book = OrderBook::new(&format!("SYM{}", i));
        for _ in 0..1000 {
            book.apply_update(&create_test_update());
        }
        books.push(book);
    }

    let final_mem = get_process_memory();
    let memory_per_book = (final_mem - initial_mem) / 100;

    // Enforce memory bound: <1MB per order book
    assert!(memory_per_book < 1_000_000,
        "Memory per book: {} bytes exceeds 1MB limit", memory_per_book);
}
```

### 3.2 CI Performance Gates

```yaml
# .github/workflows/performance-gate.yml
name: Performance Gate

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
          profile: minimal

      - name: Run benchmarks on PR
        run: |
          cargo bench --all -- --save-baseline pr

      - name: Checkout main
        run: |
          git fetch origin main
          git checkout main

      - name: Run benchmarks on main
        run: |
          cargo bench --all -- --save-baseline main

      - name: Compare results
        run: |
          cargo install cargo-criterion
          cargo criterion --message-format=json > comparison.json

      - name: Check for regression
        run: |
          python scripts/check_performance_regression.py \
            --threshold 10 \
            --comparison comparison.json

      - name: Post results to PR
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = fs.readFileSync('comparison.json', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Performance Benchmark Results\n\n${results}`
            });
```

### 3.3 Performance Regression Detection Script

```python
#!/usr/bin/env python3
# scripts/check_performance_regression.py

import json
import sys
import argparse

def check_regression(comparison_file, threshold_percent):
    """Check for performance regressions"""
    with open(comparison_file) as f:
        data = json.load(f)

    regressions = []
    improvements = []

    for benchmark, results in data.items():
        baseline = results.get('baseline', {})
        current = results.get('current', {})

        if not baseline or not current:
            continue

        baseline_mean = baseline.get('mean', 0)
        current_mean = current.get('mean', 0)

        if baseline_mean == 0:
            continue

        change_percent = ((current_mean - baseline_mean) / baseline_mean) * 100

        if change_percent > threshold_percent:
            regressions.append({
                'name': benchmark,
                'baseline_us': baseline_mean / 1000,
                'current_us': current_mean / 1000,
                'change_percent': change_percent
            })
        elif change_percent < -threshold_percent:
            improvements.append({
                'name': benchmark,
                'baseline_us': baseline_mean / 1000,
                'current_us': current_mean / 1000,
                'change_percent': change_percent
            })

    # Print report
    print("=" * 80)
    print("PERFORMANCE BENCHMARK COMPARISON")
    print("=" * 80)

    if improvements:
        print("\n✅ IMPROVEMENTS:")
        for item in improvements:
            print(f"  {item['name']}")
            print(f"    Baseline: {item['baseline_us']:.2f} μs")
            print(f"    Current:  {item['current_us']:.2f} μs")
            print(f"    Change:   {item['change_percent']:.1f}%")

    if regressions:
        print("\n❌ REGRESSIONS:")
        for item in regressions:
            print(f"  {item['name']}")
            print(f"    Baseline: {item['baseline_us']:.2f} μs")
            print(f"    Current:  {item['current_us']:.2f} μs")
            print(f"    Change:   +{item['change_percent']:.1f}%")

        print(f"\n🚫 FAIL: {len(regressions)} benchmark(s) regressed by >{threshold_percent}%")
        sys.exit(1)
    else:
        print("\n✅ PASS: No performance regressions detected")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparison', required=True, help='Comparison JSON file')
    parser.add_argument('--threshold', type=float, default=10.0, help='Regression threshold %')
    args = parser.parse_args()

    check_regression(args.comparison, args.threshold)
```

---

## 4. Production Benchmarking

### 4.1 Shadow Traffic Testing

```rust
/// Run production workload against test system
pub struct ShadowTrafficBenchmark {
    production_log: File,
}

impl ShadowTrafficBenchmark {
    /// Replay production traffic
    pub async fn replay_production_traffic(&self) -> BenchmarkResults {
        let mut results = BenchmarkResults::new();

        let reader = BufReader::new(&self.production_log);

        for line in reader.lines() {
            let event: MarketEvent = serde_json::from_str(&line?)?;

            let start = Instant::now();
            process_event(&event).await?;
            let elapsed = start.elapsed();

            results.record(elapsed);
        }

        results
    }
}
```

### 4.2 Canary Deployment Benchmarking

```rust
/// Compare performance between versions
pub struct CanaryBenchmark {
    stable_version: SystemHandle,
    canary_version: SystemHandle,
}

impl CanaryBenchmark {
    pub async fn run_canary_test(&self, duration: Duration) -> ComparisonResults {
        let start = Instant::now();

        let (stable_metrics, canary_metrics) = tokio::join!(
            self.measure_version(&self.stable_version, duration),
            self.measure_version(&self.canary_version, duration)
        );

        ComparisonResults {
            stable_latency_p99: stable_metrics.latency_p99(),
            canary_latency_p99: canary_metrics.latency_p99(),
            stable_throughput: stable_metrics.throughput(),
            canary_throughput: canary_metrics.throughput(),
            stable_errors: stable_metrics.error_count(),
            canary_errors: canary_metrics.error_count(),
        }
    }

    async fn measure_version(&self, version: &SystemHandle, duration: Duration) -> Metrics {
        let mut metrics = Metrics::new();
        let start = Instant::now();

        while start.elapsed() < duration {
            let request = generate_test_request();
            let t0 = Instant::now();

            match version.process(&request).await {
                Ok(_) => metrics.record_success(t0.elapsed()),
                Err(_) => metrics.record_error(),
            }
        }

        metrics
    }
}
```

---

## 5. Percentile-Aware Benchmarking

### 5.1 Coordinated Omission Correction

```rust
use std::time::Duration;

/// Benchmark accounting for coordinated omission
pub struct CoordinatedOmissionBenchmark {
    target_rate: f64,  // Requests per second
    histogram: Histogram<u64>,
}

impl CoordinatedOmissionBenchmark {
    pub fn new(target_rate: f64) -> Self {
        Self {
            target_rate,
            histogram: Histogram::<u64>::new(3).unwrap(),
        }
    }

    pub async fn run(&mut self, operation: impl Fn() -> Result<(), Error>, duration: Duration) {
        let interval = Duration::from_secs_f64(1.0 / self.target_rate);
        let mut next_send = Instant::now();
        let end = next_send + duration;

        while Instant::now() < end {
            let send_time = Instant::now();

            // Record start time BEFORE operation
            let operation_start = Instant::now();
            let _ = operation();
            let operation_end = Instant::now();

            // Calculate actual latency
            let latency = (operation_end - operation_start).as_nanos() as u64;
            self.histogram.record(latency).unwrap();

            // If we're behind schedule, record missed intervals
            let now = Instant::now();
            if now > next_send {
                let missed_intervals = ((now - next_send).as_nanos() as f64
                    / interval.as_nanos() as f64) as u64;

                for _ in 0..missed_intervals {
                    // Record additional latency samples for missed sends
                    self.histogram.record(latency + interval.as_nanos() as u64).unwrap();
                }
            }

            // Wait until next send time
            next_send += interval;
            if let Some(sleep_duration) = next_send.checked_duration_since(Instant::now()) {
                tokio::time::sleep(sleep_duration).await;
            }
        }
    }

    pub fn report(&self) {
        println!("\n=== Coordinated Omission Corrected Results ===");
        println!("p50:   {:.2} μs", self.histogram.value_at_quantile(0.50) as f64 / 1000.0);
        println!("p90:   {:.2} μs", self.histogram.value_at_quantile(0.90) as f64 / 1000.0);
        println!("p95:   {:.2} μs", self.histogram.value_at_quantile(0.95) as f64 / 1000.0);
        println!("p99:   {:.2} μs", self.histogram.value_at_quantile(0.99) as f64 / 1000.0);
        println!("p99.9: {:.2} μs", self.histogram.value_at_quantile(0.999) as f64 / 1000.0);
    }
}
```

---

## 6. Component Isolation Benchmarks

### 6.1 Mocked Dependency Benchmarks

```rust
/// Benchmark order book in isolation (mocked network)
#[bench]
fn bench_order_book_isolated(b: &mut Bencher) {
    let mut book = OrderBook::new("AAPL");

    // No network calls, pure computation
    b.iter(|| {
        let update = create_test_update();  // Fast in-memory generation
        book.apply_update(black_box(&update));
    });
}

/// Benchmark with realistic network latency
#[tokio::test]
async fn bench_with_network_simulation() {
    let mut book = OrderBook::new("AAPL");
    let network_delay = Duration::from_micros(100);  // Simulated network

    let mut latencies = Vec::with_capacity(1000);

    for _ in 0..1000 {
        let start = Instant::now();

        // Simulate network delay
        tokio::time::sleep(network_delay).await;

        let update = create_test_update();
        book.apply_update(&update);

        latencies.push(start.elapsed().as_micros());
    }

    let avg = latencies.iter().sum::<u128>() / latencies.len() as u128;
    println!("Average latency with network: {} μs", avg);
}
```

---

## 7. Benchmarking Dashboard

### 7.1 Automated Report Generation

```rust
use std::fs::File;
use std::io::Write;

pub struct BenchmarkReport {
    results: Vec<BenchmarkResult>,
}

impl BenchmarkReport {
    pub fn generate_html(&self, output_path: &str) -> Result<(), Error> {
        let mut file = File::create(output_path)?;

        writeln!(file, "<!DOCTYPE html><html><head>")?;
        writeln!(file, "<title>Performance Benchmark Report</title>")?;
        writeln!(file, "<style>")?;
        writeln!(file, "table {{ border-collapse: collapse; width: 100%; }}")?;
        writeln!(file, "th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}")?;
        writeln!(file, "th {{ background-color: #4CAF50; color: white; }}")?;
        writeln!(file, ".regression {{ background-color: #ffcccc; }}")?;
        writeln!(file, ".improvement {{ background-color: #ccffcc; }}")?;
        writeln!(file, "</style></head><body>")?;

        writeln!(file, "<h1>Performance Benchmark Report</h1>")?;
        writeln!(file, "<p>Generated: {}</p>", chrono::Utc::now())?;

        writeln!(file, "<table>")?;
        writeln!(file, "<tr><th>Benchmark</th><th>Current</th><th>Baseline</th><th>Change</th></tr>")?;

        for result in &self.results {
            let row_class = if result.is_regression() {
                "regression"
            } else if result.is_improvement() {
                "improvement"
            } else {
                ""
            };

            writeln!(file, "<tr class='{}'>", row_class)?;
            writeln!(file, "<td>{}</td>", result.name)?;
            writeln!(file, "<td>{:.2} μs</td>", result.current_us)?;
            writeln!(file, "<td>{:.2} μs</td>", result.baseline_us)?;
            writeln!(file, "<td>{:+.1}%</td>", result.change_percent)?;
            writeln!(file, "</tr>")?;
        }

        writeln!(file, "</table></body></html>")?;

        Ok(())
    }
}
```

---

## 8. Summary

This benchmarking strategy provides comprehensive coverage:

1. **Realistic Workloads:** Historical data replay
2. **Regression Prevention:** Automated CI gates
3. **Production Testing:** Shadow traffic and canary deployments
4. **Percentile Tracking:** Coordinated omission correction
5. **Component Isolation:** Mocked dependencies

**Key Principles:**
- Benchmark with realistic data
- Track percentiles, not just averages
- Automate regression detection
- Test in production-like environments
- Isolate components for precise measurement

**Next Steps:**
1. Implement realistic workload benchmarks
2. Set up CI performance gates
3. Create automated reporting
4. Integrate with profiling-methodology.md
5. Track progress in optimization-roadmap.md
