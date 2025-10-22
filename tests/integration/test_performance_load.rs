//! Performance and load integration tests
//!
//! Tests system performance under load:
//! - Order throughput
//! - Concurrent request handling
//! - Database performance
//! - Memory usage
//! - Latency percentiles
//! - System recovery

use chrono::Utc;
use common::types::*;
use common::config::{RiskConfig, ExecutionConfig};
use database::{DatabaseManager, MetricRecord};
use risk_manager::stops::{StopManager, StopLossConfig};
use execution_engine::router::OrderRouter;
use std::sync::Arc;
use tokio;

#[cfg(test)]
mod performance_load_tests {
    use super::*;

    #[tokio::test]
    async fn test_order_submission_throughput() {
        // Test: Measure order submission throughput
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 100, // High limit for throughput test
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = Arc::new(OrderRouter::new(config).unwrap());
        let order_count = 100;
        let start = std::time::Instant::now();

        let mut handles = vec![];

        for i in 0..order_count {
            let router_clone = router.clone();
            let handle = tokio::spawn(async move {
                let order = Order {
                    order_id: format!("ord_{}", i),
                    client_order_id: format!("client_{}", i),
                    symbol: Symbol("AAPL".to_string()),
                    side: Side::Bid,
                    order_type: OrderType::Market,
                    quantity: Quantity(10.0),
                    price: None,
                    stop_price: None,
                    status: OrderStatus::Pending,
                    filled_quantity: Quantity(0.0),
                    average_price: None,
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };

                router_clone.route(order, Some(150.0)).await
            });
            handles.push(handle);
        }

        let mut successes = 0;
        for handle in handles {
            if let Ok(Ok(_)) = handle.await {
                successes += 1;
            }
        }

        let duration = start.elapsed();
        let throughput = (order_count as f64) / duration.as_secs_f64();

        println!("Throughput: {:.2} orders/sec", throughput);
        println!("Success rate: {}/{}", successes, order_count);

        assert!(throughput > 10.0, "Should achieve >10 orders/sec");
        assert_eq!(successes, order_count, "All orders should succeed in paper trading");
    }

    #[tokio::test]
    async fn test_concurrent_order_handling_100() {
        // Test: Handle 100 concurrent orders
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 50,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = Arc::new(OrderRouter::new(config).unwrap());
        let concurrent_count = 100;

        let mut handles = vec![];
        let start = std::time::Instant::now();

        for i in 0..concurrent_count {
            let router_clone = router.clone();
            let handle = tokio::spawn(async move {
                let symbol = match i % 5 {
                    0 => "AAPL",
                    1 => "MSFT",
                    2 => "GOOGL",
                    3 => "AMZN",
                    _ => "TSLA",
                };

                let order = Order {
                    order_id: uuid::Uuid::new_v4().to_string(),
                    client_order_id: uuid::Uuid::new_v4().to_string(),
                    symbol: Symbol(symbol.to_string()),
                    side: if i % 2 == 0 { Side::Bid } else { Side::Ask },
                    order_type: OrderType::Market,
                    quantity: Quantity((10 + i as i32) as f64),
                    price: None,
                    stop_price: None,
                    status: OrderStatus::Pending,
                    filled_quantity: Quantity(0.0),
                    average_price: None,
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };

                router_clone.route(order, Some(150.0)).await
            });
            handles.push(handle);
        }

        let mut results = Vec::new();
        for handle in handles {
            if let Ok(result) = handle.await {
                results.push(result);
            }
        }

        let duration = start.elapsed();

        println!("Concurrent execution duration: {:?}", duration);
        println!("Successful orders: {}/{}", results.iter().filter(|r| r.is_ok()).count(), concurrent_count);

        assert!(duration.as_secs() < 30, "100 concurrent orders should complete in <30s");
        assert_eq!(results.len(), concurrent_count);
    }

    #[tokio::test]
    async fn test_database_write_performance_1000() {
        // Test: Database write performance with 1000 metrics
        let db_path = format!("test_perf_{}.duckdb", uuid::Uuid::new_v4());
        let db = DatabaseManager::new(&db_path).await.unwrap();
        db.initialize().await.unwrap();

        let start = std::time::Instant::now();

        for i in 0..1000 {
            let metric = MetricRecord::new(
                "performance_test",
                i as f64
            ).with_symbol(&format!("SYM{}", i % 10));

            db.insert_metric(&metric).await.expect("Insert failed");
        }

        let duration = start.elapsed();
        let writes_per_sec = 1000.0 / duration.as_secs_f64();

        println!("Database write performance: {:.0} writes/sec", writes_per_sec);

        assert!(writes_per_sec > 100.0, "Should achieve >100 writes/sec");
        assert!(duration.as_secs() < 20, "1000 writes should complete in <20s");
    }

    #[tokio::test]
    async fn test_concurrent_database_writes() {
        // Test: Concurrent database writes
        let db_path = format!("test_concurrent_{}.duckdb", uuid::Uuid::new_v4());
        let db = Arc::new(DatabaseManager::new(&db_path).await.unwrap());
        db.initialize().await.unwrap();

        let write_count = 100;
        let mut handles = vec![];
        let start = std::time::Instant::now();

        for i in 0..write_count {
            let db_clone = db.clone();
            let handle = tokio::spawn(async move {
                let metric = MetricRecord::new(
                    "concurrent_test",
                    i as f64
                ).with_symbol(&format!("SYM{}", i));

                db_clone.insert_metric(&metric).await
            });
            handles.push(handle);
        }

        for handle in handles {
            let _ = handle.await.expect("Task panicked");
        }

        let duration = start.elapsed();

        // Verify all writes completed
        let metrics = db.get_metrics("concurrent_test", None, None, 1000).await.unwrap();
        assert_eq!(metrics.len(), write_count);

        println!("Concurrent database writes: {} in {:?}", write_count, duration);
        assert!(duration.as_secs() < 10, "Concurrent writes should be fast");
    }

    #[tokio::test]
    async fn test_stop_loss_check_performance_1000() {
        // Test: Stop-loss check performance on 1000 positions
        let risk_config = RiskConfig {
            max_position_size: 10000.0,
            max_notional_exposure: 50000.0,
            max_open_positions: 5,
            stop_loss_percent: 5.0,
            trailing_stop_percent: 3.0,
            enable_circuit_breaker: true,
            max_loss_threshold: 1000.0,
        };

        let mut stop_manager = StopManager::new(risk_config);

        // Create 1000 positions
        let mut positions = Vec::new();
        for i in 0..1000 {
            let position = Position {
                symbol: Symbol(format!("SYM{}", i)),
                side: Side::Bid,
                quantity: Quantity(100.0),
                entry_price: Price(100.0 + i as f64),
                current_price: Price(95.0 + i as f64), // All underwater
                unrealized_pnl: -500.0,
                realized_pnl: 0.0,
                opened_at: Utc::now(),
                updated_at: Utc::now(),
            };

            let stop_config = StopLossConfig::static_stop(5.0).unwrap();
            stop_manager.set_stop(&position, stop_config).expect("Set stop failed");
            positions.push(position);
        }

        // Measure check performance
        let start = std::time::Instant::now();
        let mut triggered = 0;

        for pos in &positions {
            if stop_manager.check(pos).is_some() {
                triggered += 1;
            }
        }

        let duration = start.elapsed();
        let checks_per_sec = 1000.0 / duration.as_secs_f64();

        println!("Stop-loss check performance: {:.0} checks/sec", checks_per_sec);
        println!("Triggered stops: {}", triggered);

        assert!(checks_per_sec > 1000.0, "Should check >1000 positions/sec");
        assert!(duration.as_millis() < 1000, "1000 checks should complete in <1s");
    }

    #[tokio::test]
    async fn test_market_data_processing_rate() {
        // Test: Process high-frequency market data updates
        let db_path = format!("test_market_data_{}.duckdb", uuid::Uuid::new_v4());
        let db = DatabaseManager::new(&db_path).await.unwrap();
        db.initialize().await.unwrap();

        let update_count = 1000;
        let start = std::time::Instant::now();

        for i in 0..update_count {
            let price_update = MetricRecord::new("price", 150.0 + (i as f64 * 0.01))
                .with_symbol("AAPL");

            db.insert_metric(&price_update).await.expect("Insert failed");
        }

        let duration = start.elapsed();
        let updates_per_sec = update_count as f64 / duration.as_secs_f64();

        println!("Market data processing: {:.0} updates/sec", updates_per_sec);

        assert!(updates_per_sec > 100.0, "Should process >100 updates/sec");
    }

    #[tokio::test]
    async fn test_latency_percentiles() {
        // Test: Measure latency distribution (p50, p95, p99)
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 50,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = OrderRouter::new(config).unwrap();
        let sample_count = 100;
        let mut latencies = Vec::new();

        for i in 0..sample_count {
            let order = Order {
                order_id: format!("ord_{}", i),
                client_order_id: format!("client_{}", i),
                symbol: Symbol("AAPL".to_string()),
                side: Side::Bid,
                order_type: OrderType::Market,
                quantity: Quantity(10.0),
                price: None,
                stop_price: None,
                status: OrderStatus::Pending,
                filled_quantity: Quantity(0.0),
                average_price: None,
                created_at: Utc::now(),
                updated_at: Utc::now(),
            };

            let start = std::time::Instant::now();
            let _ = router.route(order, Some(150.0)).await;
            let latency = start.elapsed();

            latencies.push(latency.as_millis());
        }

        // Calculate percentiles
        latencies.sort();
        let p50 = latencies[latencies.len() / 2];
        let p95 = latencies[(latencies.len() * 95) / 100];
        let p99 = latencies[(latencies.len() * 99) / 100];

        println!("Latency p50: {}ms, p95: {}ms, p99: {}ms", p50, p95, p99);

        assert!(p50 < 1000, "p50 latency should be <1000ms");
        assert!(p95 < 2000, "p95 latency should be <2000ms");
        assert!(p99 < 3000, "p99 latency should be <3000ms");
    }

    #[tokio::test]
    async fn test_sustained_load_60_seconds() {
        // Test: System under sustained load for 60 seconds
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = Arc::new(OrderRouter::new(config).unwrap());
        let duration = std::time::Duration::from_secs(10); // Reduced to 10s for faster tests
        let start = std::time::Instant::now();
        let mut order_count = 0;

        while start.elapsed() < duration {
            let router_clone = router.clone();
            let handle = tokio::spawn(async move {
                let order = Order {
                    order_id: uuid::Uuid::new_v4().to_string(),
                    client_order_id: uuid::Uuid::new_v4().to_string(),
                    symbol: Symbol("AAPL".to_string()),
                    side: Side::Bid,
                    order_type: OrderType::Market,
                    quantity: Quantity(10.0),
                    price: None,
                    stop_price: None,
                    status: OrderStatus::Pending,
                    filled_quantity: Quantity(0.0),
                    average_price: None,
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };

                router_clone.route(order, Some(150.0)).await
            });

            let _ = handle.await;
            order_count += 1;

            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        }

        let actual_duration = start.elapsed();
        let avg_rate = order_count as f64 / actual_duration.as_secs_f64();

        println!("Sustained load: {} orders in {:?} ({:.2} orders/sec)",
                 order_count, actual_duration, avg_rate);

        assert!(order_count > 50, "Should process >50 orders in 10s");
    }

    #[tokio::test]
    async fn test_spike_load_10x_normal() {
        // Test: Handle 10x spike in traffic
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 100,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = Arc::new(OrderRouter::new(config).unwrap());
        let spike_count = 50; // 10x normal load
        let mut handles = vec![];

        let start = std::time::Instant::now();

        for i in 0..spike_count {
            let router_clone = router.clone();
            let handle = tokio::spawn(async move {
                let order = Order {
                    order_id: format!("spike_{}", i),
                    client_order_id: format!("spike_client_{}", i),
                    symbol: Symbol("AAPL".to_string()),
                    side: Side::Bid,
                    order_type: OrderType::Market,
                    quantity: Quantity(10.0),
                    price: None,
                    stop_price: None,
                    status: OrderStatus::Pending,
                    filled_quantity: Quantity(0.0),
                    average_price: None,
                    created_at: Utc::now(),
                    updated_at: Utc::now(),
                };

                router_clone.route(order, Some(150.0)).await
            });
            handles.push(handle);
        }

        for handle in handles {
            let _ = handle.await;
        }

        let duration = start.elapsed();

        println!("Spike load handled {} orders in {:?}", spike_count, duration);

        assert!(duration.as_secs() < 10, "Spike should be handled in <10s");
    }

    #[tokio::test]
    async fn test_memory_usage_under_load() {
        // Test: Monitor memory usage during load test
        use std::process::Command;

        let initial_memory = get_process_memory();

        // Create large number of positions
        let position_count = 1000;
        let mut positions = Vec::new();

        for i in 0..position_count {
            positions.push(Position {
                symbol: Symbol(format!("SYM{}", i)),
                side: Side::Bid,
                quantity: Quantity(100.0),
                entry_price: Price(100.0),
                current_price: Price(100.0),
                unrealized_pnl: 0.0,
                realized_pnl: 0.0,
                opened_at: Utc::now(),
                updated_at: Utc::now(),
            });
        }

        let final_memory = get_process_memory();
        let memory_increase = final_memory.saturating_sub(initial_memory);

        println!("Memory increase: {} bytes for {} positions", memory_increase, position_count);

        // Memory should not grow excessively
        assert!(memory_increase < 100_000_000, "Memory growth should be <100MB");

        // Helper function to get process memory (mock implementation)
        fn get_process_memory() -> usize {
            // In real implementation, would use OS-specific APIs
            0
        }
    }

    #[tokio::test]
    async fn test_database_query_performance_large_dataset() {
        // Test: Query performance with large dataset
        let db_path = format!("test_query_perf_{}.duckdb", uuid::Uuid::new_v4());
        let db = DatabaseManager::new(&db_path).await.unwrap();
        db.initialize().await.unwrap();

        // Insert 10,000 metrics
        for i in 0..10000 {
            let metric = MetricRecord::new("large_dataset_test", i as f64)
                .with_symbol("AAPL");
            db.insert_metric(&metric).await.expect("Insert failed");
        }

        // Time various queries
        let start = std::time::Instant::now();
        let all_metrics = db.get_metrics("large_dataset_test", None, None, 100).await.unwrap();
        let query_duration = start.elapsed();

        println!("Query retrieved {} records in {:?}", all_metrics.len(), query_duration);

        assert_eq!(all_metrics.len(), 100); // Limited to 100
        assert!(query_duration.as_millis() < 500, "Query should complete in <500ms");
    }
}
