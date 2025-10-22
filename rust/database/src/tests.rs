//! Integration tests for the database module

#[cfg(test)]
mod integration_tests {
    use crate::*;
    use chrono::{Duration, Utc};
    use tempfile::NamedTempFile;

    #[tokio::test]
    async fn test_full_workflow() {
        // Create temporary database
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Insert metrics
        let metrics: Vec<MetricRecord> = (0..50)
            .map(|i| {
                MetricRecord::new("price", 50000.0 + i as f64)
                    .with_symbol("BTC/USD")
                    .add_label("exchange", "alpaca")
            })
            .collect();

        db.insert_metrics(&metrics).await.unwrap();

        // Query metrics
        let retrieved = db.get_metrics("price", Some("BTC/USD"), None, 100).await.unwrap();
        assert_eq!(retrieved.len(), 50);

        // Verify values
        assert!(retrieved.iter().any(|m| m.value == 50000.0));
        assert!(retrieved.iter().all(|m| m.symbol == Some("BTC/USD".to_string())));
    }

    #[tokio::test]
    async fn test_candle_operations() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Insert candles
        let now = Utc::now();
        for i in 0..10 {
            let candle = CandleRecord::new(
                now - Duration::minutes(i),
                "ETH/USD",
                3000.0,
                3100.0,
                2900.0,
                3050.0,
                1000000,
            );
            db.insert_candle(&candle).await.unwrap();
        }

        // Query candles
        let candles = db
            .get_candles("ETH/USD", TimeInterval::Minute, None, 100)
            .await
            .unwrap();

        assert!(!candles.is_empty());
        assert!(candles.iter().all(|c| c.symbol == "ETH/USD"));
    }

    #[tokio::test]
    async fn test_event_logging() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Log events
        let event1 = SystemEvent::info("System started");
        let event2 = SystemEvent::warning("High latency detected");
        let event3 = SystemEvent::error("Connection failed");

        db.log_event(&event1).await.unwrap();
        db.log_event(&event2).await.unwrap();
        let id = db.log_event(&event3).await.unwrap();

        assert!(id > 0);
    }

    #[tokio::test]
    async fn test_aggregated_metrics() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Insert metrics over time
        let now = Utc::now();
        for i in 0..100 {
            let mut metric = MetricRecord::new("latency", (i % 10) as f64);
            metric.timestamp = now - Duration::minutes(i);
            metric.symbol = Some("BTC/USD".to_string());
            db.insert_metric(&metric).await.unwrap();
        }

        // Get aggregated metrics
        let aggregated = db
            .get_aggregated_metrics("latency", TimeInterval::Hour, None, "avg")
            .await
            .unwrap();

        assert!(!aggregated.is_empty());
    }

    #[tokio::test]
    async fn test_table_statistics() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Insert some data
        let metric = MetricRecord::new("test", 42.0);
        db.insert_metric(&metric).await.unwrap();

        // Get statistics
        let stats = db.get_table_stats().await.unwrap();
        assert!(!stats.is_empty());
        assert!(stats.iter().any(|s| s.table_name == "trading_metrics"));
    }

    #[tokio::test]
    async fn test_connection_pool() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Get multiple connections concurrently
        let mut handles = vec![];

        for i in 0..5 {
            let db_clone = DatabaseManager::new(temp_file.path()).await.unwrap();
            let handle = tokio::spawn(async move {
                let metric = MetricRecord::new("concurrent_test", i as f64);
                db_clone.insert_metric(&metric).await
            });
            handles.push(handle);
        }

        for handle in handles {
            assert!(handle.await.unwrap().is_ok());
        }

        // Verify all were inserted
        let metrics = db.get_metrics("concurrent_test", None, None, 100).await.unwrap();
        assert_eq!(metrics.len(), 5);
    }

    #[tokio::test]
    async fn test_database_optimization() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        // Insert data
        let metrics: Vec<MetricRecord> = (0..1000)
            .map(|i| MetricRecord::new("opt_test", i as f64))
            .collect();
        db.insert_metrics(&metrics).await.unwrap();

        // Run optimization
        assert!(db.optimize().await.is_ok());
    }

    #[tokio::test]
    async fn test_time_range_queries() {
        let temp_file = NamedTempFile::new().unwrap();
        let db = DatabaseManager::new(temp_file.path()).await.unwrap();
        db.initialize().await.unwrap();

        let now = Utc::now();
        let hour_ago = now - Duration::hours(1);

        // Insert metrics with timestamps
        for i in 0..100 {
            let mut metric = MetricRecord::new("time_test", i as f64);
            metric.timestamp = now - Duration::minutes(i);
            db.insert_metric(&metric).await.unwrap();
        }

        // Query with time range
        let recent = db
            .get_metrics("time_test", None, Some(hour_ago), 1000)
            .await
            .unwrap();

        assert!(recent.len() <= 60); // Should be approximately 60 minutes
        assert!(recent.iter().all(|m| m.timestamp >= hour_ago));
    }
}
