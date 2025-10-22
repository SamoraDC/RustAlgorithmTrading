//! Integration tests for observability and metrics collection
//!
//! Tests end-to-end observability workflows including:
//! - Metric collection and storage
//! - DuckDB database integration
//! - Time-series queries
//! - System event logging
//! - Performance tracking

use chrono::{Utc, Duration};
use database::{DatabaseManager, MetricRecord, CandleRecord, TradeRecord, SystemEvent};
use std::collections::HashMap;
use tokio;

#[cfg(test)]
mod observability_integration_tests {
    use super::*;

    async fn setup_test_db() -> DatabaseManager {
        let db_path = format!("test_metrics_{}.duckdb", uuid::Uuid::new_v4());
        let db = DatabaseManager::new(&db_path).await
            .expect("Failed to create test database");
        db.initialize().await.expect("Failed to initialize database");
        db
    }

    async fn cleanup_test_db(db: &DatabaseManager) {
        // Database will be cleaned up when dropped
        // In production, you might want to explicitly close connections
        drop(db);
    }

    #[tokio::test]
    async fn test_metric_collection_and_storage() {
        // Test: End-to-end metric collection from order to database
        let db = setup_test_db().await;

        // Create metric record
        let metric = MetricRecord::new("order_latency_ms", 42.5)
            .with_symbol("AAPL")
            .add_label("exchange", "alpaca")
            .add_label("order_type", "market");

        // Store metric
        let result = db.insert_metric(&metric).await;
        assert!(result.is_ok(), "Metric insertion should succeed");

        // Retrieve metric
        let metrics = db.get_metrics("order_latency_ms", None, None, 10).await;
        assert!(metrics.is_ok());

        let retrieved = metrics.unwrap();
        assert_eq!(retrieved.len(), 1);
        assert_eq!(retrieved[0].metric_name, "order_latency_ms");
        assert_eq!(retrieved[0].value, 42.5);
        assert_eq!(retrieved[0].symbol, Some("AAPL".to_string()));

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_multiple_metrics_storage() {
        // Test: Store multiple different metrics
        let db = setup_test_db().await;

        let metrics = vec![
            MetricRecord::new("order_latency_ms", 45.2).with_symbol("AAPL"),
            MetricRecord::new("fill_rate_pct", 98.5).with_symbol("MSFT"),
            MetricRecord::new("slippage_bps", 2.3).with_symbol("GOOGL"),
            MetricRecord::new("position_pnl", 1234.56).with_symbol("AAPL"),
            MetricRecord::new("cpu_usage_pct", 45.0),
        ];

        for metric in &metrics {
            let result = db.insert_metric(metric).await;
            assert!(result.is_ok(), "All metrics should be inserted successfully");
        }

        // Retrieve specific metric
        let latency_metrics = db.get_metrics("order_latency_ms", None, None, 10).await;
        assert!(latency_metrics.is_ok());
        assert_eq!(latency_metrics.unwrap().len(), 1);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_time_series_data_retrieval() {
        // Test: Retrieve metrics within time range
        let db = setup_test_db().await;

        let now = Utc::now();
        let hour_ago = now - Duration::hours(1);
        let two_hours_ago = now - Duration::hours(2);

        // Insert metrics with different timestamps
        let metrics = vec![
            MetricRecord {
                timestamp: two_hours_ago,
                metric_name: "order_latency_ms".to_string(),
                value: 40.0,
                symbol: Some("AAPL".to_string()),
                labels: None,
            },
            MetricRecord {
                timestamp: hour_ago,
                metric_name: "order_latency_ms".to_string(),
                value: 45.0,
                symbol: Some("AAPL".to_string()),
                labels: None,
            },
            MetricRecord {
                timestamp: now,
                metric_name: "order_latency_ms".to_string(),
                value: 50.0,
                symbol: Some("AAPL".to_string()),
                labels: None,
            },
        ];

        for metric in &metrics {
            db.insert_metric(metric).await.expect("Insert failed");
        }

        // Query last hour
        let recent_metrics = db.get_metrics(
            "order_latency_ms",
            Some(hour_ago),
            Some(now),
            10
        ).await.unwrap();

        assert_eq!(recent_metrics.len(), 2); // Should get 2 most recent

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_metric_aggregation() {
        // Test: Aggregate metrics over time intervals
        let db = setup_test_db().await;

        let now = Utc::now();

        // Insert multiple metrics in same time window
        for i in 0..10 {
            let metric = MetricRecord {
                timestamp: now - Duration::minutes(i),
                metric_name: "order_latency_ms".to_string(),
                value: 40.0 + (i as f64),
                symbol: Some("AAPL".to_string()),
                labels: None,
            };
            db.insert_metric(&metric).await.expect("Insert failed");
        }

        // Retrieve and verify
        let metrics = db.get_metrics("order_latency_ms", None, None, 100).await.unwrap();
        assert_eq!(metrics.len(), 10);

        // Calculate average manually
        let sum: f64 = metrics.iter().map(|m| m.value).sum();
        let avg = sum / metrics.len() as f64;
        assert!((avg - 44.5).abs() < 0.1); // Average should be ~44.5

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_candle_data_storage() {
        // Test: Store and retrieve OHLCV candle data
        let db = setup_test_db().await;

        let candle = CandleRecord::new(
            Utc::now(),
            "AAPL",
            150.0,
            155.0,
            149.0,
            154.0,
            1000000
        ).with_trade_count(500);

        let result = db.insert_candle(&candle).await;
        assert!(result.is_ok(), "Candle insertion should succeed");

        // Verify candle data
        assert_eq!(candle.open, 150.0);
        assert_eq!(candle.high, 155.0);
        assert_eq!(candle.low, 149.0);
        assert_eq!(candle.close, 154.0);
        assert_eq!(candle.volume, 1000000);
        assert_eq!(candle.trade_count, Some(500));

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_trade_execution_recording() {
        // Test: Record trade execution in database
        let db = setup_test_db().await;

        let trade = TradeRecord {
            trade_id: uuid::Uuid::new_v4().to_string(),
            order_id: uuid::Uuid::new_v4().to_string(),
            symbol: "AAPL".to_string(),
            side: "buy".to_string(),
            quantity: 100.0,
            price: 150.0,
            timestamp: Utc::now(),
            commission: 1.0,
            trade_value: 15000.0,
            liquidity: Some("taker".to_string()),
        };

        let result = db.insert_trade(&trade).await;
        assert!(result.is_ok(), "Trade insertion should succeed");

        // Verify trade value calculation
        assert_eq!(trade.trade_value, trade.quantity * trade.price);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_system_event_logging() {
        // Test: Log system events with different severity levels
        let db = setup_test_db().await;

        let events = vec![
            SystemEvent::info("System started successfully"),
            SystemEvent::warning("High latency detected"),
            SystemEvent::error("Failed to connect to exchange"),
        ];

        for event in &events {
            let result = db.insert_event(event).await;
            assert!(result.is_ok(), "Event insertion should succeed");
        }

        // Query recent events
        let recent_events = db.get_events(None, None, 10).await;
        assert!(recent_events.is_ok());
        assert_eq!(recent_events.unwrap().len(), 3);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_system_event_with_details() {
        // Test: System events with JSON details
        let db = setup_test_db().await;

        let details = serde_json::json!({
            "order_id": "12345",
            "error_code": "TIMEOUT",
            "retry_count": 3
        });

        let event = SystemEvent::error("Order execution failed")
            .with_details(details.clone());

        let result = db.insert_event(&event).await;
        assert!(result.is_ok());

        assert_eq!(event.severity, "error");
        assert!(event.details.is_some());
        assert_eq!(event.details.unwrap()["order_id"], "12345");

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_concurrent_metric_writes() {
        // Test: Multiple concurrent writes to database
        let db = setup_test_db().await;

        let mut handles = vec![];

        for i in 0..10 {
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

        // Wait for all writes to complete
        for handle in handles {
            let result = handle.await;
            assert!(result.is_ok());
            assert!(result.unwrap().is_ok());
        }

        // Verify all metrics were written
        let metrics = db.get_metrics("concurrent_test", None, None, 100).await.unwrap();
        assert_eq!(metrics.len(), 10);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_database_performance_1000_writes() {
        // Test: Database write performance with 1000 metrics
        use std::time::Instant;

        let db = setup_test_db().await;
        let start = Instant::now();

        for i in 0..1000 {
            let metric = MetricRecord::new("perf_test", i as f64)
                .with_symbol("AAPL");
            db.insert_metric(&metric).await.expect("Insert failed");
        }

        let duration = start.elapsed();
        let writes_per_sec = 1000.0 / duration.as_secs_f64();

        println!("Write performance: {:.0} writes/sec", writes_per_sec);
        assert!(writes_per_sec > 100.0, "Should achieve >100 writes/sec");

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_database_query_performance() {
        // Test: Query performance with large dataset
        use std::time::Instant;

        let db = setup_test_db().await;

        // Insert 1000 metrics
        for i in 0..1000 {
            let metric = MetricRecord::new("query_perf_test", i as f64)
                .with_symbol("AAPL");
            db.insert_metric(&metric).await.expect("Insert failed");
        }

        // Time query
        let start = Instant::now();
        let metrics = db.get_metrics("query_perf_test", None, None, 100).await;
        let duration = start.elapsed();

        assert!(metrics.is_ok());
        assert_eq!(metrics.unwrap().len(), 100);
        assert!(duration.as_millis() < 100, "Query should be fast (<100ms)");

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_metric_filtering_by_symbol() {
        // Test: Filter metrics by symbol
        let db = setup_test_db().await;

        // Insert metrics for different symbols
        for symbol in &["AAPL", "MSFT", "GOOGL"] {
            for i in 0..5 {
                let metric = MetricRecord::new("test_metric", i as f64)
                    .with_symbol(symbol);
                db.insert_metric(&metric).await.expect("Insert failed");
            }
        }

        // Query specific symbol
        let aapl_metrics = db.get_metrics_by_symbol("test_metric", "AAPL", 100).await;
        assert!(aapl_metrics.is_ok());
        assert_eq!(aapl_metrics.unwrap().len(), 5);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_database_table_statistics() {
        // Test: Get database statistics
        let db = setup_test_db().await;

        // Insert some data
        for i in 0..100 {
            let metric = MetricRecord::new("stats_test", i as f64);
            db.insert_metric(&metric).await.expect("Insert failed");
        }

        // Get table stats
        let stats = db.get_table_stats("metrics").await;
        assert!(stats.is_ok());

        let table_stats = stats.unwrap();
        assert_eq!(table_stats.table_name, "metrics");
        assert!(table_stats.row_count >= 100);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_order_execution_workflow_with_metrics() {
        // Test: Complete workflow from order to metrics collection
        let db = setup_test_db().await;
        let start_time = std::time::Instant::now();

        // Step 1: Order submitted
        let order_id = uuid::Uuid::new_v4().to_string();
        let submit_event = SystemEvent::info("Order submitted")
            .with_details(serde_json::json!({
                "order_id": order_id,
                "symbol": "AAPL",
                "quantity": 100
            }));
        db.insert_event(&submit_event).await.expect("Event insert failed");

        // Step 2: Record latency
        let latency_ms = start_time.elapsed().as_millis() as f64;
        let latency_metric = MetricRecord::new("order_submit_latency_ms", latency_ms)
            .with_symbol("AAPL")
            .add_label("order_id", &order_id);
        db.insert_metric(&latency_metric).await.expect("Metric insert failed");

        // Step 3: Order filled
        let trade = TradeRecord {
            trade_id: uuid::Uuid::new_v4().to_string(),
            order_id: order_id.clone(),
            symbol: "AAPL".to_string(),
            side: "buy".to_string(),
            quantity: 100.0,
            price: 150.0,
            timestamp: Utc::now(),
            commission: 1.0,
            trade_value: 15000.0,
            liquidity: Some("taker".to_string()),
        };
        db.insert_trade(&trade).await.expect("Trade insert failed");

        // Step 4: Record fill metric
        let fill_metric = MetricRecord::new("order_filled", 1.0)
            .with_symbol("AAPL")
            .add_label("order_id", &order_id);
        db.insert_metric(&fill_metric).await.expect("Metric insert failed");

        // Verify all data stored
        let events = db.get_events(None, None, 10).await.unwrap();
        assert!(events.len() >= 1);

        let metrics = db.get_metrics("order_submit_latency_ms", None, None, 10).await.unwrap();
        assert!(metrics.len() >= 1);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_database_error_handling() {
        // Test: Database handles errors gracefully
        let db = setup_test_db().await;

        // Try to query non-existent metric
        let result = db.get_metrics("nonexistent_metric", None, None, 10).await;
        // Should return empty list, not error
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), 0);

        cleanup_test_db(&db).await;
    }

    #[tokio::test]
    async fn test_alert_threshold_monitoring() {
        // Test: Detect when metrics exceed thresholds
        let db = setup_test_db().await;

        let threshold_latency = 100.0; // ms
        let mut alerts = Vec::new();

        // Insert metrics, some exceeding threshold
        let latencies = vec![50.0, 75.0, 150.0, 45.0, 200.0, 80.0];

        for (i, latency) in latencies.iter().enumerate() {
            let metric = MetricRecord::new("order_latency_ms", *latency)
                .with_symbol("AAPL");
            db.insert_metric(&metric).await.expect("Insert failed");

            // Check threshold
            if *latency > threshold_latency {
                let alert = SystemEvent::warning(
                    format!("High latency detected: {:.2}ms", latency)
                ).with_details(serde_json::json!({
                    "metric": "order_latency_ms",
                    "value": latency,
                    "threshold": threshold_latency,
                    "index": i
                }));
                db.insert_event(&alert).await.expect("Alert insert failed");
                alerts.push(alert);
            }
        }

        // Should have 2 alerts (150.0 and 200.0)
        assert_eq!(alerts.len(), 2);

        // Verify alerts were logged
        let events = db.get_events(None, None, 10).await.unwrap();
        let warning_events: Vec<_> = events.iter()
            .filter(|e| e.severity == "warning")
            .collect();
        assert!(warning_events.len() >= 2);

        cleanup_test_db(&db).await;
    }
}
