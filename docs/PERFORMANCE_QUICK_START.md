# Performance Optimization - Quick Start Guide

## 🎯 Goal
Achieve sub-100μs latency for critical trading paths

## 📊 Current Status vs Target

| Metric | Current (Estimated) | Target | Status |
|--------|-------------------|--------|--------|
| WebSocket Processing | 200-500μs | <50μs | ❌ |
| Order Book Update | 10-50μs | <10μs | ⚠️ |
| Risk Check | 5-20μs | <5μs | ⚠️ |
| Message Serialization | 20-100μs | <10μs | ❌ |
| **Total Critical Path** | **235-670μs** | **<100μs** | ❌ |

## 🚀 Quick Wins (Implement First)

### 1. Update Cargo.toml (5 minutes)
```bash
# Edit rust/Cargo.toml
[profile.release]
opt-level = 3
lto = "thin"        # Change to "fat" for production
codegen-units = 1
strip = true
panic = "abort"     # ADD THIS
overflow-checks = false  # ADD THIS
```

### 2. Add Performance Dependencies (10 minutes)
```toml
# Add to rust/Cargo.toml [workspace.dependencies]
bincode = "1.3"
simd-json = "0.13"
parking_lot = "0.12"
crossbeam-channel = "0.5"
ahash = "0.8"
```

### 3. Build with CPU Optimizations (2 minutes)
```bash
cd rust
RUSTFLAGS="-C target-cpu=native" cargo build --release
```

**Expected Gain**: 30-50% improvement (immediate)

---

## 🎯 High-Priority Optimizations

### Priority 1: Order Book BTreeMap (1-2 hours)
**Impact**: 5-10x faster updates
**File**: `/rust/market-data/src/orderbook.rs`
**Details**: See `/docs/CODE_OPTIMIZATION_EXAMPLES.md` Section 1

```bash
# After implementing, test with:
cargo test --package market-data --lib orderbook::tests::test_btree_orderbook_performance
```

### Priority 2: Bincode Serialization (30 minutes)
**Impact**: 3-5x faster serialization
**File**: `/rust/common/src/messaging.rs`
**Details**: See `/docs/CODE_OPTIMIZATION_EXAMPLES.md` Section 2

```bash
# After implementing, test with:
cargo test --package common --lib messaging::tests::test_bincode_performance
```

### Priority 3: SIMD JSON Parsing (1 hour)
**Impact**: 2-3x faster parsing
**File**: `/rust/market-data/src/websocket.rs`
**Details**: See `/docs/CODE_OPTIMIZATION_EXAMPLES.md` Section 3

```bash
# After implementing, test with:
cargo test --package market-data --lib websocket::bench::compare_json_parsers
```

---

## 📈 Implementation Roadmap

### Week 1: Foundation (Expected 3-5x gain)
- [x] Update Cargo.toml with optimization flags
- [ ] Replace order book BinaryHeap with BTreeMap
- [ ] Switch message serialization to Bincode
- [ ] Build with CPU-native flags
- [ ] Run baseline benchmarks

**Estimated Result**: 70-150μs critical path latency

### Week 2: Advanced (Expected 5-8x gain)
- [ ] Implement SIMD JSON parsing
- [ ] Add atomic operations to risk manager
- [ ] Implement rate limiter fast path
- [ ] Add connection pooling optimizations
- [ ] Create comprehensive benchmark suite

**Estimated Result**: 48-108μs critical path latency

### Week 3: Expert (Expected 8-12x gain)
- [ ] Profile-guided optimization (PGO)
- [ ] Object pooling for allocations
- [ ] Lock-free data structures
- [ ] Thread affinity tuning
- [ ] Custom allocator (jemalloc)

**Estimated Result**: 38-88μs critical path latency ✅ **MEETS TARGET**

---

## 🛠️ Build Commands

### Quick Build
```bash
cd rust
cargo build --release
```

### Optimized Build
```bash
cd rust
RUSTFLAGS="-C target-cpu=native -C link-arg=-fuse-ld=lld" \
cargo build --release
```

### PGO Build (Best Performance)
```bash
./scripts/build_optimized.sh pgo
```

### Run Benchmarks
```bash
cargo bench
```

---

## 📊 Benchmarking

### Current Benchmarks
```bash
cd rust
cargo bench --bench orderbook_bench
```

### Add New Benchmarks
Create files in `/rust/benches/`:
- `orderbook_bench.rs` ✅ Exists
- `risk_check_bench.rs` (TODO)
- `websocket_bench.rs` (TODO)
- `serialization_bench.rs` (TODO)

### Benchmark Template
```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_my_function(c: &mut Criterion) {
    c.bench_function("my_function", |b| {
        b.iter(|| {
            // Code to benchmark
            my_function(black_box(input))
        });
    });
}

criterion_group!(benches, bench_my_function);
criterion_main!(benches);
```

---

## 🔍 Profiling

### CPU Profiling (Linux)
```bash
# Build with debug symbols
cargo build --release

# Profile
perf record -g ./target/release/market-data
perf report
```

### Flamegraph
```bash
cargo install flamegraph
cargo flamegraph --release
```

### Memory Profiling
```bash
valgrind --tool=massif ./target/release/market-data
ms_print massif.out.<pid>
```

---

## 📝 Performance Checklist

### Before Optimization
- [ ] Run baseline benchmarks
- [ ] Record current latency numbers
- [ ] Identify top 3 bottlenecks
- [ ] Set clear performance targets

### During Optimization
- [ ] Implement one optimization at a time
- [ ] Benchmark after each change
- [ ] Verify correctness with tests
- [ ] Document performance gains

### After Optimization
- [ ] Run full benchmark suite
- [ ] Compare against baseline
- [ ] Update documentation
- [ ] Deploy to staging environment

---

## 🚨 Common Pitfalls

### ❌ Don't
- Over-optimize without profiling
- Disable safety checks without testing
- Use unsafe code without careful review
- Optimize for benchmarks that don't match production

### ✅ Do
- Profile first, optimize second
- Measure every change
- Test thoroughly
- Document trade-offs

---

## 📚 Reference Documentation

1. **Full Analysis**: `/docs/PERFORMANCE_ANALYSIS.md`
   - Comprehensive bottleneck analysis
   - Expected improvements per optimization
   - Risk assessment

2. **Code Examples**: `/docs/CODE_OPTIMIZATION_EXAMPLES.md`
   - Production-ready optimized code
   - Drop-in replacements
   - Benchmark comparisons

3. **Cargo Config**: `/docs/OPTIMIZED_CARGO_CONFIG.md`
   - Complete Cargo.toml updates
   - Build configuration
   - Platform-specific flags

4. **Build Script**: `/scripts/build_optimized.sh`
   - Automated optimized builds
   - PGO support
   - Platform detection

---

## 🎓 Learning Resources

### Rust Performance
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/)
- [Criterion.rs Guide](https://bheisler.github.io/criterion.rs/book/)
- [Benchmarking in Rust](https://doc.rust-lang.org/unstable-book/library-features/test.html)

### Low-Latency Trading
- [High-Frequency Trading with Rust](https://www.janestreet.com/tech-talks/building-low-latency-systems/)
- [Lock-Free Programming](https://preshing.com/20120612/an-introduction-to-lock-free-programming/)
- [CPU Cache Effects](https://igoro.com/archive/gallery-of-processor-cache-effects/)

---

## 💡 Quick Tips

1. **Always benchmark** - Don't guess, measure
2. **Profile in production mode** - Debug builds are 10-100x slower
3. **Hot path first** - Optimize the 1% that matters
4. **Lock-free when possible** - Avoid contention on critical paths
5. **Pre-allocate memory** - Avoid allocations in hot loops
6. **SIMD when beneficial** - 2-4x speedup for parallel operations
7. **Cache-friendly data** - Compact, aligned, sequential
8. **Minimize copies** - Use references and zero-copy techniques

---

## 🎯 Success Metrics

### Code Metrics
- Order book update: <10μs (p99)
- Risk check: <5μs (p99)
- Message serialization: <10μs (p99)
- WebSocket parsing: <50μs (p99)

### System Metrics
- Total critical path: <100μs (p99)
- Throughput: >10,000 orders/sec
- Memory usage: <500MB RSS
- CPU usage: <50% per core

---

## 🚀 Getting Started (Right Now!)

1. **Read this file** ✅ You're here
2. **Update Cargo.toml** (5 min)
   ```bash
   # Edit rust/Cargo.toml and add panic="abort", overflow-checks=false
   ```
3. **Build optimized** (2 min)
   ```bash
   cd rust
   RUSTFLAGS="-C target-cpu=native" cargo build --release
   ```
4. **Run benchmarks** (1 min)
   ```bash
   cargo bench
   ```
5. **Review results** and pick next optimization from roadmap

**Total time to first improvement: <10 minutes**

---

## 📞 Questions?

Refer to:
- Full analysis: `/docs/PERFORMANCE_ANALYSIS.md`
- Code examples: `/docs/CODE_OPTIMIZATION_EXAMPLES.md`
- Cargo guide: `/docs/OPTIMIZED_CARGO_CONFIG.md`

Happy optimizing! 🚀
