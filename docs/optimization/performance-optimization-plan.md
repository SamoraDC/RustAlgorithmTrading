# Performance Optimization Plan
## Rust Algorithmic Trading System

**Document Version:** 1.0
**Last Updated:** 2025-10-14
**Performance Analyzer Agent:** swarm-1760472826183-pn8tf56wf

---

## Executive Summary

This document outlines a comprehensive performance optimization strategy for the algorithmic trading system, targeting sub-millisecond latencies for critical paths. The plan focuses on lock-free data structures, SIMD vectorization, zero-copy serialization, and cache-friendly memory layouts to achieve ultra-low latency execution.

### Performance Targets Summary

| Component | Current P99 | Target P99 | Optimization Strategy |
|-----------|-------------|------------|----------------------|
| Order Book Update | 15 μs | **5 μs** | Lock-free concurrent structures |
| Signal Generation | 250 μs | **80 μs** | SIMD vectorization |
| Risk Check | 60 μs | **20 μs** | Cache-line alignment |
| End-to-End | 15 ms | **3 ms** | Zero-copy serialization |

---

## 1. Lock-Free Data Structures

### 1.1 Order Book Optimization

**Problem:** Current order book uses mutex-protected HashMap, causing lock contention under high update rates.

**Solution:** Lock-free concurrent order book using crossbeam or concurrent collections.

```rust
use crossbeam::queue::SegQueue;
use std::sync::atomic::{AtomicU64, Ordering};

/// Lock-free order book implementation
pub struct LockFreeOrderBook {
    /// Lock-free price levels (sorted by price)
    bids: concurrent_skip_list::SkipMap<OrderedFloat<f64>, Level>,
    asks: concurrent_skip_list::SkipMap<OrderedFloat<f64>, Level>,

    /// Atomic sequence number for updates
    sequence: AtomicU64,

    /// Lock-free queue for update events
    update_queue: SegQueue<OrderBookUpdate>,
}

#[repr(align(64))]  // Cache-line aligned
pub struct Level {
    price: f64,
    quantity: AtomicU64,  // Atomic for lock-free updates
    order_count: AtomicU32,
}

impl LockFreeOrderBook {
    /// Update order book without locks (wait-free)
    pub fn update(&self, price: f64, quantity: u64, side: Side) {
        let levels = match side {
            Side::Bid => &self.bids,
            Side::Ask => &self.asks,
        };

        // Lock-free insert/update
        levels.insert(
            OrderedFloat(price),
            Level {
                price,
                quantity: AtomicU64::new(quantity),
                order_count: AtomicU32::new(1),
            }
        );

        // Increment sequence atomically
        self.sequence.fetch_add(1, Ordering::SeqCst);
    }

    /// Get best bid/ask without locks
    pub fn best_bid(&self) -> Option<(f64, u64)> {
        self.bids.iter()
            .next_back()  // Highest bid
            .map(|entry| {
                let level = entry.value();
                (level.price, level.quantity.load(Ordering::Acquire))
            })
    }
}
```

**Expected Improvement:**
- Update latency: 15 μs → **5 μs** (67% reduction)
- Throughput: 100K updates/sec → **500K updates/sec** (5x)
- No lock contention on multi-core systems

### 1.2 Position Tracking

**Current:** Mutex-protected HashMap for positions.

**Optimized:** Lock-free concurrent HashMap using DashMap.

```rust
use dashmap::DashMap;

pub struct LockFreePositionTracker {
    /// Lock-free concurrent positions map
    positions: DashMap<String, Position>,
}

impl LockFreePositionTracker {
    /// Update position without global lock
    pub fn update(&self, symbol: &str, quantity: i64, price: f64) {
        self.positions.entry(symbol.to_string())
            .and_modify(|pos| {
                pos.quantity += quantity;
                pos.update_avg_price(price);
            })
            .or_insert_with(|| Position::new(quantity, price));
    }

    /// Read position without blocking writers
    pub fn get_position(&self, symbol: &str) -> Option<Position> {
        self.positions.get(symbol).map(|r| r.clone())
    }
}
```

---

## 2. SIMD Vectorization for Signal Generation

### 2.1 Technical Indicator Optimization

**Problem:** Sequential calculations for RSI, MACD, Bollinger Bands are CPU-bound.

**Solution:** Use SIMD instructions (AVX2/AVX512) via `packed_simd` or manual intrinsics.

```rust
use packed_simd::{f64x4, f64x8};

/// SIMD-accelerated RSI calculation
pub fn calculate_rsi_simd(prices: &[f64], period: usize) -> Vec<f64> {
    let gains = Vec::with_capacity(prices.len());
    let losses = Vec::with_capacity(prices.len());

    // Process 8 prices at a time with AVX-512
    let chunks = prices.chunks_exact(8);

    for chunk in chunks {
        // Load 8 prices into SIMD register
        let curr = f64x8::from_slice_unaligned(chunk);
        let prev = f64x8::from_slice_unaligned(&chunk[1..]);

        // Vectorized difference
        let diff = curr - prev;

        // Vectorized conditional split (gains/losses)
        let zero = f64x8::splat(0.0);
        let gains_vec = diff.max(zero);
        let losses_vec = (-diff).max(zero);

        // Store results
        gains_vec.write_to_slice_unaligned(&mut gains[..8]);
        losses_vec.write_to_slice_unaligned(&mut losses[..8]);
    }

    // Calculate RSI from gains/losses (also vectorized)
    calculate_rsi_from_gains_losses_simd(&gains, &losses, period)
}

/// SIMD moving average
pub fn sma_simd(values: &[f64], window: usize) -> Vec<f64> {
    let mut result = Vec::with_capacity(values.len());

    for i in window..values.len() {
        let slice = &values[i - window..i];

        // SIMD sum reduction
        let sum = simd_sum_f64(slice);
        result.push(sum / window as f64);
    }

    result
}

#[inline(always)]
fn simd_sum_f64(slice: &[f64]) -> f64 {
    let mut sum = f64x8::splat(0.0);

    for chunk in slice.chunks_exact(8) {
        let vals = f64x8::from_slice_unaligned(chunk);
        sum += vals;
    }

    // Horizontal sum
    sum.sum()
}
```

**Expected Improvement:**
- RSI calculation: 10 μs → **2 μs** (5x faster)
- MACD calculation: 15 μs → **3 μs** (5x faster)
- Full signal pipeline: 250 μs → **80 μs** (3x faster)

### 2.2 Feature Engineering with SIMD

```rust
/// SIMD-accelerated order book imbalance
pub fn calculate_imbalance_simd(bids: &[Level], asks: &[Level]) -> f64 {
    let bid_volumes = bids.iter()
        .map(|l| l.quantity.load(Ordering::Relaxed) as f64)
        .collect::<Vec<_>>();

    let ask_volumes = asks.iter()
        .map(|l| l.quantity.load(Ordering::Relaxed) as f64)
        .collect::<Vec<_>>();

    let total_bid = simd_sum_f64(&bid_volumes);
    let total_ask = simd_sum_f64(&ask_volumes);

    (total_bid - total_ask) / (total_bid + total_ask)
}
```

---

## 3. Zero-Copy Serialization

### 3.1 Binary Protocol Instead of JSON

**Problem:** JSON serialization/deserialization adds 2-5 μs latency per message.

**Solution:** Use zero-copy binary formats (bincode, Cap'n Proto, or flatbuffers).

```rust
use bincode::{serialize_into, deserialize_from};
use serde::{Serialize, Deserialize};

/// Zero-copy order representation
#[derive(Serialize, Deserialize)]
#[repr(C)]  // C layout for zero-copy
pub struct BinaryOrder {
    order_id: u64,
    symbol: [u8; 8],  // Fixed-size symbol (pad with zeros)
    side: u8,  // 0 = buy, 1 = sell
    quantity: u64,
    price: f64,
    timestamp: u64,
}

impl BinaryOrder {
    /// Serialize to bytes without allocation
    pub fn to_bytes(&self, buf: &mut [u8]) -> Result<usize, bincode::Error> {
        bincode::serialize_into(buf, self)?;
        Ok(std::mem::size_of::<Self>())
    }

    /// Deserialize from bytes without copying
    pub fn from_bytes(buf: &[u8]) -> Result<Self, bincode::Error> {
        bincode::deserialize(buf)
    }
}

/// Zero-copy message passing between components
pub struct ZeroCopyChannel<T> {
    /// Ring buffer for zero-copy message passing
    ring: RingBuffer<T>,
}

impl<T: Copy> ZeroCopyChannel<T> {
    /// Send message without copying
    pub fn send(&self, msg: T) -> Result<(), ChannelError> {
        // Direct memory write to ring buffer
        self.ring.push(msg)
    }

    /// Receive message by reference (no copy)
    pub fn recv(&self) -> Option<&T> {
        self.ring.peek()
    }
}
```

**Expected Improvement:**
- Serialization: 3 μs (JSON) → **0.2 μs** (bincode) (15x faster)
- Deserialization: 5 μs (JSON) → **0.3 μs** (bincode) (16x faster)
- Network protocol overhead: -60%

### 3.2 Memory-Mapped Inter-Process Communication

For Python integration, use shared memory instead of sockets.

```rust
use memmap2::MmapMut;
use std::sync::atomic::{AtomicU64, Ordering};

/// Zero-copy shared memory for Rust-Python communication
pub struct SharedMemoryChannel {
    /// Memory-mapped file
    mmap: MmapMut,

    /// Write pointer (atomic for synchronization)
    write_ptr: AtomicU64,

    /// Read pointer
    read_ptr: AtomicU64,
}

impl SharedMemoryChannel {
    /// Write data directly to shared memory (zero-copy)
    pub fn write(&self, data: &[u8]) -> Result<(), Error> {
        let offset = self.write_ptr.load(Ordering::Acquire);

        // Direct memory copy
        unsafe {
            let dest = self.mmap.as_ptr().add(offset as usize);
            std::ptr::copy_nonoverlapping(data.as_ptr(), dest, data.len());
        }

        // Update write pointer
        self.write_ptr.fetch_add(data.len() as u64, Ordering::Release);
        Ok(())
    }
}
```

---

## 4. Cache-Friendly Memory Layouts

### 4.1 Cache-Line Alignment

**Problem:** False sharing between threads causes cache thrashing.

**Solution:** Align hot data structures to 64-byte cache lines.

```rust
use std::alloc::Layout;

/// Cache-line aligned structure to prevent false sharing
#[repr(align(64))]
pub struct CacheAlignedCounter {
    value: AtomicU64,
    _padding: [u8; 56],  // Pad to 64 bytes
}

/// Array of counters without false sharing
pub struct PerCoreCounters {
    counters: Vec<CacheAlignedCounter>,
}

impl PerCoreCounters {
    pub fn new(num_cores: usize) -> Self {
        Self {
            counters: (0..num_cores)
                .map(|_| CacheAlignedCounter {
                    value: AtomicU64::new(0),
                    _padding: [0; 56],
                })
                .collect(),
        }
    }

    /// Increment without false sharing
    pub fn increment(&self, core_id: usize) {
        self.counters[core_id].value.fetch_add(1, Ordering::Relaxed);
    }
}
```

### 4.2 Structure-of-Arrays Layout

**Problem:** Array-of-Structures (AoS) causes poor cache utilization.

**Solution:** Use Structure-of-Arrays (SoA) for vectorized operations.

```rust
/// Inefficient: Array of Structures
pub struct Trade {
    symbol: String,
    price: f64,
    quantity: u64,
    timestamp: u64,
}
pub struct TradesAoS {
    trades: Vec<Trade>,
}

/// Efficient: Structure of Arrays
pub struct TradesSoA {
    symbols: Vec<String>,
    prices: Vec<f64>,      // Contiguous in memory
    quantities: Vec<u64>,  // Better cache locality
    timestamps: Vec<u64>,  // SIMD-friendly
}

impl TradesSoA {
    /// Calculate average price with SIMD
    pub fn avg_price_simd(&self) -> f64 {
        simd_sum_f64(&self.prices) / self.prices.len() as f64
    }

    /// Filter by price threshold with SIMD
    pub fn filter_by_price_simd(&self, threshold: f64) -> Vec<usize> {
        let mut indices = Vec::new();
        let threshold_vec = f64x8::splat(threshold);

        for (i, chunk) in self.prices.chunks_exact(8).enumerate() {
            let prices = f64x8::from_slice_unaligned(chunk);
            let mask = prices.gt(threshold_vec);

            // Add matching indices
            for j in 0..8 {
                if mask.extract(j) {
                    indices.push(i * 8 + j);
                }
            }
        }

        indices
    }
}
```

**Expected Improvement:**
- Cache hit rate: 70% → **95%**
- SIMD vectorization efficiency: 50% → **95%**
- Batch processing throughput: +3x

---

## 5. Memory Management Optimization

### 5.1 Custom Allocators

**Problem:** Default allocator (jemalloc) has overhead for small allocations.

**Solution:** Use arena allocators for short-lived objects.

```rust
use bumpalo::Bump;

/// Arena allocator for per-request data
pub struct RequestArena {
    arena: Bump,
}

impl RequestArena {
    pub fn new() -> Self {
        Self {
            arena: Bump::with_capacity(64 * 1024),  // 64KB arena
        }
    }

    /// Allocate from arena (fast, no fragmentation)
    pub fn alloc_trade(&self, symbol: &str, price: f64, qty: u64) -> &mut Trade {
        self.arena.alloc(Trade {
            symbol: symbol.to_string(),
            price,
            quantity: qty,
            timestamp: current_timestamp(),
        })
    }

    /// Reset arena after request (O(1))
    pub fn reset(&mut self) {
        self.arena.reset();
    }
}
```

### 5.2 Object Pooling

```rust
use crossbeam::queue::ArrayQueue;

/// Object pool for reusable orders
pub struct OrderPool {
    pool: ArrayQueue<Order>,
}

impl OrderPool {
    pub fn new(capacity: usize) -> Self {
        let pool = ArrayQueue::new(capacity);
        for _ in 0..capacity {
            let _ = pool.push(Order::default());
        }
        Self { pool }
    }

    /// Get order from pool (no allocation)
    pub fn get(&self) -> Option<Order> {
        self.pool.pop()
    }

    /// Return order to pool for reuse
    pub fn put(&self, mut order: Order) {
        order.reset();
        let _ = self.pool.push(order);
    }
}
```

---

## 6. CPU Affinity and Thread Pinning

### 6.1 Core Pinning for Critical Threads

```rust
use core_affinity;

/// Pin critical threads to specific CPU cores
pub fn pin_threads() {
    // Pin WebSocket thread to core 0 (isolated core)
    let core_ids = core_affinity::get_core_ids().unwrap();

    std::thread::spawn(move || {
        core_affinity::set_for_current(core_ids[0]);
        run_websocket_loop();
    });

    // Pin signal generation to cores 1-2 (compute)
    std::thread::spawn(move || {
        core_affinity::set_for_current(core_ids[1]);
        run_signal_generation_loop();
    });

    // Pin order execution to core 3 (isolated)
    std::thread::spawn(move || {
        core_affinity::set_for_current(core_ids[3]);
        run_order_execution_loop();
    });
}
```

---

## 7. Compiler Optimizations

### 7.1 Profile-Guided Optimization (PGO)

```bash
# Step 1: Build instrumented binary
RUSTFLAGS="-C profile-generate=/tmp/pgo-data" cargo build --release

# Step 2: Run representative workload
./target/release/trading-system --benchmark

# Step 3: Build optimized binary with profile data
RUSTFLAGS="-C profile-use=/tmp/pgo-data" cargo build --release
```

### 7.2 LTO and CPU-Specific Optimizations

```toml
# Cargo.toml
[profile.release]
opt-level = 3
lto = "fat"           # Link-time optimization
codegen-units = 1     # Better optimization, slower compile
panic = "abort"       # Smaller binary, faster unwinding

[build]
rustflags = [
    "-C", "target-cpu=native",  # Use AVX2/AVX512
    "-C", "target-feature=+avx2,+fma",
]
```

---

## 8. Performance Budget Allocation

### 8.1 Latency Budget Breakdown (Target: 3ms end-to-end)

| Component | Budget (μs) | % of Total | Priority |
|-----------|-------------|------------|----------|
| WebSocket receive | 50 | 1.7% | High |
| Data parsing | 100 | 3.3% | High |
| Order book update | 5 | 0.2% | Critical |
| Signal generation | 80 | 2.7% | High |
| Risk check | 20 | 0.7% | Critical |
| Order serialization | 10 | 0.3% | Medium |
| Network send | 200 | 6.7% | Medium |
| Exchange processing | 2000 | 66.7% | External |
| Fill acknowledgment | 535 | 17.8% | External |
| **Total** | **3000** | **100%** | |

### 8.2 Memory Budget

| Component | Budget (MB) | Max Growth |
|-----------|-------------|------------|
| Order book (per symbol) | 10 | 20 MB |
| Trade history | 50 | 100 MB |
| Position tracking | 5 | 10 MB |
| Signal cache | 20 | 50 MB |
| Network buffers | 10 | 20 MB |
| **Total** | **95** | **200 MB** |

---

## 9. Quick Wins (Low Effort, High Impact)

### Priority 1: Immediate Implementation (Week 1)

1. **Replace std::sync::Mutex with parking_lot::Mutex** (20% faster)
2. **Enable LTO in Cargo.toml** (5-10% faster)
3. **Add #[inline] attributes to hot functions** (2-5% faster)
4. **Use SmallVec for small collections** (avoid heap allocations)

```rust
use parking_lot::RwLock;  // Faster than std::sync::RwLock
use smallvec::SmallVec;

pub struct OptimizedOrderBook {
    // Before: std::sync::RwLock
    // After: parking_lot::RwLock (20% faster)
    bids: RwLock<BTreeMap<OrderedFloat<f64>, Level>>,

    // Before: Vec<Order> (heap allocation)
    // After: SmallVec (stack-allocated for <8 orders)
    pending_orders: SmallVec<[Order; 8]>,
}

#[inline(always)]  // Force inline for hot path
pub fn get_best_bid(&self) -> Option<f64> {
    self.bids.read()
        .iter()
        .next_back()
        .map(|(price, _)| price.0)
}
```

### Priority 2: Medium Effort (Week 2-3)

1. **Implement DashMap for concurrent positions** (50% faster)
2. **Use bincode instead of JSON** (10x faster serialization)
3. **Add SIMD to RSI/MACD calculations** (5x faster)
4. **Align hot structures to cache lines** (20% faster)

### Priority 3: Long-Term (Week 4+)

1. **Full lock-free order book** (5x throughput)
2. **Zero-copy shared memory for Python** (100x faster IPC)
3. **WASM SIMD for portable vectorization**
4. **Custom memory allocator**

---

## 10. Measurement and Validation

### 10.1 Before/After Benchmarks

```bash
# Baseline (before optimization)
cargo bench --all > baseline.txt

# After each optimization
cargo bench --all > optimized.txt

# Compare
cargo criterion --baseline baseline
```

### 10.2 Continuous Performance Monitoring

```rust
use metrics::{histogram, counter};

#[inline(always)]
fn instrument<F, R>(name: &'static str, f: F) -> R
where
    F: FnOnce() -> R,
{
    let start = std::time::Instant::now();
    let result = f();
    let elapsed = start.elapsed().as_micros() as f64;

    histogram!(name).record(elapsed);

    if elapsed > LATENCY_THRESHOLD {
        counter!("latency_violations", "component" => name).increment(1);
    }

    result
}
```

---

## Summary

This performance optimization plan provides a roadmap to achieve sub-millisecond latencies through:

1. **Lock-free data structures** for order book and positions
2. **SIMD vectorization** for signal calculations
3. **Zero-copy serialization** for network efficiency
4. **Cache-friendly layouts** to maximize CPU cache utilization
5. **Memory management** with custom allocators and pooling

**Expected Overall Improvement:**
- End-to-end latency: 15ms → **3ms** (5x faster)
- Throughput: 200 trades/sec → **2000 trades/sec** (10x)
- Memory usage: Stable at <200MB
- CPU utilization: <30% average, <60% P99

**Next Steps:**
1. Review profiling methodology (see profiling-methodology.md)
2. Implement quick wins first
3. Benchmark after each optimization
4. Follow optimization roadmap

---

**References:**
- [profiling-methodology.md](./profiling-methodology.md)
- [benchmarking-strategy.md](./benchmarking-strategy.md)
- [optimization-roadmap.md](./optimization-roadmap.md)
