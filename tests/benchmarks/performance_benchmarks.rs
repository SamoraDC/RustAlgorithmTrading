//! Performance Benchmarks for Critical Path Components
//!
//! These benchmarks validate the performance optimizations implemented
//! in Phase 1 of the latency reduction project.

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use common::types::{Order, OrderStatus, OrderType, Price, Quantity, Side, Symbol};
use execution_engine::slippage::SlippageEstimator;
use market_data::orderbook::FastOrderBook;
use chrono::Utc;

fn create_test_order(qty: f64, price: Option<f64>, order_type: OrderType) -> Order {
    Order {
        order_id: "test".to_string(),
        client_order_id: "client".to_string(),
        symbol: Symbol("AAPL".to_string()),
        side: Side::Bid,
        order_type,
        quantity: Quantity(qty),
        price: price.map(Price),
        stop_price: None,
        status: OrderStatus::Pending,
        filled_quantity: Quantity(0.0),
        average_price: None,
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

/// Benchmark order book updates (Target: <30μs p99)
fn bench_orderbook_update(c: &mut Criterion) {
    let mut group = c.benchmark_group("orderbook_update");

    // Single update benchmark
    group.bench_function("single_bid_update", |b| {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        b.iter(|| {
            book.update_bid(Price(black_box(150.0)), Quantity(black_box(100.0)));
        });
    });

    // Batch update benchmark
    group.bench_function("batch_100_updates", |b| {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        b.iter(|| {
            for i in 0..100 {
                let price = 150.0 + (i as f64 * 0.01);
                book.update_bid(Price(black_box(price)), Quantity(black_box(100.0)));
            }
        });
    });

    // Best bid/ask retrieval
    group.bench_function("get_best_bid_ask", |b| {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_ask(Price(150.5), Quantity(100.0));

        b.iter(|| {
            let _ = black_box(book.best_bid());
            let _ = black_box(book.best_ask());
        });
    });

    group.finish();
}

/// Benchmark slippage estimation (Target: <10μs)
fn bench_slippage_estimation(c: &mut Criterion) {
    let mut group = c.benchmark_group("slippage_estimation");

    let estimator = SlippageEstimator::new();

    // Small market order
    group.bench_function("market_order_small", |b| {
        let order = create_test_order(100.0, None, OrderType::Market);
        b.iter(|| {
            black_box(estimator.estimate(&order));
        });
    });

    // Large market order
    group.bench_function("market_order_large", |b| {
        let order = create_test_order(100000.0, None, OrderType::Market);
        b.iter(|| {
            black_box(estimator.estimate(&order));
        });
    });

    // Limit order
    group.bench_function("limit_order", |b| {
        let order = create_test_order(1000.0, Some(150.0), OrderType::Limit);
        b.iter(|| {
            black_box(estimator.estimate(&order));
        });
    });

    group.finish();
}

/// Benchmark order book walking for slippage calculation (Target: <5μs)
fn bench_orderbook_walking(c: &mut Criterion) {
    let mut group = c.benchmark_group("orderbook_walking");

    // Create order book with realistic depth
    let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
    for i in 0..100 {
        let bid_price = 150.0 - (i as f64 * 0.01);
        let ask_price = 150.5 + (i as f64 * 0.01);
        book.update_bid(Price(bid_price), Quantity(100.0));
        book.update_ask(Price(ask_price), Quantity(100.0));
    }

    // Walk for small order
    group.bench_function("walk_small_order", |b| {
        b.iter(|| {
            black_box(book.walk_book(Side::Bid, black_box(500.0)));
        });
    });

    // Walk for large order
    group.bench_function("walk_large_order", |b| {
        b.iter(|| {
            black_box(book.walk_book(Side::Bid, black_box(5000.0)));
        });
    });

    group.finish();
}

/// Benchmark serialization (JSON vs Bincode)
fn bench_serialization(c: &mut Criterion) {
    let mut group = c.benchmark_group("serialization");

    let order = create_test_order(1000.0, Some(150.0), OrderType::Limit);

    // JSON serialization
    group.bench_function("json_serialize", |b| {
        b.iter(|| {
            let _ = black_box(serde_json::to_string(&order).unwrap());
        });
    });

    // Bincode serialization
    group.bench_function("bincode_serialize", |b| {
        b.iter(|| {
            let _ = black_box(bincode::serialize(&order).unwrap());
        });
    });

    // JSON deserialization
    let json_str = serde_json::to_string(&order).unwrap();
    group.bench_function("json_deserialize", |b| {
        b.iter(|| {
            let _: Order = black_box(serde_json::from_str(&json_str).unwrap());
        });
    });

    // Bincode deserialization
    let bincode_bytes = bincode::serialize(&order).unwrap();
    group.bench_function("bincode_deserialize", |b| {
        b.iter(|| {
            let _: Order = black_box(bincode::deserialize(&bincode_bytes).unwrap());
        });
    });

    group.finish();
}

/// Benchmark overall critical path latency
fn bench_critical_path(c: &mut Criterion) {
    let mut group = c.benchmark_group("critical_path");

    group.bench_function("end_to_end_order_processing", |b| {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        let estimator = SlippageEstimator::new();

        // Setup order book
        for i in 0..50 {
            let bid_price = 150.0 - (i as f64 * 0.01);
            let ask_price = 150.5 + (i as f64 * 0.01);
            book.update_bid(Price(bid_price), Quantity(100.0));
            book.update_ask(Price(ask_price), Quantity(100.0));
        }

        b.iter(|| {
            // 1. Create order
            let order = create_test_order(
                black_box(1000.0),
                Some(black_box(150.25)),
                OrderType::Limit
            );

            // 2. Estimate slippage
            let slippage = estimator.estimate(&order);
            black_box(slippage);

            // 3. Walk order book
            let (avg_price, filled, _) = book.walk_book(Side::Bid, order.quantity.0);
            black_box((avg_price, filled));

            // 4. Serialize order (Bincode)
            let serialized = bincode::serialize(&order).unwrap();
            black_box(serialized);
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_orderbook_update,
    bench_slippage_estimation,
    bench_orderbook_walking,
    bench_serialization,
    bench_critical_path
);

criterion_main!(benches);
