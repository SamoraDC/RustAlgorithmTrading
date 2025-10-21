//! Performance benchmarks for latency-critical paths
//!
//! Benchmarks:
//! - Order book updates
//! - Order validation
//! - Risk checks
//! - Message parsing

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use chrono::Utc;
use common::types::{OrderBook, Level, Symbol, Price, Quantity, Order, OrderStatus, OrderType, Side};
use market_data::orderbook::OrderBookManager;

fn create_orderbook(depth: usize) -> OrderBook {
    let mut bids = Vec::new();
    let mut asks = Vec::new();

    for i in 0..depth {
        bids.push(Level {
            price: Price(100.0 - i as f64 * 0.01),
            quantity: Quantity((i + 1) as f64 * 10.0),
            timestamp: Utc::now(),
        });
        asks.push(Level {
            price: Price(100.01 + i as f64 * 0.01),
            quantity: Quantity((i + 1) as f64 * 10.0),
            timestamp: Utc::now(),
        });
    }

    OrderBook {
        symbol: Symbol("AAPL".to_string()),
        bids,
        asks,
        timestamp: Utc::now(),
        sequence: 1,
    }
}

fn create_order(quantity: f64) -> Order {
    Order {
        order_id: "bench_order".to_string(),
        client_order_id: "client_order".to_string(),
        symbol: Symbol("AAPL".to_string()),
        side: Side::Bid,
        order_type: OrderType::Limit,
        quantity: Quantity(quantity),
        price: Some(Price(100.0)),
        stop_price: None,
        status: OrderStatus::Pending,
        filled_quantity: Quantity(0.0),
        average_price: None,
        created_at: Utc::now(),
        updated_at: Utc::now(),
    }
}

fn bench_orderbook_update(c: &mut Criterion) {
    let mut group = c.benchmark_group("orderbook_update");

    for depth in [10, 50, 100, 500].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(depth), depth, |b, &depth| {
            let mut manager = OrderBookManager::new();
            let orderbook = create_orderbook(depth);

            b.iter(|| {
                manager.update(black_box(orderbook.clone()));
            });
        });
    }

    group.finish();
}

fn bench_orderbook_retrieval(c: &mut Criterion) {
    let mut manager = OrderBookManager::new();
    let orderbook = create_orderbook(100);
    manager.update(orderbook);

    c.bench_function("orderbook_get", |b| {
        b.iter(|| {
            let _book = manager.get(black_box("AAPL"));
        });
    });
}

fn bench_spread_calculation(c: &mut Criterion) {
    let orderbook = create_orderbook(100);

    c.bench_function("spread_calculation", |b| {
        b.iter(|| {
            let best_bid = black_box(&orderbook.bids[0].price);
            let best_ask = black_box(&orderbook.asks[0].price);
            let _spread = best_ask.0 - best_bid.0;
        });
    });
}

fn bench_order_validation(c: &mut Criterion) {
    c.bench_function("order_validation", |b| {
        let order = create_order(100.0);

        b.iter(|| {
            let _valid = black_box(order.quantity.0 > 0.0
                && !order.symbol.0.is_empty()
                && order.price.is_some());
        });
    });
}

fn bench_multiple_orderbook_updates(c: &mut Criterion) {
    let mut group = c.benchmark_group("multi_symbol_update");

    for num_symbols in [5, 10, 20, 50].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(num_symbols), num_symbols, |b, &num_symbols| {
            let mut manager = OrderBookManager::new();
            let orderbooks: Vec<_> = (0..num_symbols)
                .map(|i| {
                    let mut book = create_orderbook(100);
                    book.symbol = Symbol(format!("SYM{}", i));
                    book
                })
                .collect();

            b.iter(|| {
                for book in &orderbooks {
                    manager.update(black_box(book.clone()));
                }
            });
        });
    }

    group.finish();
}

fn bench_order_book_depth_analysis(c: &mut Criterion) {
    let orderbook = create_orderbook(1000);

    c.bench_function("depth_analysis", |b| {
        b.iter(|| {
            let mut total_bid_volume = 0.0;
            let mut total_ask_volume = 0.0;

            for level in black_box(&orderbook.bids) {
                total_bid_volume += level.quantity.0;
            }

            for level in black_box(&orderbook.asks) {
                total_ask_volume += level.quantity.0;
            }

            let _imbalance = total_bid_volume - total_ask_volume;
        });
    });
}

fn bench_vwap_calculation(c: &mut Criterion) {
    let orderbook = create_orderbook(100);

    c.bench_function("vwap_calculation", |b| {
        b.iter(|| {
            let mut total_value = 0.0;
            let mut total_volume = 0.0;

            for level in black_box(&orderbook.bids).iter().take(10) {
                total_value += level.price.0 * level.quantity.0;
                total_volume += level.quantity.0;
            }

            let _vwap = if total_volume > 0.0 {
                total_value / total_volume
            } else {
                0.0
            };
        });
    });
}

fn bench_order_creation(c: &mut Criterion) {
    c.bench_function("order_creation", |b| {
        b.iter(|| {
            let _order = create_order(black_box(100.0));
        });
    });
}

criterion_group!(
    benches,
    bench_orderbook_update,
    bench_orderbook_retrieval,
    bench_spread_calculation,
    bench_order_validation,
    bench_multiple_orderbook_updates,
    bench_order_book_depth_analysis,
    bench_vwap_calculation,
    bench_order_creation,
);

criterion_main!(benches);
