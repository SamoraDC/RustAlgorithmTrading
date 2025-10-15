//! Unit tests for error handling module
//!
//! Tests cover:
//! - Error type creation and matching
//! - Error message formatting
//! - Error conversion (From trait)
//! - Error propagation

use common::errors::*;
use std::io;

#[cfg(test)]
mod error_tests {
    use super::*;

    #[test]
    fn test_market_data_error() {
        let err = TradingError::MarketData("Invalid data".to_string());
        assert!(matches!(err, TradingError::MarketData(_)));
        assert_eq!(err.to_string(), "Market data error: Invalid data");
    }

    #[test]
    fn test_websocket_error() {
        let err = TradingError::WebSocket("Connection failed".to_string());
        assert!(matches!(err, TradingError::WebSocket(_)));
        assert_eq!(err.to_string(), "WebSocket error: Connection failed");
    }

    #[test]
    fn test_order_validation_error() {
        let err = TradingError::OrderValidation("Invalid quantity".to_string());
        assert!(matches!(err, TradingError::OrderValidation(_)));
        assert_eq!(err.to_string(), "Order validation error: Invalid quantity");
    }

    #[test]
    fn test_risk_check_error() {
        let err = TradingError::RiskCheck("Position limit exceeded".to_string());
        assert!(matches!(err, TradingError::RiskCheck(_)));
        assert_eq!(err.to_string(), "Risk check failed: Position limit exceeded");
    }

    #[test]
    fn test_execution_error() {
        let err = TradingError::Execution("Order rejected".to_string());
        assert!(matches!(err, TradingError::Execution(_)));
        assert_eq!(err.to_string(), "Execution error: Order rejected");
    }

    #[test]
    fn test_messaging_error() {
        let err = TradingError::Messaging("ZMQ connection lost".to_string());
        assert!(matches!(err, TradingError::Messaging(_)));
        assert_eq!(err.to_string(), "Messaging error: ZMQ connection lost");
    }

    #[test]
    fn test_configuration_error() {
        let err = TradingError::Configuration("Missing API key".to_string());
        assert!(matches!(err, TradingError::Configuration(_)));
        assert_eq!(err.to_string(), "Configuration error: Missing API key");
    }

    #[test]
    fn test_unknown_error() {
        let err = TradingError::Unknown("Unexpected error".to_string());
        assert!(matches!(err, TradingError::Unknown(_)));
        assert_eq!(err.to_string(), "Unknown error: Unexpected error");
    }

    #[test]
    fn test_serialization_error_conversion() {
        let json_err = serde_json::from_str::<String>("invalid json");
        assert!(json_err.is_err());

        if let Err(e) = json_err {
            let trading_err: TradingError = e.into();
            assert!(matches!(trading_err, TradingError::Serialization(_)));
        }
    }

    #[test]
    fn test_io_error_conversion() {
        let io_err = io::Error::new(io::ErrorKind::NotFound, "File not found");
        let trading_err: TradingError = io_err.into();
        assert!(matches!(trading_err, TradingError::Io(_)));
    }

    #[test]
    fn test_error_debug_format() {
        let err = TradingError::RiskCheck("Test error".to_string());
        let debug_str = format!("{:?}", err);
        assert!(debug_str.contains("RiskCheck"));
        assert!(debug_str.contains("Test error"));
    }

    #[test]
    fn test_result_type_ok() {
        let result: Result<i32> = Ok(42);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 42);
    }

    #[test]
    fn test_result_type_err() {
        let result: Result<i32> = Err(TradingError::Unknown("Error".to_string()));
        assert!(result.is_err());
    }

    #[test]
    fn test_error_chain() {
        fn inner() -> Result<()> {
            Err(TradingError::MarketData("Inner error".to_string()))
        }

        fn outer() -> Result<()> {
            inner()?;
            Ok(())
        }

        let result = outer();
        assert!(result.is_err());
        if let Err(e) = result {
            assert!(matches!(e, TradingError::MarketData(_)));
        }
    }

    #[test]
    fn test_multiple_error_types() {
        let errors = vec![
            TradingError::MarketData("Error 1".to_string()),
            TradingError::WebSocket("Error 2".to_string()),
            TradingError::RiskCheck("Error 3".to_string()),
        ];

        assert_eq!(errors.len(), 3);
        assert!(matches!(errors[0], TradingError::MarketData(_)));
        assert!(matches!(errors[1], TradingError::WebSocket(_)));
        assert!(matches!(errors[2], TradingError::RiskCheck(_)));
    }

    #[test]
    fn test_error_message_contents() {
        let err = TradingError::OrderValidation("Price must be positive".to_string());
        let msg = err.to_string();
        assert!(msg.contains("Order validation"));
        assert!(msg.contains("Price must be positive"));
    }

    #[test]
    fn test_error_equality_check() {
        // Test that errors can be pattern matched
        let err = TradingError::RiskCheck("Limit exceeded".to_string());

        match err {
            TradingError::RiskCheck(msg) => {
                assert_eq!(msg, "Limit exceeded");
            }
            _ => panic!("Wrong error type"),
        }
    }
}
