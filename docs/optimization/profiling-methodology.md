# Profiling Methodology
## Rust Algorithmic Trading System

**Document Version:** 1.0
**Last Updated:** 2025-10-14
**Agent:** Performance Analyzer

---

## Executive Summary

This document defines the systematic approach to profiling and identifying performance bottlenecks in the trading system. It covers CPU profiling, memory profiling, latency analysis, and production profiling techniques.

---

## 1. CPU Profiling

### 1.1 Flamegraph Generation

**Tool:** cargo-flamegraph

```bash
# Install flamegraph tool
cargo install flamegraph

# Profile entire application
sudo cargo flamegraph --bin trading-system

# Profile specific workload
sudo cargo flamegraph --bin trading-system -- --mode benchmark

# Profile tests
sudo cargo flamegraph --test integration_tests

# Open flamegraph.svg in browser
firefox flamegraph.svg
```

**Interpreting Flamegraphs:**
- **Wide bars:** High CPU time (optimization candidates)
- **Tall stacks:** Deep call chains (consider inlining)
- **Flat tops:** Leaf functions (hottest code paths)
- **Colors:** Random (no meaning, just for distinction)

### 1.2 perf (Linux Performance Monitoring)

```bash
# Record performance events
sudo perf record -g --call-graph dwarf \
    ./target/release/trading-system

# Generate report
sudo perf report

# Focus on specific events
sudo perf record -e cycles,instructions,cache-misses,branch-misses \
    ./target/release/trading-system

# Generate annotated source
sudo perf annotate --stdio
```

**Key Metrics to Monitor:**
- **IPC (Instructions Per Cycle):** Target >2.0 (good), <1.0 (bad)
- **Cache miss rate:** Target <5%
- **Branch misprediction rate:** Target <5%

### 1.3 Criterion Profiling Integration

```rust
// benches/profiled_bench.rs
use criterion::{criterion_group, criterion_main, Criterion};
use pprof::criterion::{Output, PProfProfiler};

fn bench_order_book_with_profiling(c: &mut Criterion) {
    c.bench_function("order_book_update", |b| {
        let mut book = OrderBook::new("AAPL");
        b.iter(|| {
            book.apply_update(&create_test_update());
        });
    });
}

criterion_group! {
    name = profiled_benches;
    config = Criterion::default().with_profiler(PProfProfiler::new(100, Output::Flamegraph(None)));
    targets = bench_order_book_with_profiling
}
criterion_main!(profiled_benches);
```

---

## 2. Memory Profiling

### 2.1 Valgrind Massif (Heap Profiling)

```bash
# Profile heap memory usage
valgrind --tool=massif \
    --massif-out-file=massif.out \
    ./target/release/trading-system

# Visualize memory usage over time
ms_print massif.out > massif_report.txt

# Interactive visualization
massif-visualizer massif.out
```

**Key Insights:**
- Peak memory usage
- Memory allocation hotspots
- Memory growth over time
- Allocation stack traces

### 2.2 heaptrack (Detailed Heap Profiling)

```bash
# Install heaptrack
sudo apt install heaptrack

# Profile application
heaptrack ./target/release/trading-system

# Analyze results
heaptrack_gui heaptrack.trading-system.*.gz
```

**Metrics:**
- Total allocations
- Peak memory usage
- Temporary allocations (candidates for pooling)
- Memory leaks

### 2.3 jemalloc Profiling

```toml
# Cargo.toml
[dependencies]
jemallocator = "0.5"
```

```rust
// main.rs
#[cfg(not(target_env = "msvc"))]
use jemallocator::Jemalloc;

#[cfg(not(target_env = "msvc"))]
#[global_allocator]
static GLOBAL: Jemalloc = Jemalloc;

fn main() {
    // Enable profiling
    if std::env::var("MALLOC_CONF").is_err() {
        std::env::set_var("MALLOC_CONF", "prof:true,prof_prefix:jeprof.out");
    }

    // Run application...
}
```

```bash
# Generate heap profile
MALLOC_CONF=prof:true,prof_prefix:jeprof.out ./target/release/trading-system

# Analyze with jeprof
jeprof --show_bytes ./target/release/trading-system jeprof.out.*.heap
```

---

## 3. Latency Profiling

### 3.1 HDR Histogram for Percentile Tracking

```rust
use hdrhistogram::Histogram;
use std::time::Instant;

/// Latency tracker with HDR histogram
pub struct LatencyTracker {
    histogram: Histogram<u64>,
    name: String,
}

impl LatencyTracker {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            histogram: Histogram::<u64>::new(3).unwrap(),  // 3 significant digits
            name: name.into(),
        }
    }

    /// Record single latency measurement
    pub fn record<F, R>(&mut self, f: F) -> R
    where
        F: FnOnce() -> R,
    {
        let start = Instant::now();
        let result = f();
        let elapsed = start.elapsed().as_nanos() as u64;

        self.histogram.record(elapsed).unwrap();
        result
    }

    /// Print percentile report
    pub fn report(&self) {
        println!("\n=== Latency Report: {} ===", self.name);
        println!("Count: {}", self.histogram.len());
        println!("Min: {} ns", self.histogram.min());
        println!("Max: {} ns", self.histogram.max());
        println!("Mean: {:.2} ns", self.histogram.mean());
        println!("StdDev: {:.2} ns", self.histogram.stdev());
        println!("\nPercentiles:");
        println!("  p50:   {} ns", self.histogram.value_at_quantile(0.50));
        println!("  p90:   {} ns", self.histogram.value_at_quantile(0.90));
        println!("  p95:   {} ns", self.histogram.value_at_quantile(0.95));
        println!("  p99:   {} ns", self.histogram.value_at_quantile(0.99));
        println!("  p99.9: {} ns", self.histogram.value_at_quantile(0.999));
        println!("  p99.99:{} ns", self.histogram.value_at_quantile(0.9999));
    }
}
```

### 3.2 Component-Level Latency Tracing

```rust
use tracing::{instrument, info_span};
use std::time::Instant;

#[instrument(skip(order))]
pub async fn process_order(order: Order) -> Result<OrderResponse, Error> {
    let span = info_span!("process_order", order_id = %order.id);
    let _enter = span.enter();

    // Track latency for each stage
    let t0 = Instant::now();
    let validated = validate_order(&order)?;
    let t1 = Instant::now();

    let risk_checked = check_risk(&validated)?;
    let t2 = Instant::now();

    let executed = execute_order(&risk_checked).await?;
    let t3 = Instant::now();

    // Log latency breakdown
    tracing::info!(
        validation_us = (t1 - t0).as_micros(),
        risk_check_us = (t2 - t1).as_micros(),
        execution_us = (t3 - t2).as_micros(),
        total_us = (t3 - t0).as_micros(),
        "Order processing complete"
    );

    Ok(executed)
}
```

### 3.3 Automated Latency Regression Detection

```rust
use criterion::{criterion_group, Criterion, BenchmarkId};

fn latency_regression_test(c: &mut Criterion) {
    let mut group = c.benchmark_group("latency_regression");

    // Set strict thresholds
    group.sample_size(1000);
    group.measurement_time(std::time::Duration::from_secs(10));

    // Define acceptable latency bounds
    let max_p99_us = 10.0;  // 10 microseconds

    group.bench_function("order_book_update", |b| {
        let mut book = OrderBook::new("AAPL");
        let update = create_test_update();

        b.iter(|| {
            book.apply_update(&update);
        });
    });

    group.finish();
}

criterion_group! {
    name = latency_benches;
    config = Criterion::default()
        .significance_level(0.05)
        .noise_threshold(0.05);
    targets = latency_regression_test
}
```

---

## 4. Cache Profiling

### 4.1 perf Cache Analysis

```bash
# Profile cache behavior
sudo perf stat -e cache-references,cache-misses,L1-dcache-loads,L1-dcache-load-misses \
    ./target/release/trading-system

# Expected output:
#   cache-references:     10,000,000  (total cache accesses)
#   cache-misses:            500,000  (5% miss rate - good)
#   L1-dcache-loads:       5,000,000
#   L1-dcache-load-misses:   100,000  (2% miss rate - good)
```

### 4.2 cachegrind (Detailed Cache Simulation)

```bash
# Run cache simulation
valgrind --tool=cachegrind \
    --cachegrind-out-file=cachegrind.out \
    ./target/release/trading-system

# Annotate source with cache statistics
cg_annotate cachegrind.out --auto=yes > cache_report.txt

# Focus on specific functions
cg_annotate cachegrind.out --show=src/order_book.rs
```

**Key Metrics:**
- **I1 miss rate:** Instruction cache (target <1%)
- **D1 miss rate:** L1 data cache (target <5%)
- **LL miss rate:** Last-level cache (target <1%)

---

## 5. System-Level Profiling

### 5.1 eBPF Tracing with bpftrace

```bash
# Install bpftrace
sudo apt install bpftrace

# Trace function calls
sudo bpftrace -e 'uprobe:/path/to/trading-system:order_book_update { @[tid] = count(); }'

# Measure function latency
sudo bpftrace -e '
    uprobe:/path/to/trading-system:order_book_update { @start[tid] = nsecs; }
    uretprobe:/path/to/trading-system:order_book_update /@start[tid]/ {
        @latency_us = hist((nsecs - @start[tid]) / 1000);
        delete(@start[tid]);
    }
'

# Monitor syscalls
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_* /comm == "trading-system"/ { @[probe] = count(); }'
```

### 5.2 strace for System Call Analysis

```bash
# Trace all syscalls with timing
strace -c ./target/release/trading-system

# Trace specific syscalls
strace -e trace=network,file ./target/release/trading-system

# Measure syscall latency
strace -T -e trace=all ./target/release/trading-system 2>&1 | grep "= 0"
```

---

## 6. Production Profiling (Low Overhead)

### 6.1 Continuous CPU Profiling

```rust
use pprof::ProfilerGuard;
use std::fs::File;

/// Continuous profiler with periodic snapshots
pub struct ContinuousProfiler {
    guard: Option<ProfilerGuard<'static>>,
}

impl ContinuousProfiler {
    pub fn start() -> Self {
        let guard = ProfilerGuard::new(100).ok();  // 100Hz sampling
        Self { guard }
    }

    /// Take snapshot and write to file
    pub fn snapshot(&self, path: &str) -> Result<(), Box<dyn std::error::Error>> {
        if let Some(guard) = &self.guard {
            let report = guard.report().build()?;
            let file = File::create(path)?;
            report.flamegraph(file)?;
        }
        Ok(())
    }
}

// Usage in main loop
#[tokio::main]
async fn main() {
    let profiler = ContinuousProfiler::start();

    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(60));
        loop {
            interval.tick().await;
            profiler.snapshot(&format!("profile_{}.svg", current_timestamp())).ok();
        }
    });

    // Run application...
}
```

### 6.2 Low-Overhead Metrics Collection

```rust
use metrics::{counter, histogram, gauge};
use metrics_exporter_prometheus::PrometheusBuilder;

/// Initialize metrics with minimal overhead
pub fn init_metrics() -> Result<(), Box<dyn std::error::Error>> {
    PrometheusBuilder::new()
        .with_http_listener("0.0.0.0:9090".parse()?)
        .idle_timeout(
            metrics_util::MetricKindMask::ALL,
            Some(Duration::from_secs(300))
        )
        .install()?;

    Ok(())
}

/// Lightweight instrumentation macro
#[macro_export]
macro_rules! measure {
    ($name:expr, $expr:expr) => {{
        let start = std::time::Instant::now();
        let result = $expr;
        let elapsed = start.elapsed().as_micros() as f64;
        metrics::histogram!($name).record(elapsed);
        result
    }};
}

// Usage
let order = measure!("order_validation_us", validate_order(&raw_order)?);
```

---

## 7. Profiling Workflow

### 7.1 Systematic Profiling Process

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ESTABLISH BASELINE                                       │
│    - Run benchmarks (cargo bench --all)                     │
│    - Record current latencies                               │
│    - Save flamegraph baseline                               │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. IDENTIFY HOTSPOTS                                        │
│    - Generate flamegraph (cargo flamegraph)                 │
│    - Run perf analysis (perf record + report)               │
│    - Check cache behavior (perf stat cache metrics)         │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DEEP DIVE INTO TOP 3 HOTSPOTS                            │
│    - Annotate source with perf                              │
│    - Profile memory allocations (heaptrack)                 │
│    - Analyze cache misses (cachegrind)                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. IMPLEMENT OPTIMIZATION                                   │
│    - Apply optimization technique                           │
│    - Write focused benchmark                                │
│    - Test correctness                                       │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. MEASURE IMPROVEMENT                                      │
│    - Run benchmarks (cargo bench)                           │
│    - Compare to baseline                                    │
│    - Generate new flamegraph                                │
│    - Calculate % improvement                                │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. ITERATE OR MOVE TO NEXT HOTSPOT                          │
│    - If improvement < 10%, revert                           │
│    - If improvement ≥ 10%, commit                           │
│    - Repeat from step 2                                     │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Profiling Checklist

**Before Optimization:**
- [ ] Baseline benchmarks recorded
- [ ] Flamegraph generated and analyzed
- [ ] Top 3 hotspots identified
- [ ] Cache behavior profiled
- [ ] Memory allocations profiled
- [ ] Test suite passing

**During Optimization:**
- [ ] Optimization approach documented
- [ ] Focused benchmark created
- [ ] Correctness tests written
- [ ] Edge cases considered

**After Optimization:**
- [ ] New benchmarks show ≥10% improvement
- [ ] All tests passing
- [ ] New flamegraph generated
- [ ] Memory usage unchanged or reduced
- [ ] Code reviewed

---

## 8. Common Profiling Pitfalls

### 8.1 Debug vs Release Builds

```bash
# ❌ WRONG: Profiling debug build (10x slower)
cargo build
./target/debug/trading-system

# ✅ CORRECT: Profile release build
cargo build --release
./target/release/trading-system

# ✅ BETTER: Profile with debug symbols
cargo build --profile release-with-debug
./target/release-with-debug/trading-system
```

### 8.2 Insufficient Sampling

```rust
// ❌ WRONG: Too few samples (high variance)
c.bench_function("test", |b| {
    b.iter(|| expensive_operation());
});

// ✅ CORRECT: Sufficient samples
c.bench_function("test", |b| {
    let mut group = c.benchmark_group("thorough");
    group.sample_size(1000);  // Minimum 1000 samples
    group.measurement_time(Duration::from_secs(10));

    group.bench_function("operation", |b| {
        b.iter(|| expensive_operation());
    });
});
```

### 8.3 Ignoring Tail Latencies

```rust
// ❌ WRONG: Only looking at average
println!("Average latency: {:.2} ms", histogram.mean() / 1_000_000.0);

// ✅ CORRECT: Track percentiles
println!("p50:   {:.2} ms", histogram.value_at_quantile(0.50) as f64 / 1_000_000.0);
println!("p95:   {:.2} ms", histogram.value_at_quantile(0.95) as f64 / 1_000_000.0);
println!("p99:   {:.2} ms", histogram.value_at_quantile(0.99) as f64 / 1_000_000.0);
println!("p99.9: {:.2} ms", histogram.value_at_quantile(0.999) as f64 / 1_000_000.0);
```

---

## 9. Profiling Tools Quick Reference

| Tool | Purpose | Command |
|------|---------|---------|
| **cargo-flamegraph** | CPU profiling | `cargo flamegraph` |
| **perf** | CPU, cache, branch | `perf record -g` |
| **valgrind massif** | Heap profiling | `valgrind --tool=massif` |
| **heaptrack** | Allocation tracking | `heaptrack ./binary` |
| **cachegrind** | Cache simulation | `valgrind --tool=cachegrind` |
| **criterion** | Microbenchmarks | `cargo bench` |
| **bpftrace** | System tracing | `bpftrace script.bt` |
| **strace** | Syscall tracing | `strace -c ./binary` |

---

## 10. Profiling Scripts

### 10.1 Automated Profiling Pipeline

```bash
#!/bin/bash
# scripts/profile_full.sh

set -e

echo "=== Full Profiling Pipeline ==="

# 1. Build optimized binary
echo "Building optimized binary..."
cargo build --release

# 2. CPU profiling
echo "Generating flamegraph..."
cargo flamegraph --bin trading-system -- --benchmark
mv flamegraph.svg profiles/cpu_flamegraph_$(date +%Y%m%d_%H%M%S).svg

# 3. Cache profiling
echo "Profiling cache behavior..."
valgrind --tool=cachegrind \
    --cachegrind-out-file=profiles/cachegrind.out \
    ./target/release/trading-system --benchmark
cg_annotate profiles/cachegrind.out > profiles/cache_report.txt

# 4. Memory profiling
echo "Profiling heap usage..."
heaptrack ./target/release/trading-system --benchmark
mv heaptrack.*.gz profiles/

# 5. Run benchmarks
echo "Running benchmarks..."
cargo bench --all > profiles/benchmark_results.txt

echo "=== Profiling Complete ==="
echo "Results saved to profiles/ directory"
```

---

## Summary

This profiling methodology provides a systematic approach to identifying and analyzing performance bottlenecks:

1. **CPU Profiling:** Flamegraphs and perf for hotspot identification
2. **Memory Profiling:** Valgrind, heaptrack for allocation analysis
3. **Latency Profiling:** HDR histograms for percentile tracking
4. **Cache Profiling:** Cachegrind for cache optimization
5. **Production Profiling:** Low-overhead continuous profiling

**Key Principles:**
- Always profile release builds
- Focus on percentiles (p95, p99), not just averages
- Profile with realistic workloads
- Measure before and after every optimization

**Next Steps:**
1. Follow profiling workflow systematically
2. Document findings in benchmark reports
3. Implement optimizations from performance-optimization-plan.md
4. Track progress in optimization-roadmap.md
