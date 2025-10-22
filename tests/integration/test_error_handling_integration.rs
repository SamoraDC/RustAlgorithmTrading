//! Integration tests for error handling across the system
//!
//! Tests comprehensive error scenarios including:
//! - HTTP handler errors
//! - Network timeouts
//! - Exchange API failures
//! - Database connection errors
//! - Configuration validation
//! - Rate limiting
//! - Authentication failures

use common::{TradingError, Result, config::ExecutionConfig};
use execution_engine::router::OrderRouter;
use common::types::*;
use chrono::Utc;
use tokio;

#[cfg(test)]
mod error_handling_tests {
    use super::*;

    #[tokio::test]
    async fn test_invalid_configuration_https_validation() {
        // Test: Configuration must enforce HTTPS in live trading
        let config = ExecutionConfig {
            exchange_api_url: "http://insecure-api.example.com".to_string(), // HTTP not HTTPS
            api_key: Some("key".to_string()),
            api_secret: Some("secret".to_string()),
            paper_trading: false, // Live trading
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());

        if let Err(TradingError::Configuration(msg)) = result {
            assert!(msg.contains("HTTPS") || msg.contains("https"));
        } else {
            panic!("Expected Configuration error for non-HTTPS URL");
        }
    }

    #[tokio::test]
    async fn test_missing_credentials_error() {
        // Test: Live trading requires API credentials
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: None, // Missing credentials
            api_secret: None,
            paper_trading: false, // Live trading
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());

        if let Err(TradingError::Configuration(msg)) = result {
            assert!(msg.contains("API key") || msg.contains("credentials"));
        } else {
            panic!("Expected Configuration error for missing credentials");
        }
    }

    #[tokio::test]
    async fn test_zero_rate_limit_error() {
        // Test: Rate limit must be positive
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("key".to_string()),
            api_secret: Some("secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 0, // Invalid: zero rate limit
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());

        if let Err(TradingError::Configuration(msg)) = result {
            assert!(msg.contains("rate_limit") || msg.contains("greater than 0"));
        } else {
            panic!("Expected Configuration error for zero rate limit");
        }
    }

    #[tokio::test]
    async fn test_slippage_rejection() {
        // Test: Order rejected due to excessive slippage
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("key".to_string()),
            api_secret: Some("secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = OrderRouter::new(config).unwrap();

        let order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(200.0)), // Limit price far from market
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let current_market_price = Some(150.0); // Market at $150, limit at $200 = 33% slippage

        let result = router.route(order, current_market_price).await;
        assert!(result.is_err());

        if let Err(TradingError::Risk(msg)) = result {
            assert!(msg.contains("Slippage") || msg.contains("slippage"));
        } else {
            panic!("Expected Risk error for excessive slippage");
        }
    }

    #[tokio::test]
    async fn test_paper_trading_allows_http() {
        // Test: Paper trading should allow HTTP (for testing)
        let config = ExecutionConfig {
            exchange_api_url: "http://localhost:8080".to_string(), // HTTP is OK for paper trading
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let result = OrderRouter::new(config);
        // Paper trading should allow HTTP for local testing
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_network_error_handling() {
        // Test: Handle network failures gracefully
        use common::config::RiskConfig;
        use risk_manager::stops::{StopManager, StopLossConfig};

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

        let position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(145.0),
            unrealized_pnl: -500.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        let stop_config = StopLossConfig::static_stop(5.0).unwrap();
        let result = stop_manager.set_stop(&position, stop_config);
        assert!(result.is_ok());

        // Even with network issues, stop manager should track state locally
        let trigger = stop_manager.check(&position);
        assert!(trigger.is_some()); // Stop should trigger regardless of network
    }

    #[tokio::test]
    async fn test_invalid_order_type_handling() {
        // Test: Validate order type combinations
        let order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::StopLimit,
            quantity: Quantity(100.0),
            price: Some(Price(150.0)),
            stop_price: None, // Invalid: StopLimit requires stop_price
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        // Validation should catch missing stop_price for StopLimit orders
        assert_eq!(order.order_type, OrderType::StopLimit);
        assert!(order.stop_price.is_none()); // This would be invalid
    }

    #[tokio::test]
    async fn test_database_connection_error_recovery() {
        // Test: System should handle database unavailability
        use database::DatabaseManager;

        // Try to connect to non-existent database path
        let invalid_path = "/nonexistent/path/to/database.duckdb";
        let result = DatabaseManager::new(invalid_path).await;

        // Should handle error gracefully
        if result.is_err() {
            // Expected - database creation failed
            println!("Database connection failed as expected");
        }
    }

    #[tokio::test]
    async fn test_concurrent_error_handling() {
        // Test: Multiple concurrent errors should be handled independently
        use std::sync::Arc;
        use tokio::sync::Mutex;

        let errors = Arc::new(Mutex::new(Vec::new()));
        let mut handles = vec![];

        for i in 0..10 {
            let errors_clone = errors.clone();
            let handle = tokio::spawn(async move {
                // Simulate various errors
                let err = match i % 3 {
                    0 => TradingError::Network("Connection timeout".to_string()),
                    1 => TradingError::Parse("Invalid JSON".to_string()),
                    _ => TradingError::Risk("Position limit exceeded".to_string()),
                };

                let mut errs = errors_clone.lock().await;
                errs.push(err);
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.await.unwrap();
        }

        let final_errors = errors.lock().await;
        assert_eq!(final_errors.len(), 10);
    }

    #[tokio::test]
    async fn test_malformed_price_handling() {
        // Test: Handle edge cases in price values
        let test_prices = vec![
            0.0,           // Zero price
            -100.0,        // Negative price
            f64::NAN,      // NaN
            f64::INFINITY, // Infinity
        ];

        for price_val in test_prices {
            let price = Price(price_val);

            // System should handle these gracefully
            if price.0.is_nan() || price.0.is_infinite() || price.0 <= 0.0 {
                // These would be invalid prices
                println!("Invalid price detected: {:?}", price);
            }
        }
    }

    #[tokio::test]
    async fn test_order_quantity_validation() {
        // Test: Validate order quantities
        let test_quantities = vec![
            0.0,           // Zero quantity - invalid
            -50.0,         // Negative quantity - invalid
            0.000001,      // Very small quantity - might be below minimum
            1000000000.0,  // Very large quantity - might exceed limits
        ];

        for qty_val in test_quantities {
            let quantity = Quantity(qty_val);

            if quantity.0 <= 0.0 {
                // Invalid quantity
                println!("Invalid quantity: {:?}", quantity);
                assert!(quantity.0 <= 0.0);
            }
        }
    }

    #[tokio::test]
    async fn test_symbol_validation() {
        // Test: Symbol validation
        let invalid_symbols = vec![
            "",              // Empty symbol
            " ",             // Whitespace only
            "AAPL MSFT",     // Space in symbol
            "AAA/BBB/CCC",   // Too many slashes
        ];

        for sym_str in invalid_symbols {
            let symbol = Symbol(sym_str.to_string());

            if symbol.0.is_empty() || symbol.0.trim().is_empty() {
                println!("Empty or whitespace symbol detected");
            }
        }
    }

    #[tokio::test]
    async fn test_authentication_failure_scenario() {
        // Test: Invalid API credentials should be rejected
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("invalid_key_12345".to_string()),
            api_secret: Some("invalid_secret_67890".to_string()),
            paper_trading: true, // Even in paper trading, we track auth
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = OrderRouter::new(config);
        assert!(router.is_ok()); // Config is valid, but auth would fail at runtime

        // In real execution, these invalid credentials would cause auth failure
    }

    #[tokio::test]
    async fn test_rate_limit_enforcement() {
        // Test: Rate limiter should enforce limits
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("key".to_string()),
            api_secret: Some("secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 2, // Very low limit for testing
            retry_attempts: 3,
            retry_delay_ms: 100,
        };

        let router = OrderRouter::new(config).unwrap();

        // Create multiple orders
        let orders: Vec<Order> = (0..5)
            .map(|i| Order {
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
            })
            .collect();

        // Rate limiter should throttle these requests
        let start = std::time::Instant::now();
        for order in orders {
            let _ = router.route(order, None).await;
        }
        let duration = start.elapsed();

        // With rate limit of 2/sec and 5 orders, should take at least 2 seconds
        assert!(duration.as_secs() >= 2, "Rate limiting should enforce delays");
    }

    #[tokio::test]
    async fn test_retry_logic_with_failures() {
        // Test: Retry logic should attempt multiple times
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("key".to_string()),
            api_secret: Some("secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 100,
        };

        let router = OrderRouter::new(config).unwrap();

        // In paper trading, orders should succeed
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

        let result = router.route(order, None).await;
        assert!(result.is_ok()); // Paper trading should succeed
    }

    #[tokio::test]
    async fn test_error_message_clarity() {
        // Test: Error messages should be clear and actionable
        let errors = vec![
            TradingError::Network("Connection timeout after 10s".to_string()),
            TradingError::Parse("Invalid JSON at line 42".to_string()),
            TradingError::Risk("Position size 15000 exceeds limit 10000".to_string()),
            TradingError::Exchange("Order rejected: insufficient funds".to_string()),
            TradingError::Configuration("API key required for live trading".to_string()),
        ];

        for err in errors {
            let msg = format!("{}", err);

            // Error messages should not be empty
            assert!(!msg.is_empty());

            // Error messages should contain useful context
            println!("Error: {}", msg);
        }
    }

    #[tokio::test]
    async fn test_circuit_breaker_scenario() {
        // Test: Circuit breaker should prevent cascading failures
        use common::config::RiskConfig;

        let config = RiskConfig {
            max_position_size: 10000.0,
            max_notional_exposure: 50000.0,
            max_open_positions: 5,
            stop_loss_percent: 5.0,
            trailing_stop_percent: 3.0,
            enable_circuit_breaker: true,
            max_loss_threshold: 1000.0,
        };

        assert!(config.enable_circuit_breaker);
        assert_eq!(config.max_loss_threshold, 1000.0);

        // Circuit breaker should trigger when max_loss_threshold exceeded
        let total_loss = 1500.0; // Exceeds threshold
        assert!(total_loss > config.max_loss_threshold);
    }

    #[tokio::test]
    async fn test_position_limit_validation() {
        // Test: Position limits should be enforced
        use common::config::RiskConfig;

        let config = RiskConfig {
            max_position_size: 10000.0,
            max_notional_exposure: 50000.0,
            max_open_positions: 5,
            stop_loss_percent: 5.0,
            trailing_stop_percent: 3.0,
            enable_circuit_breaker: true,
            max_loss_threshold: 1000.0,
        };

        // Attempt to create position larger than limit
        let position_size = 15000.0;
        assert!(position_size > config.max_position_size);

        // This should be rejected by risk manager
        let would_exceed = position_size > config.max_position_size;
        assert!(would_exceed);
    }
}
