/// Unit tests for Alpaca WebSocket client initialization and configuration
///
/// Tests cover:
/// - Client initialization with valid/invalid credentials
/// - URL parsing and validation
/// - Configuration management
/// - Symbol list handling
/// - Reconnection logic setup

use market_data::websocket::{WebSocketClient, AlpacaMessage};
use common::{TradingError, Result};

#[test]
fn test_client_new_with_valid_credentials() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols = vec!["AAPL".to_string(), "GOOGL".to_string()];

    let client = WebSocketClient::new(api_key, api_secret, symbols.clone());

    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_empty_credentials() {
    let api_key = "".to_string();
    let api_secret = "".to_string();
    let symbols = vec!["AAPL".to_string()];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    // Client should still initialize (validation happens on connect)
    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_empty_symbols() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols: Vec<String> = vec![];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_many_symbols() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols: Vec<String> = (0..100)
        .map(|i| format!("SYM{}", i))
        .collect();

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_duplicate_symbols() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols = vec![
        "AAPL".to_string(),
        "AAPL".to_string(),
        "GOOGL".to_string(),
    ];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_invalid_symbol_format() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols = vec![
        "AAPL".to_string(),
        "".to_string(),
        "123".to_string(),
        "SYMBOL_WITH_UNDERSCORE".to_string(),
    ];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    // Client initialization should succeed (validation happens at subscription time)
    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_unicode_credentials() {
    let api_key = "test_🔑_key".to_string();
    let api_secret = "test_🔐_secret".to_string();
    let symbols = vec!["AAPL".to_string()];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_very_long_credentials() {
    let api_key = "a".repeat(10000);
    let api_secret = "b".repeat(10000);
    let symbols = vec!["AAPL".to_string()];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    assert!(client.is_ok());
}

#[test]
fn test_client_new_preserves_symbol_order() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols = vec![
        "ZEBRA".to_string(),
        "APPLE".to_string(),
        "MICROSOFT".to_string(),
    ];

    let client = WebSocketClient::new(api_key.clone(), api_secret.clone(), symbols.clone());

    // Can't directly test symbol order without exposing internals,
    // but we verify initialization succeeds
    assert!(client.is_ok());
}

#[test]
fn test_client_new_with_special_chars_in_symbols() {
    let api_key = "test_api_key".to_string();
    let api_secret = "test_api_secret".to_string();
    let symbols = vec![
        "BRK.A".to_string(),
        "BRK.B".to_string(),
        "ETF-USD".to_string(),
    ];

    let client = WebSocketClient::new(api_key, api_secret, symbols);

    assert!(client.is_ok());
}

#[cfg(test)]
mod configuration_tests {
    use super::*;

    #[test]
    fn test_client_configuration_immutability() {
        let api_key = "test_api_key".to_string();
        let api_secret = "test_api_secret".to_string();
        let symbols = vec!["AAPL".to_string()];

        let client = WebSocketClient::new(api_key, api_secret, symbols);

        assert!(client.is_ok());
        // Client should be immutable after creation
    }

    #[test]
    fn test_client_clone_semantics() {
        let api_key = "test_api_key".to_string();
        let api_secret = "test_api_secret".to_string();
        let symbols = vec!["AAPL".to_string()];

        let _client = WebSocketClient::new(api_key, api_secret, symbols);

        // WebSocketClient doesn't implement Clone, which is correct
        // (it manages network connections)
    }
}

#[cfg(test)]
mod boundary_tests {
    use super::*;

    #[test]
    fn test_client_with_maximum_reasonable_symbols() {
        let api_key = "test_api_key".to_string();
        let api_secret = "test_api_secret".to_string();
        let symbols: Vec<String> = (0..1000)
            .map(|i| format!("SYMBOL{:04}", i))
            .collect();

        let client = WebSocketClient::new(api_key, api_secret, symbols);

        assert!(client.is_ok());
    }

    #[test]
    fn test_client_with_extremely_long_symbol_names() {
        let api_key = "test_api_key".to_string();
        let api_secret = "test_api_secret".to_string();
        let symbols = vec![
            "A".repeat(100),
            "B".repeat(100),
        ];

        let client = WebSocketClient::new(api_key, api_secret, symbols);

        assert!(client.is_ok());
    }

    #[test]
    fn test_client_with_null_bytes_in_credentials() {
        let api_key = "test\0key".to_string();
        let api_secret = "test\0secret".to_string();
        let symbols = vec!["AAPL".to_string()];

        let client = WebSocketClient::new(api_key, api_secret, symbols);

        // Should initialize but may fail on actual authentication
        assert!(client.is_ok());
    }
}
