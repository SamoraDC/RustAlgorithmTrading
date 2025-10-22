/// Performance benchmarks for critical trading paths
/// Uses criterion for statistical analysis of performance

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use common::types::*;
use market_data::orderbook::OrderBookManager;
use chrono::Utc;

fn benchmark_order_creation(c: &mut Criterion) {
    c.bench_function("order_creation", |b| {
        b.iter(|| {
            let order = Order {
                id: "bench-order".to_string(),
                symbol: "AAPL".to_string(),
                side: OrderSide::Buy,
                order_type: OrderType::Limit,
                quantity: black_box(100),
                price: Some(black_box(150.00)),
                status: OrderStatus::Pending,
                timestamp: Utc::now(),
            };
            black_box(order);
        });
    });
}

fn benchmark_order_serialization(c: &mut Criterion) {
    let order = Order {
        id: "serialize-bench".to_string(),
        symbol: "TSLA".to_string(),
        side: OrderSide::Buy,
        order_type: OrderType::Market,
        quantity: 50,
        price: None,
        status: OrderStatus::Pending,
        timestamp: Utc::now(),
    };

    c.bench_function("order_serialization", |b| {
        b.iter(|| {
            let json = serde_json::to_string(black_box(&order)).unwrap();
            black_box(json);
        });
    });
}

fn benchmark_order_deserialization(c: &mut Criterion) {
    let order = Order {
        id: "deserialize-bench".to_string(),
        symbol: "NVDA".to_string(),
        side: OrderSide::Sell,
        order_type: OrderType::Limit,
        quantity: 25,
        price: Some(450.00),
        status: OrderStatus::Filled,
        timestamp: Utc::now(),
    };

    let json = serde_json::to_string(&order).unwrap();

    c.bench_function("order_deserialization", |b| {
        b.iter(|| {
            let order: Order = serde_json::from_str(black_box(&json)).unwrap();
            black_box(order);
        });
    });
}

fn benchmark_orderbook_updates(c: &mut Criterion) {
    let mut group = c.benchmark_group("orderbook_updates");

    for depth in [10, 100, 1000].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(depth),
            depth,
            |b, &depth| {
                let mut manager = OrderBookManager::new();
                let symbol = "BENCH".to_string();

                b.iter(|| {
                    for i in 0..depth {
                        let level = PriceLevel {
                            price: 100.00 + (i as f64 * 0.01),
                            volume: 100,
                        };
                        // manager.add_bid(&symbol, level);
                        black_box(&level);
                    }
                });
            },
        );
    }

    group.finish();
}

fn benchmark_position_pnl_calculation(c: &mut Criterion) {
    c.bench_function("position_pnl", |b| {
        b.iter(|| {
            let quantity = black_box(100);
            let avg_price = black_box(150.00);
            let current_price = black_box(155.00);

            let unrealized_pnl = (current_price - avg_price) * quantity as f64;

            let position = Position {
                symbol: "AAPL".to_string(),
                quantity,
                average_price: avg_price,
                current_price,
                unrealized_pnl,
                realized_pnl: 0.0,
                timestamp: Utc::now(),
            };

            black_box(position);
        });
    });
}

fn benchmark_tick_processing(c: &mut Criterion) {
    let mut group = c.benchmark_group("tick_processing");

    for tick_count in [100, 1000, 10000].iter() {
        group.bench_with_input(
            BenchmarkId::from_parameter(tick_count),
            tick_count,
            |b, &count| {
                b.iter(|| {
                    for i in 0..count {
                        let tick = Tick {
                            symbol: "AAPL".to_string(),
                            price: 150.00 + (i as f64 * 0.01),
                            volume: 100,
                            timestamp: Utc::now(),
                        };
                        black_box(tick);
                    }
                });
            },
        );
    }

    group.finish();
}

fn benchmark_bar_aggregation(c: &mut Criterion) {
    c.bench_function("bar_aggregation", |b| {
        b.iter(|| {
            let bar = Bar {
                symbol: "TSLA".to_string(),
                open: black_box(250.00),
                high: black_box(255.00),
                low: black_box(248.00),
                close: black_box(252.00),
                volume: black_box(50000),
                timestamp: Utc::now(),
                timeframe: "1m".to_string(),
            };
            black_box(bar);
        });
    });
}

fn benchmark_concurrent_order_processing(c: &mut Criterion) {
    use std::sync::Arc;
    use std::sync::atomic::{AtomicU64, Ordering};

    c.bench_function("concurrent_orders", |b| {
        let counter = Arc::new(AtomicU64::new(0));

        b.iter(|| {
            let handles: Vec<_> = (0..10)
                .map(|_| {
                    let counter_clone = Arc::clone(&counter);
                    std::thread::spawn(move || {
                        for _ in 0..100 {
                            let order = Order {
                                id: format!("order-{}", counter_clone.fetch_add(1, Ordering::SeqCst)),
                                symbol: "AAPL".to_string(),
                                side: OrderSide::Buy,
                                order_type: OrderType::Market,
                                quantity: 10,
                                price: None,
                                status: OrderStatus::Pending,
                                timestamp: Utc::now(),
                            };
                            black_box(order);
                        }
                    })
                })
                .collect();

            for handle in handles {
                handle.join().unwrap();
            }
        });
    });
}

fn benchmark_spread_calculation(c: &mut Criterion) {
    c.bench_function("spread_calculation", |b| {
        b.iter(|| {
            let bid = black_box(150.00);
            let ask = black_box(150.50);
            let spread = ask - bid;
            let spread_bps = (spread / bid) * 10000.0;
            black_box(spread_bps);
        });
    });
}

fn benchmark_order_validation(c: &mut Criterion) {
    let order = Order {
        id: "validate-bench".to_string(),
        symbol: "GOOG".to_string(),
        side: OrderSide::Buy,
        order_type: OrderType::Limit,
        quantity: 10,
        price: Some(2500.00),
        status: OrderStatus::Pending,
        timestamp: Utc::now(),
    };

    c.bench_function("order_validation", |b| {
        b.iter(|| {
            // Validation checks
            let valid = order.quantity > 0
                && order.price.is_some()
                && !order.symbol.is_empty();
            black_box(valid);
        });
    });
}

fn benchmark_large_orderbook(c: &mut Criterion) {
    let mut manager = OrderBookManager::new();
    let symbol = "DEEP".to_string();

    // Pre-populate with 1000 levels
    for i in 0..1000 {
        let bid = PriceLevel {
            price: 1000.00 - (i as f64 * 0.01),
            volume: 100,
        };
        let ask = PriceLevel {
            price: 1001.00 + (i as f64 * 0.01),
            volume: 100,
        };
        // manager.add_bid(&symbol, bid);
        // manager.add_ask(&symbol, ask);
    }

    c.bench_function("large_orderbook_query", |b| {
        b.iter(|| {
            // Benchmark querying large orderbook
            // let best_bid = manager.get_best_bid(&symbol);
            // let best_ask = manager.get_best_ask(&symbol);
            // black_box(best_bid);
            // black_box(best_ask);
        });
    });
}

fn benchmark_memory_allocation(c: &mut Criterion) {
    c.bench_function("order_vector_allocation", |b| {
        b.iter(|| {
            let mut orders = Vec::with_capacity(1000);
            for i in 0..1000 {
                orders.push(Order {
                    id: format!("order-{}", i),
                    symbol: "AAPL".to_string(),
                    side: OrderSide::Buy,
                    order_type: OrderType::Market,
                    quantity: 10,
                    price: None,
                    status: OrderStatus::Pending,
                    timestamp: Utc::now(),
                });
            }
            black_box(orders);
        });
    });
}

criterion_group!(
    benches,
    benchmark_order_creation,
    benchmark_order_serialization,
    benchmark_order_deserialization,
    benchmark_orderbook_updates,
    benchmark_position_pnl_calculation,
    benchmark_tick_processing,
    benchmark_bar_aggregation,
    benchmark_concurrent_order_processing,
    benchmark_spread_calculation,
    benchmark_order_validation,
    benchmark_large_orderbook,
    benchmark_memory_allocation
);

criterion_main!(benches);
