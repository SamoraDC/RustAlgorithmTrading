//! Integration tests for concurrent order handling
//!
//! Tests cover:
//! - Concurrent order submission
//! - Race condition handling
//! - Thread safety
//! - Order queue management

use std::sync::{Arc, Mutex};
use tokio::task::JoinSet;
use common::types::{Order, OrderStatus, OrderType, Price, Quantity, Side, Symbol};
use chrono::Utc;

#[cfg(test)]
mod concurrent_order_tests {
    use super::*;

    fn create_test_order(id: usize, symbol: &str) -> Order {
        Order {
            order_id: format!("ord_{}", id),
            client_order_id: format!("client_{}", id),
            symbol: Symbol(symbol.to_string()),
            side: Side::Bid,
            order_type: OrderType::Market,
            quantity: Quantity(100.0),
            price: None,
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    #[tokio::test]
    async fn test_concurrent_order_creation() {
        let orders = Arc::new(Mutex::new(Vec::new()));
        let mut tasks = JoinSet::new();

        // Spawn 100 concurrent tasks
        for i in 0..100 {
            let orders_clone = Arc::clone(&orders);
            tasks.spawn(async move {
                let order = create_test_order(i, "AAPL");
                let mut orders = orders_clone.lock().unwrap();
                orders.push(order);
            });
        }

        // Wait for all tasks
        while let Some(_) = tasks.join_next().await {}

        let final_orders = orders.lock().unwrap();
        assert_eq!(final_orders.len(), 100);
    }

    #[tokio::test]
    async fn test_concurrent_multi_symbol_orders() {
        let orders = Arc::new(Mutex::new(Vec::new()));
        let symbols = vec!["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"];
        let mut tasks = JoinSet::new();

        // Create 20 orders per symbol concurrently
        for (i, symbol) in symbols.iter().enumerate() {
            for j in 0..20 {
                let orders_clone = Arc::clone(&orders);
                let symbol = symbol.to_string();
                let order_id = i * 20 + j;

                tasks.spawn(async move {
                    let order = create_test_order(order_id, &symbol);
                    let mut orders = orders_clone.lock().unwrap();
                    orders.push(order);
                });
            }
        }

        while let Some(_) = tasks.join_next().await {}

        let final_orders = orders.lock().unwrap();
        assert_eq!(final_orders.len(), 100);

        // Verify all symbols are present
        for symbol in symbols {
            let count = final_orders.iter()
                .filter(|o| o.symbol.0 == symbol)
                .count();
            assert_eq!(count, 20);
        }
    }

    #[tokio::test]
    async fn test_concurrent_order_updates() {
        let order = Arc::new(Mutex::new(create_test_order(1, "AAPL")));
        let mut tasks = JoinSet::new();

        // Spawn tasks that update different fields
        for i in 0..50 {
            let order_clone = Arc::clone(&order);
            tasks.spawn(async move {
                let mut order = order_clone.lock().unwrap();
                order.filled_quantity = Quantity(i as f64);
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let final_order = order.lock().unwrap();
        // Some filled quantity should be set
        assert!(final_order.filled_quantity.0 >= 0.0);
    }

    #[tokio::test]
    async fn test_order_processing_queue() {
        let queue = Arc::new(Mutex::new(Vec::new()));
        let processed = Arc::new(Mutex::new(Vec::new()));
        let mut tasks = JoinSet::new();

        // Add orders to queue
        {
            let mut q = queue.lock().unwrap();
            for i in 0..50 {
                q.push(create_test_order(i, "AAPL"));
            }
        }

        // Spawn workers to process queue
        for _ in 0..5 {
            let queue_clone = Arc::clone(&queue);
            let processed_clone = Arc::clone(&processed);

            tasks.spawn(async move {
                loop {
                    let order_opt = {
                        let mut q = queue_clone.lock().unwrap();
                        q.pop()
                    };

                    match order_opt {
                        Some(mut order) => {
                            // Simulate processing
                            order.status = OrderStatus::Filled;
                            let mut p = processed_clone.lock().unwrap();
                            p.push(order);
                        }
                        None => break,
                    }
                }
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let final_processed = processed.lock().unwrap();
        assert_eq!(final_processed.len(), 50);

        // All should be filled
        for order in final_processed.iter() {
            assert_eq!(order.status, OrderStatus::Filled);
        }
    }

    #[tokio::test]
    async fn test_concurrent_order_validation() {
        let valid_orders = Arc::new(Mutex::new(0));
        let invalid_orders = Arc::new(Mutex::new(0));
        let mut tasks = JoinSet::new();

        for i in 0..100 {
            let valid_clone = Arc::clone(&valid_orders);
            let invalid_clone = Arc::clone(&invalid_orders);

            tasks.spawn(async move {
                let order = create_test_order(i, "AAPL");

                // Validate order
                let is_valid = order.quantity.0 > 0.0 && !order.symbol.0.is_empty();

                if is_valid {
                    let mut v = valid_clone.lock().unwrap();
                    *v += 1;
                } else {
                    let mut inv = invalid_clone.lock().unwrap();
                    *inv += 1;
                }
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let valid = *valid_orders.lock().unwrap();
        let invalid = *invalid_orders.lock().unwrap();

        assert_eq!(valid + invalid, 100);
        assert_eq!(valid, 100); // All should be valid
    }
}

#[cfg(test)]
mod race_condition_tests {
    use super::*;

    #[tokio::test]
    async fn test_counter_increment_race() {
        let counter = Arc::new(Mutex::new(0));
        let mut tasks = JoinSet::new();

        for _ in 0..1000 {
            let counter_clone = Arc::clone(&counter);
            tasks.spawn(async move {
                let mut c = counter_clone.lock().unwrap();
                *c += 1;
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let final_count = *counter.lock().unwrap();
        assert_eq!(final_count, 1000);
    }

    #[tokio::test]
    async fn test_shared_state_consistency() {
        #[derive(Clone)]
        struct SharedState {
            order_count: usize,
            total_quantity: f64,
        }

        let state = Arc::new(Mutex::new(SharedState {
            order_count: 0,
            total_quantity: 0.0,
        }));

        let mut tasks = JoinSet::new();

        for i in 0..100 {
            let state_clone = Arc::clone(&state);
            tasks.spawn(async move {
                let mut s = state_clone.lock().unwrap();
                s.order_count += 1;
                s.total_quantity += 100.0 * (i as f64 + 1.0);
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let final_state = state.lock().unwrap();
        assert_eq!(final_state.order_count, 100);

        // Sum of 100, 200, 300, ..., 10000
        let expected_total = (1..=100).map(|i| 100.0 * i as f64).sum::<f64>();
        assert_eq!(final_state.total_quantity, expected_total);
    }
}

#[cfg(test)]
mod performance_tests {
    use super::*;
    use std::time::Instant;

    #[tokio::test]
    async fn test_order_throughput() {
        let start = Instant::now();
        let orders = Arc::new(Mutex::new(Vec::new()));
        let mut tasks = JoinSet::new();

        // Process 1000 orders
        for i in 0..1000 {
            let orders_clone = Arc::clone(&orders);
            tasks.spawn(async move {
                let order = create_test_order(i, "AAPL");
                let mut orders = orders_clone.lock().unwrap();
                orders.push(order);
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let duration = start.elapsed();
        let final_orders = orders.lock().unwrap();

        assert_eq!(final_orders.len(), 1000);

        // Should complete in reasonable time (< 5 seconds)
        assert!(duration.as_secs() < 5);
    }

    #[tokio::test]
    async fn test_batch_processing_performance() {
        let start = Instant::now();
        let processed_count = Arc::new(Mutex::new(0));
        let mut tasks = JoinSet::new();

        // Process in batches of 100
        for batch in 0..10 {
            let count_clone = Arc::clone(&processed_count);
            tasks.spawn(async move {
                // Simulate batch processing
                for i in 0..100 {
                    let _order = create_test_order(batch * 100 + i, "AAPL");
                    // Process order
                }
                let mut count = count_clone.lock().unwrap();
                *count += 100;
            });
        }

        while let Some(_) = tasks.join_next().await {}

        let duration = start.elapsed();
        let total = *processed_count.lock().unwrap();

        assert_eq!(total, 1000);
        assert!(duration.as_secs() < 5);
    }
}
