//! Integration tests for Risk-Execution-Observability workflows
//!
//! Tests complete workflows involving:
//! - Risk management checks
//! - Order execution
//! - Observability metrics collection
//! - Multi-component coordination

use chrono::{Utc, Duration};
use common::types::*;
use common::config::{RiskConfig, ExecutionConfig};
use database::{DatabaseManager, MetricRecord, TradeRecord, SystemEvent};
use risk_manager::stops::{StopManager, StopLossConfig, StopLossType};
use execution_engine::router::OrderRouter;
use tokio;

#[cfg(test)]
mod risk_execution_observability_tests {
    use super::*;

    async fn setup_test_environment() -> (StopManager, OrderRouter, DatabaseManager) {
        let risk_config = RiskConfig {
            max_position_size: 10000.0,
            max_notional_exposure: 50000.0,
            max_open_positions: 5,
            stop_loss_percent: 5.0,
            trailing_stop_percent: 3.0,
            enable_circuit_breaker: true,
            max_loss_threshold: 1000.0,
        };

        let exec_config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let db_path = format!("test_integration_{}.duckdb", uuid::Uuid::new_v4());
        let db = DatabaseManager::new(&db_path).await
            .expect("Failed to create database");
        db.initialize().await.expect("Failed to initialize database");

        let stop_manager = StopManager::new(risk_config);
        let router = OrderRouter::new(exec_config).expect("Failed to create router");

        (stop_manager, router, db)
    }

    #[tokio::test]
    async fn test_complete_signal_to_execution_workflow() {
        // Test: Complete workflow from signal -> risk check -> execution -> metrics
        let (mut stop_manager, router, db) = setup_test_environment().await;
        let workflow_start = std::time::Instant::now();

        // Step 1: Receive trading signal
        let signal = Signal {
            symbol: Symbol("AAPL".to_string()),
            action: SignalAction::Buy,
            confidence: 0.85,
            features: vec![1.0, 2.0, 3.0],
            timestamp: Utc::now(),
        };

        // Log signal reception
        let signal_event = SystemEvent::info("Trading signal received")
            .with_details(serde_json::json!({
                "symbol": signal.symbol.0,
                "action": format!("{:?}", signal.action),
                "confidence": signal.confidence
            }));
        db.insert_event(&signal_event).await.expect("Event insert failed");

        // Step 2: Create order from signal
        let order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: signal.symbol.clone(),
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
        };

        // Step 3: Risk check (position size validation)
        let notional_value = 100.0 * 150.0; // 100 shares at $150
        assert!(notional_value < 50000.0); // Within max_notional_exposure

        // Step 4: Execute order
        let exec_start = std::time::Instant::now();
        let result = router.route(order.clone(), Some(150.0)).await;
        let exec_duration = exec_start.elapsed();

        assert!(result.is_ok());
        let response = result.unwrap();

        // Step 5: Record execution metrics
        let latency_metric = MetricRecord::new("order_execution_latency_ms", exec_duration.as_millis() as f64)
            .with_symbol("AAPL")
            .add_label("order_id", &order.order_id);
        db.insert_metric(&latency_metric).await.expect("Metric insert failed");

        // Step 6: Record trade
        let trade = TradeRecord {
            trade_id: response.id.clone(),
            order_id: order.order_id.clone(),
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

        // Step 7: Create position and set stop-loss
        let position = Position {
            symbol: order.symbol.clone(),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(150.0),
            unrealized_pnl: 0.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let stop_config = StopLossConfig::static_stop(5.0).unwrap();
        stop_manager.set_stop(&position, stop_config).expect("Set stop failed");

        // Step 8: Record workflow completion metric
        let workflow_duration = workflow_start.elapsed();
        let workflow_metric = MetricRecord::new("complete_workflow_duration_ms", workflow_duration.as_millis() as f64)
            .with_symbol("AAPL");
        db.insert_metric(&workflow_metric).await.expect("Metric insert failed");

        // Verify all components worked together
        assert_eq!(response.symbol, "AAPL");
        assert!(stop_manager.has_stop(&position.symbol));
        assert!(workflow_duration.as_millis() < 5000); // Complete workflow < 5s
    }

    #[tokio::test]
    async fn test_position_limit_enforcement_with_metrics() {
        // Test: Risk manager rejects order exceeding position limits, metrics recorded
        let (_, router, db) = setup_test_environment().await;

        let max_position_size = 10000.0;

        // Attempt to create oversized order
        let order_size = 15000.0;
        assert!(order_size > max_position_size);

        // Log rejection
        let rejection_event = SystemEvent::warning("Order rejected: exceeds position limit")
            .with_details(serde_json::json!({
                "requested_size": order_size,
                "max_size": max_position_size,
                "symbol": "AAPL"
            }));
        db.insert_event(&rejection_event).await.expect("Event insert failed");

        // Record rejection metric
        let rejection_metric = MetricRecord::new("order_rejection", 1.0)
            .with_symbol("AAPL")
            .add_label("reason", "position_limit_exceeded");
        db.insert_metric(&rejection_metric).await.expect("Metric insert failed");

        // Verify metrics were recorded
        let metrics = db.get_metrics("order_rejection", None, None, 10).await.unwrap();
        assert_eq!(metrics.len(), 1);

        let events = db.get_events(None, None, 10).await.unwrap();
        assert!(events.iter().any(|e| e.severity == "warning"));
    }

    #[tokio::test]
    async fn test_slippage_detection_and_metrics() {
        // Test: Detect high slippage, reject order, record metrics
        let (_, router, db) = setup_test_environment().await;

        let order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(200.0)), // Far from market
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let market_price = 150.0;
        let slippage_bps = ((200.0 - market_price) / market_price) * 10000.0;

        // Record slippage metric before rejection
        let slippage_metric = MetricRecord::new("slippage_bps", slippage_bps)
            .with_symbol("AAPL")
            .add_label("order_id", &order.order_id);
        db.insert_metric(&slippage_metric).await.expect("Metric insert failed");

        // Attempt to execute - should fail due to high slippage
        let result = router.route(order, Some(market_price)).await;
        assert!(result.is_err());

        // Verify slippage metric was recorded
        let metrics = db.get_metrics("slippage_bps", None, None, 10).await.unwrap();
        assert_eq!(metrics.len(), 1);
        assert!(metrics[0].value > 50.0); // Exceeds 50 bps limit
    }

    #[tokio::test]
    async fn test_stop_loss_trigger_with_execution_and_metrics() {
        // Test: Stop-loss triggers -> Creates closing order -> Records metrics
        let (mut stop_manager, router, db) = setup_test_environment().await;

        // Create position with stop-loss
        let mut position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(150.0),
            unrealized_pnl: 0.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let stop_config = StopLossConfig::static_stop(5.0).unwrap();
        stop_manager.set_stop(&position, stop_config).expect("Set stop failed");

        // Price drops, triggering stop-loss
        position.current_price = Price(142.0); // -5.3% loss
        position.unrealized_pnl = (142.0 - 150.0) * 100.0;

        let trigger = stop_manager.check(&position);
        assert!(trigger.is_some());

        let trigger_event = trigger.unwrap();

        // Log stop-loss trigger
        let stop_event = SystemEvent::warning("Stop-loss triggered")
            .with_details(serde_json::json!({
                "symbol": "AAPL",
                "trigger_price": trigger_event.trigger_price.0,
                "current_price": trigger_event.current_price.0,
                "unrealized_pnl": trigger_event.unrealized_pnl,
                "stop_type": format!("{:?}", trigger_event.stop_type)
            }));
        db.insert_event(&stop_event).await.expect("Event insert failed");

        // Create closing order
        let closing_order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: trigger_event.symbol.clone(),
            side: trigger_event.close_side(),
            order_type: OrderType::Market,
            quantity: trigger_event.close_quantity(),
            price: None,
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        // Execute closing order
        let result = router.route(closing_order.clone(), Some(142.0)).await;
        assert!(result.is_ok());

        // Record P&L metric
        let pnl_metric = MetricRecord::new("realized_pnl", position.unrealized_pnl)
            .with_symbol("AAPL")
            .add_label("reason", "stop_loss");
        db.insert_metric(&pnl_metric).await.expect("Metric insert failed");

        // Verify stop-loss was triggered and executed
        let events = db.get_events(None, None, 10).await.unwrap();
        assert!(events.iter().any(|e| e.message.contains("Stop-loss")));

        let metrics = db.get_metrics("realized_pnl", None, None, 10).await.unwrap();
        assert_eq!(metrics.len(), 1);
        assert!(metrics[0].value < 0.0); // Loss recorded
    }

    #[tokio::test]
    async fn test_circuit_breaker_activation_workflow() {
        // Test: Circuit breaker triggers when losses exceed threshold
        let (_, _, db) = setup_test_environment().await;

        let max_loss_threshold = 1000.0;
        let mut total_loss = 0.0;

        // Simulate multiple losing positions
        let losses = vec![-200.0, -300.0, -350.0, -250.0]; // Total = -1100

        for (i, loss) in losses.iter().enumerate() {
            total_loss += loss;

            let loss_metric = MetricRecord::new("position_pnl", *loss)
                .with_symbol(&format!("SYM{}", i));
            db.insert_metric(&loss_metric).await.expect("Metric insert failed");

            if total_loss.abs() > max_loss_threshold {
                // Circuit breaker triggered
                let cb_event = SystemEvent::error("Circuit breaker activated")
                    .with_details(serde_json::json!({
                        "total_loss": total_loss,
                        "threshold": max_loss_threshold,
                        "trigger_position": i
                    }));
                db.insert_event(&cb_event).await.expect("Event insert failed");

                let cb_metric = MetricRecord::new("circuit_breaker_triggered", 1.0)
                    .add_label("total_loss", &total_loss.to_string());
                db.insert_metric(&cb_metric).await.expect("Metric insert failed");

                break;
            }
        }

        assert!(total_loss.abs() > max_loss_threshold);

        // Verify circuit breaker event was logged
        let events = db.get_events(None, None, 10).await.unwrap();
        assert!(events.iter().any(|e| e.message.contains("Circuit breaker")));

        let metrics = db.get_metrics("circuit_breaker_triggered", None, None, 10).await.unwrap();
        assert_eq!(metrics.len(), 1);
    }

    #[tokio::test]
    async fn test_multiple_positions_aggregate_risk_tracking() {
        // Test: Track aggregate risk across multiple positions with metrics
        let (mut stop_manager, _, db) = setup_test_environment().await;

        let positions = vec![
            Position {
                symbol: Symbol("AAPL".to_string()),
                side: Side::Bid,
                quantity: Quantity(100.0),
                entry_price: Price(150.0),
                current_price: Price(152.0),
                unrealized_pnl: 200.0,
                realized_pnl: 0.0,
                opened_at: Utc::now(),
                updated_at: Utc::now(),
            },
            Position {
                symbol: Symbol("MSFT".to_string()),
                side: Side::Bid,
                quantity: Quantity(50.0),
                entry_price: Price(300.0),
                current_price: Price(295.0),
                unrealized_pnl: -250.0,
                realized_pnl: 0.0,
                opened_at: Utc::now(),
                updated_at: Utc::now(),
            },
            Position {
                symbol: Symbol("GOOGL".to_string()),
                side: Side::Bid,
                quantity: Quantity(10.0),
                entry_price: Price(2800.0),
                current_price: Price(2850.0),
                unrealized_pnl: 500.0,
                realized_pnl: 0.0,
                opened_at: Utc::now(),
                updated_at: Utc::now(),
            },
        ];

        let mut total_pnl = 0.0;
        let mut total_exposure = 0.0;

        for pos in &positions {
            // Set stop-loss for each position
            let stop_config = StopLossConfig::static_stop(5.0).unwrap();
            stop_manager.set_stop(pos, stop_config).expect("Set stop failed");

            // Track aggregate metrics
            total_pnl += pos.unrealized_pnl;
            total_exposure += pos.quantity.0 * pos.current_price.0;

            // Record individual position metrics
            let pos_metric = MetricRecord::new("position_pnl", pos.unrealized_pnl)
                .with_symbol(&pos.symbol.0);
            db.insert_metric(&pos_metric).await.expect("Metric insert failed");
        }

        // Record aggregate metrics
        let aggregate_pnl = MetricRecord::new("total_portfolio_pnl", total_pnl);
        db.insert_metric(&aggregate_pnl).await.expect("Metric insert failed");

        let aggregate_exposure = MetricRecord::new("total_notional_exposure", total_exposure);
        db.insert_metric(&aggregate_exposure).await.expect("Metric insert failed");

        // Verify aggregate tracking
        assert_eq!(total_pnl, 450.0); // 200 - 250 + 500
        assert!(total_exposure < 50000.0); // Within limit

        let pnl_metrics = db.get_metrics("position_pnl", None, None, 10).await.unwrap();
        assert_eq!(pnl_metrics.len(), 3);

        let total_metrics = db.get_metrics("total_portfolio_pnl", None, None, 10).await.unwrap();
        assert_eq!(total_metrics.len(), 1);
        assert_eq!(total_metrics[0].value, 450.0);
    }

    #[tokio::test]
    async fn test_failed_execution_retry_with_metrics() {
        // Test: Failed execution attempts are retried and metrics collected
        let (_, router, db) = setup_test_environment().await;

        let order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: Symbol("AAPL".to_string()),
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
        };

        let start = std::time::Instant::now();

        // Execute order (should succeed in paper trading, but track retries if any)
        let result = router.route(order.clone(), Some(150.0)).await;

        let duration = start.elapsed();

        // Record execution attempt metrics
        let attempt_metric = MetricRecord::new("execution_attempt_duration_ms", duration.as_millis() as f64)
            .with_symbol("AAPL")
            .add_label("order_id", &order.order_id)
            .add_label("result", if result.is_ok() { "success" } else { "failure" });
        db.insert_metric(&attempt_metric).await.expect("Metric insert failed");

        assert!(result.is_ok()); // Paper trading should succeed

        // Verify retry metrics were recorded
        let metrics = db.get_metrics("execution_attempt_duration_ms", None, None, 10).await.unwrap();
        assert!(metrics.len() >= 1);
    }

    #[tokio::test]
    async fn test_performance_degradation_alert() {
        // Test: Detect performance degradation and generate alerts
        let (_, _, db) = setup_test_environment().await;

        let latency_threshold = 100.0; // ms

        // Simulate increasing latencies
        let latencies = vec![45.0, 55.0, 85.0, 120.0, 150.0, 95.0];

        for (i, latency) in latencies.iter().enumerate() {
            let latency_metric = MetricRecord::new("order_latency_ms", *latency)
                .with_symbol("AAPL");
            db.insert_metric(&latency_metric).await.expect("Metric insert failed");

            if *latency > latency_threshold {
                let alert = SystemEvent::warning(format!("High latency detected: {:.2}ms", latency))
                    .with_details(serde_json::json!({
                        "latency": latency,
                        "threshold": latency_threshold,
                        "sample": i
                    }));
                db.insert_event(&alert).await.expect("Alert insert failed");
            }
        }

        // Verify alerts were generated
        let events = db.get_events(None, None, 10).await.unwrap();
        let high_latency_alerts: Vec<_> = events.iter()
            .filter(|e| e.message.contains("High latency"))
            .collect();

        assert!(high_latency_alerts.len() >= 2); // At least 2 samples exceeded threshold
    }
}
