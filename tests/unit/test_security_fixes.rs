use common::{config::ExecutionConfig, TradingError};

#[cfg(test)]
mod security_tests {
    use super::*;

    /// Test HTTPS validation for live trading
    #[test]
    fn test_https_validation_live_trading() {
        let mut config = ExecutionConfig {
            exchange_api_url: "http://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        // Should fail for HTTP URL in live trading
        let result = config.validate_https();
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), TradingError::Configuration(_)));

        // Should pass for HTTPS URL
        config.exchange_api_url = "https://api.alpaca.markets".to_string();
        let result = config.validate_https();
        assert!(result.is_ok());
    }

    /// Test HTTPS validation allows HTTP in paper trading
    #[test]
    fn test_https_validation_paper_trading() {
        let config = ExecutionConfig {
            exchange_api_url: "http://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: true,
        };

        // Should pass for HTTP URL in paper trading
        let result = config.validate_https();
        assert!(result.is_ok());
    }

    /// Test credential validation rejects missing API key
    #[test]
    fn test_credential_validation_missing_key() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: None,
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate_credentials();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("API key not configured"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test credential validation rejects missing API secret
    #[test]
    fn test_credential_validation_missing_secret() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: None,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate_credentials();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("API secret not configured"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test credential validation rejects empty API key
    #[test]
    fn test_credential_validation_empty_key() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("   ".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate_credentials();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("API key cannot be empty"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test credential validation rejects empty API secret
    #[test]
    fn test_credential_validation_empty_secret() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate_credentials();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("API secret cannot be empty"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test credential validation passes with valid credentials
    #[test]
    fn test_credential_validation_valid() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("PKABCDEF123456".to_string()),
            api_secret: Some("secret123".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate_credentials();
        assert!(result.is_ok());
    }

    /// Test credential validation is skipped in paper trading
    #[test]
    fn test_credential_validation_paper_trading() {
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: None,
            api_secret: None,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: true,
        };

        // Should pass even without credentials in paper trading mode
        let result = config.validate_credentials();
        assert!(result.is_ok());
    }

    /// Test load_credentials validates empty values from environment
    #[test]
    fn test_load_credentials_validates_empty() {
        use std::env;

        // Set empty environment variable
        env::set_var("ALPACA_API_KEY", "   ");
        env::set_var("ALPACA_SECRET_KEY", "secret");

        let mut config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: None,
            api_secret: None,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.load_credentials();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("ALPACA_API_KEY cannot be empty"));
            }
            _ => panic!("Expected Configuration error"),
        }

        // Clean up
        env::remove_var("ALPACA_API_KEY");
        env::remove_var("ALPACA_SECRET_KEY");
    }

    /// Test load_credentials validates both keys
    #[test]
    fn test_load_credentials_validates_both() {
        use std::env;

        // Set valid environment variables
        env::set_var("ALPACA_API_KEY", "PKABCDEF123456");
        env::set_var("ALPACA_SECRET_KEY", "secret123");

        let mut config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: None,
            api_secret: None,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.load_credentials();
        assert!(result.is_ok());
        assert!(config.api_key.is_some());
        assert!(config.api_secret.is_some());
        assert_eq!(config.api_key.unwrap(), "PKABCDEF123456");
        assert_eq!(config.api_secret.unwrap(), "secret123");

        // Clean up
        env::remove_var("ALPACA_API_KEY");
        env::remove_var("ALPACA_SECRET_KEY");
    }

    /// Test that error messages don't leak credentials
    #[test]
    fn test_error_messages_no_credential_leak() {
        let config = ExecutionConfig {
            exchange_api_url: "http://api.alpaca.markets".to_string(),
            api_key: Some("SUPER_SECRET_KEY_12345".to_string()),
            api_secret: Some("SUPER_SECRET_VALUE_67890".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate_https();
        assert!(result.is_err());

        let error_msg = format!("{}", result.unwrap_err());
        // Error message should mention the URL but not credentials
        assert!(error_msg.contains("http://api.alpaca.markets"));
        assert!(!error_msg.contains("SUPER_SECRET_KEY"));
        assert!(!error_msg.contains("SUPER_SECRET_VALUE"));
    }

    /// Test rate_limit_per_second validation
    #[test]
    fn test_rate_limit_validation() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 0,
            retry_attempts: 3,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("rate_limit_per_second must be at least 1"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test retry_attempts validation
    #[test]
    fn test_retry_attempts_validation() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 0,
            retry_delay_ms: 1000,
            paper_trading: false,
        };

        let result = config.validate();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("retry_attempts must be at least 1"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }

    /// Test retry_delay_ms validation
    #[test]
    fn test_retry_delay_validation() {
        let config = ExecutionConfig {
            exchange_api_url: "https://api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 50,
            paper_trading: false,
        };

        let result = config.validate();
        assert!(result.is_err());
        match result.unwrap_err() {
            TradingError::Configuration(msg) => {
                assert!(msg.contains("retry_delay_ms must be at least 100ms"));
            }
            _ => panic!("Expected Configuration error"),
        }
    }
}
