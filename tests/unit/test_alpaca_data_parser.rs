/// Unit tests for Alpaca data parsing and validation
///
/// Tests cover:
/// - Trade message parsing
/// - Quote message parsing
/// - Bar/OHLCV data parsing
/// - Timestamp parsing and validation
/// - Field validation and edge cases

use market_data::websocket::AlpacaMessage;
use serde_json;

#[test]
fn test_parse_trade_message() {
    let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
    match message.unwrap() {
        AlpacaMessage::Trade { symbol, price, size, .. } => {
            assert_eq!(symbol, "AAPL");
            assert_eq!(price, 150.25);
            assert_eq!(size, 100.0);
        }
        _ => panic!("Expected Trade message"),
    }
}

#[test]
fn test_parse_quote_message() {
    let json = r#"{"T":"q","S":"GOOGL","bp":2800.50,"bs":10,"ap":2801.00,"as":5,"t":"2024-01-01T10:00:00Z"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
    match message.unwrap() {
        AlpacaMessage::Quote { symbol, bid_price, ask_price, .. } => {
            assert_eq!(symbol, "GOOGL");
            assert_eq!(bid_price, 2800.50);
            assert_eq!(ask_price, 2801.00);
        }
        _ => panic!("Expected Quote message"),
    }
}

#[test]
fn test_parse_bar_message() {
    let json = r#"{"T":"b","S":"TSLA","o":700.00,"h":705.50,"l":698.00,"c":703.25,"v":1000000,"t":"2024-01-01T10:00:00Z"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
    match message.unwrap() {
        AlpacaMessage::Bar { symbol, open, high, low, close, volume, .. } => {
            assert_eq!(symbol, "TSLA");
            assert_eq!(open, 700.00);
            assert_eq!(high, 705.50);
            assert_eq!(low, 698.00);
            assert_eq!(close, 703.25);
            assert_eq!(volume, 1000000.0);
        }
        _ => panic!("Expected Bar message"),
    }
}

#[test]
fn test_parse_unknown_message_type() {
    let json = r#"{"T":"unknown","S":"AAPL","data":"something"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
    match message.unwrap() {
        AlpacaMessage::Unknown => {
            // Expected behavior
        }
        _ => panic!("Expected Unknown message type"),
    }
}

#[test]
fn test_parse_message_array() {
    let json = r#"[
        {"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345},
        {"T":"q","S":"GOOGL","bp":2800.50,"bs":10,"ap":2801.00,"as":5,"t":"2024-01-01T10:00:00Z"}
    ]"#;

    let messages: Result<Vec<AlpacaMessage>, _> = serde_json::from_str(json);

    assert!(messages.is_ok());
    assert_eq!(messages.unwrap().len(), 2);
}

#[test]
fn test_parse_trade_with_zero_size() {
    let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":0,"t":"2024-01-01T10:00:00Z","i":12345}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}

#[test]
fn test_parse_trade_with_negative_price() {
    let json = r#"{"T":"t","S":"AAPL","p":-150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    // Parser should accept it (validation happens at business logic layer)
    assert!(message.is_ok());
}

#[test]
fn test_parse_quote_with_inverted_spread() {
    // Bid higher than ask (abnormal but possible in extreme conditions)
    let json = r#"{"T":"q","S":"AAPL","bp":150.10,"bs":10,"ap":150.00,"as":5,"t":"2024-01-01T10:00:00Z"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}

#[test]
fn test_parse_bar_with_invalid_ohlc() {
    // High lower than low (invalid but parser should accept)
    let json = r#"{"T":"b","S":"AAPL","o":150.00,"h":149.00,"l":151.00,"c":150.50,"v":1000,"t":"2024-01-01T10:00:00Z"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}

#[test]
fn test_parse_message_with_missing_fields() {
    let json = r#"{"T":"t","S":"AAPL"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_err());
}

#[test]
fn test_parse_message_with_extra_fields() {
    let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345,"extra":"field","another":true}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}

#[cfg(test)]
mod timestamp_parsing {
    use super::*;

    #[test]
    fn test_parse_iso8601_timestamp() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_timestamp_with_milliseconds() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00.123Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_timestamp_with_microseconds() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00.123456Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_timestamp_with_timezone() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00-05:00","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }
}

#[cfg(test)]
mod field_validation {
    use super::*;

    #[test]
    fn test_parse_symbol_with_dots() {
        let json = r#"{"T":"t","S":"BRK.A","p":500000.00,"s":1,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_symbol_with_hyphens() {
        let json = r#"{"T":"t","S":"SPY-USD","p":450.00,"s":100,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_very_large_trade_size() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":1000000000,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_fractional_shares() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":0.5,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_very_small_price() {
        let json = r#"{"T":"t","S":"PENNY","p":0.0001,"s":100000,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }

    #[test]
    fn test_parse_very_large_price() {
        let json = r#"{"T":"t","S":"BRK.A","p":500000.00,"s":1,"t":"2024-01-01T10:00:00Z","i":12345}"#;
        let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

        assert!(message.is_ok());
    }
}

#[test]
fn test_parse_malformed_json() {
    let json = r#"{"T":"t","S":"AAPL","p":150.25,"#; // Incomplete JSON
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_err());
}

#[test]
fn test_parse_empty_string() {
    let json = "";
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_err());
}

#[test]
fn test_parse_null_json() {
    let json = "null";
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_err());
}

#[test]
fn test_serialization_roundtrip() {
    let original = r#"{"T":"t","S":"AAPL","p":150.25,"s":100.0,"t":"2024-01-01T10:00:00Z","i":12345}"#;
    let message: AlpacaMessage = serde_json::from_str(original).unwrap();
    let serialized = serde_json::to_string(&message).unwrap();
    let deserialized: AlpacaMessage = serde_json::from_str(&serialized).unwrap();

    // Both deserializations should succeed
    match (message, deserialized) {
        (AlpacaMessage::Trade { .. }, AlpacaMessage::Trade { .. }) => {},
        _ => panic!("Serialization roundtrip failed"),
    }
}

#[test]
fn test_parse_unicode_symbol() {
    let json = r#"{"T":"t","S":"股票","p":150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}

#[test]
fn test_parse_message_with_scientific_notation() {
    let json = r#"{"T":"t","S":"AAPL","p":1.5025e2,"s":1e2,"t":"2024-01-01T10:00:00Z","i":12345}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}

#[test]
fn test_parse_bar_with_zero_volume() {
    let json = r#"{"T":"b","S":"AAPL","o":150.00,"h":150.00,"l":150.00,"c":150.00,"v":0,"t":"2024-01-01T10:00:00Z"}"#;
    let message: Result<AlpacaMessage, _> = serde_json::from_str(json);

    assert!(message.is_ok());
}
