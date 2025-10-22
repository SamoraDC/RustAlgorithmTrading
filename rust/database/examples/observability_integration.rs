//! Observability integration example showing metrics collection

use database::{DatabaseManager, MetricRecord, SystemEvent};
use chrono::{Duration, Utc};
use std::collections::HashMap;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing with custom format
    tracing_subscriber::fmt()
        .with_target(false)
        .with_level(true)
        .init();

    println!("📊 Observability Integration Example\n");

    // Create database
    let db = DatabaseManager::new("examples/observability_demo.duckdb").await?;
    db.initialize().await?;

    // Simulate collecting system metrics
    println!("📈 Collecting system metrics...");

    let now = Utc::now();
    let mut metrics = Vec::new();

    // Simulate 1 hour of metrics at 10Hz (36000 data points)
    for i in 0..3600 {
        let timestamp = now - Duration::seconds(3600 - i as i64);

        // CPU metrics
        metrics.push(MetricRecord {
            timestamp,
            metric_name: "system_cpu_percent".to_string(),
            value: 20.0 + (i as f64 % 100.0) / 10.0,
            symbol: None,
            labels: Some({
                let mut map = HashMap::new();
                map.insert("host".to_string(), "trading-server-1".to_string());
                map.insert("core".to_string(), "0".to_string());
                map
            }),
        });

        // Memory metrics
        if i % 10 == 0 {
            metrics.push(MetricRecord {
                timestamp,
                metric_name: "system_memory_percent".to_string(),
                value: 60.0 + (i as f64 % 200.0) / 20.0,
                symbol: None,
                labels: Some({
                    let mut map = HashMap::new();
                    map.insert("host".to_string(), "trading-server-1".to_string());
                    map
                }),
            });
        }

        // Market data metrics
        if i % 5 == 0 {
            metrics.push(MetricRecord {
                timestamp,
                metric_name: "market_price".to_string(),
                value: 50000.0 + (i as f64 * 10.0).sin() * 1000.0,
                symbol: Some("BTC/USD".to_string()),
                labels: Some({
                    let mut map = HashMap::new();
                    map.insert("exchange".to_string(), "alpaca".to_string());
                    map
                }),
            });

            metrics.push(MetricRecord {
                timestamp,
                metric_name: "market_price".to_string(),
                value: 3000.0 + (i as f64 * 5.0).cos() * 100.0,
                symbol: Some("ETH/USD".to_string()),
                labels: Some({
                    let mut map = HashMap::new();
                    map.insert("exchange".to_string(), "alpaca".to_string());
                    map
                }),
            });
        }

        // Execution metrics
        if i % 30 == 0 {
            metrics.push(MetricRecord {
                timestamp,
                metric_name: "order_latency_ms".to_string(),
                value: 10.0 + (i as f64 % 50.0),
                symbol: Some("BTC/USD".to_string()),
                labels: Some({
                    let mut map = HashMap::new();
                    map.insert("order_type".to_string(), "market".to_string());
                    map
                }),
            });
        }
    }

    // Batch insert (high performance)
    let start = std::time::Instant::now();
    db.insert_metrics(&metrics).await?;
    let duration = start.elapsed();

    println!(
        "  ✓ Inserted {} metrics in {:?} ({:.0} metrics/sec)",
        metrics.len(),
        duration,
        metrics.len() as f64 / duration.as_secs_f64()
    );

    // Log system events
    println!("\n📝 Logging system events...");

    let events = vec![
        SystemEvent::info("Trading system started"),
        SystemEvent::info("Connected to market data feed"),
        SystemEvent::warning("High latency detected: 150ms"),
        SystemEvent::info("Order executed successfully"),
        SystemEvent::error("Failed to connect to backup exchange"),
    ];

    for event in &events {
        db.log_event(event).await?;
    }

    println!("  ✓ Logged {} events", events.len());

    // Query and analyze metrics
    println!("\n🔍 Analyzing metrics...");

    // Get latest CPU metrics
    let cpu_metrics = db
        .get_metrics("system_cpu_percent", None, None, 10)
        .await?;

    if !cpu_metrics.is_empty() {
        let avg_cpu: f64 = cpu_metrics.iter().map(|m| m.value).sum::<f64>()
            / cpu_metrics.len() as f64;
        println!("  CPU Usage (avg of last 10): {:.2}%", avg_cpu);
    }

    // Get latest prices for all symbols
    let btc_metrics = db
        .get_metrics("market_price", Some("BTC/USD"), None, 1)
        .await?;

    if let Some(btc) = btc_metrics.first() {
        println!("  BTC/USD Price: ${:.2}", btc.value);
    }

    let eth_metrics = db
        .get_metrics("market_price", Some("ETH/USD"), None, 1)
        .await?;

    if let Some(eth) = eth_metrics.first() {
        println!("  ETH/USD Price: ${:.2}", eth.value);
    }

    // Get aggregated latency metrics
    use database::TimeInterval;

    let aggregated = db
        .get_aggregated_metrics(
            "order_latency_ms",
            TimeInterval::Minute,
            Some(now - Duration::hours(1)),
            "avg",
        )
        .await?;

    if !aggregated.is_empty() {
        let avg_latency: f64 = aggregated.iter().map(|m| m.value).sum::<f64>()
            / aggregated.len() as f64;
        println!("  Order Latency (avg): {:.2}ms", avg_latency);
    }

    // Database statistics
    println!("\n📊 Database Statistics:");

    let stats = db.get_table_stats().await?;
    for stat in stats {
        println!("  Table: {}", stat.table_name);
        println!("    Rows: {}", stat.row_count);
        if let (Some(min), Some(max)) = (stat.min_timestamp, stat.max_timestamp) {
            println!(
                "    Range: {} to {}",
                min.format("%H:%M:%S"),
                max.format("%H:%M:%S")
            );
        }
    }

    // Connection pool stats
    let pool_stats = db.pool_stats();
    println!("\n🔌 Connection Pool:");
    println!("  Total: {}", pool_stats.connections);
    println!("  Idle: {}", pool_stats.idle_connections);

    // Optimize database
    println!("\n🔧 Optimizing database...");
    db.optimize().await?;

    println!("\n✅ Observability integration example completed!");

    Ok(())
}
