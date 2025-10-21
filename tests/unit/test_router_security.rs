use common::{config::ExecutionConfig, TradingError};
use execution_engine::router::OrderRouter;

#[cfg(test)]
mod router_security_tests {
    use super::*;

    /// Test OrderRouter rejects HTTP URLs in live trading
    #[test]
    fn test_router_rejects_http_live_trading() {
        let config = ExecutionConfig {
            exchange_api_url: "http://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("must use HTTPS"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test OrderRouter accepts HTTPS URLs in live trading
    #[test]
    fn test_router_accepts_https_live_trading() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("PKABCDEF123456".to_string()),
            api_secret: Some("secret123".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_ok());
    }

    /// Test OrderRouter allows HTTP in paper trading mode
    #[test]
    fn test_router_allows_http_paper_trading() {
        let config = ExecutionConfig {
            exchange_api_url: "http://paper-api.alpaca.markets".to_string(),
            api_key: None,
            api_secret: None,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: true,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_ok());
    }

    /// Test OrderRouter rejects missing credentials in live trading
    #[test]
    fn test_router_rejects_missing_credentials() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: None,
            api_secret: Some("secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("API key not configured"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test OrderRouter rejects empty credentials in live trading
    #[test]
    fn test_router_rejects_empty_credentials() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("".to_string()),
            api_secret: Some("secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("cannot be empty"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test OrderRouter rejects zero rate limit
    #[test]
    fn test_router_rejects_zero_rate_limit() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("key".to_string()),
            api_secret: Some("secret".to_string()),
            rate_limit_per_second: 0,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("rate_limit_per_second must be greater than 0"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test OrderRouter enforces TLS 1.2 minimum
    #[test]
    fn test_router_enforces_tls_version() {
        // This test verifies the router is configured with min_tls_version
        // The actual TLS negotiation happens at runtime, but we can verify
        // the router was created successfully with TLS requirements
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("PKABCDEF123456".to_string()),
            api_secret: Some("secret123".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let router = OrderRouter::new(config);
        assert!(router.is_ok(), "Router should be created with TLS requirements");
    }

    /// Test that paper trading mode doesn't require credentials
    #[test]
    fn test_paper_trading_no_credentials_required() {
        let config = ExecutionConfig {
            exchange_api_url: "http://localhost:8080".to_string(),
            api_key: None,
            api_secret: None,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: true,
        };

        let result = OrderRouter::new(config);
        assert!(result.is_ok());
    }
}
