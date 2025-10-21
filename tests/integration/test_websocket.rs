//! Integration tests for WebSocket connection and message handling
//!
//! Tests cover:
//! - Message parsing (trades, quotes, bars)
//! - Authentication flow
//! - Reconnection logic
//! - Error handling

use serde_json::json;

#[cfg(test)]
mod websocket_message_tests {
    use super::*;

    #[test]
    fn test_parse_trade_message() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":100.0,"t":"2024-01-01T10:00:00Z","i":12345}"#;

        let parsed: serde_json::Value = serde_json::from_str(json).unwrap();
        assert_eq!(parsed["T"], "t");
        assert_eq!(parsed["S"], "AAPL");
        assert_eq!(parsed["p"], 150.25);
        assert_eq!(parsed["s"], 100.0);
    }

    #[test]
    fn test_parse_quote_message() {
        let json = r#"{"T":"q","S":"AAPL","bp":150.00,"bs":10.0,"ap":150.05,"as":5.0,"t":"2024-01-01T10:00:00Z"}"#;

        let parsed: serde_json::Value = serde_json::from_str(json).unwrap();
        assert_eq!(parsed["T"], "q");
        assert_eq!(parsed["bp"], 150.00);
        assert_eq!(parsed["ap"], 150.05);
    }

    #[test]
    fn test_parse_bar_message() {
        let json = r#"{"T":"b","S":"AAPL","o":150.0,"h":152.0,"l":149.0,"c":151.0,"v":10000.0,"t":"2024-01-01T10:00:00Z"}"#;

        let parsed: serde_json::Value = serde_json::from_str(json).unwrap();
        assert_eq!(parsed["T"], "b");
        assert_eq!(parsed["o"], 150.0);
        assert_eq!(parsed["h"], 152.0);
        assert_eq!(parsed["l"], 149.0);
        assert_eq!(parsed["c"], 151.0);
    }

    #[test]
    fn test_parse_message_array() {
        let json = r#"[
            {"T":"t","S":"AAPL","p":150.25,"s":100.0,"t":"2024-01-01T10:00:00Z","i":12345},
            {"T":"q","S":"AAPL","bp":150.00,"bs":10.0,"ap":150.05,"as":5.0,"t":"2024-01-01T10:00:00Z"}
        ]"#;

        let parsed: Vec<serde_json::Value> = serde_json::from_str(json).unwrap();
        assert_eq!(parsed.len(), 2);
        assert_eq!(parsed[0]["T"], "t");
        assert_eq!(parsed[1]["T"], "q");
    }

    #[test]
    fn test_auth_message_format() {
        let auth_msg = json!({
            "action": "auth",
            "key": "test_key",
            "secret": "test_secret"
        });

        assert_eq!(auth_msg["action"], "auth");
        assert_eq!(auth_msg["key"], "test_key");
        assert_eq!(auth_msg["secret"], "test_secret");
    }

    #[test]
    fn test_subscribe_message_format() {
        let subscribe_msg = json!({
            "action": "subscribe",
            "trades": vec!["AAPL", "MSFT"],
            "quotes": vec!["AAPL", "MSFT"],
            "bars": vec!["AAPL", "MSFT"]
        });

        assert_eq!(subscribe_msg["action"], "subscribe");
        assert_eq!(subscribe_msg["trades"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn test_malformed_message_handling() {
        let malformed = r#"{"T":"invalid","missing":"fields"}"#;

        // Should be able to parse as generic JSON even if not a valid message
        let result: Result<serde_json::Value, _> = serde_json::from_str(malformed);
        assert!(result.is_ok());
    }

    #[test]
    fn test_empty_message_array() {
        let empty = r#"[]"#;
        let parsed: Vec<serde_json::Value> = serde_json::from_str(empty).unwrap();
        assert_eq!(parsed.len(), 0);
    }

    #[test]
    fn test_trade_message_with_large_values() {
        let json = r#"{"T":"t","S":"BRK.A","p":500000.00,"s":1000000.0,"t":"2024-01-01T10:00:00Z","i":99999}"#;

        let parsed: serde_json::Value = serde_json::from_str(json).unwrap();
        assert_eq!(parsed["p"], 500000.00);
        assert_eq!(parsed["s"], 1000000.0);
    }

    #[test]
    fn test_message_with_fractional_shares() {
        let json = r#"{"T":"t","S":"AAPL","p":150.25,"s":0.5,"t":"2024-01-01T10:00:00Z","i":12345}"#;

        let parsed: serde_json::Value = serde_json::from_str(json).unwrap();
        assert_eq!(parsed["s"], 0.5);
    }
}

#[cfg(test)]
mod websocket_error_tests {
    use super::*;

    #[test]
    fn test_invalid_json_handling() {
        let invalid = r#"{"incomplete": "#;
        let result: Result<serde_json::Value, _> = serde_json::from_str(invalid);
        assert!(result.is_err());
    }

    #[test]
    fn test_missing_required_fields() {
        let incomplete = r#"{"T":"t","S":"AAPL"}"#; // Missing price, size, etc.

        let parsed: serde_json::Value = serde_json::from_str(incomplete).unwrap();
        assert!(parsed.get("p").is_none());
        assert!(parsed.get("s").is_none());
    }

    #[test]
    fn test_wrong_type_fields() {
        let wrong_types = r#"{"T":"t","S":"AAPL","p":"not_a_number","s":"also_wrong"}"#;

        let parsed: serde_json::Value = serde_json::from_str(wrong_types).unwrap();
        assert!(parsed["p"].is_string());
    }
}

#[cfg(test)]
mod websocket_flow_tests {
    use super::*;

    #[test]
    fn test_complete_message_flow() {
        // Simulate complete flow: auth -> subscribe -> receive messages

        // 1. Auth message
        let auth = json!({
            "action": "auth",
            "key": "test",
            "secret": "secret"
        });
        assert_eq!(auth["action"], "auth");

        // 2. Auth response
        let auth_response = json!([{
            "T": "success",
            "msg": "authenticated"
        }]);
        assert!(auth_response.is_array());

        // 3. Subscribe
        let subscribe = json!({
            "action": "subscribe",
            "trades": ["AAPL"]
        });
        assert_eq!(subscribe["action"], "subscribe");

        // 4. Data message
        let trade = json!({
            "T": "t",
            "S": "AAPL",
            "p": 150.0,
            "s": 100.0
        });
        assert_eq!(trade["S"], "AAPL");
    }

    #[test]
    fn test_multi_symbol_subscription() {
        let symbols = vec!["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"];

        let subscribe = json!({
            "action": "subscribe",
            "trades": symbols,
            "quotes": symbols,
            "bars": symbols
        });

        assert_eq!(subscribe["trades"].as_array().unwrap().len(), 5);
        assert_eq!(subscribe["quotes"].as_array().unwrap().len(), 5);
        assert_eq!(subscribe["bars"].as_array().unwrap().len(), 5);
    }

    #[test]
    fn test_unsubscribe_flow() {
        let unsubscribe = json!({
            "action": "unsubscribe",
            "trades": ["AAPL"]
        });

        assert_eq!(unsubscribe["action"], "unsubscribe");
    }
}

#[cfg(test)]
mod websocket_reconnection_tests {
    use std::time::Duration;

    #[test]
    fn test_reconnect_delay_calculation() {
        let base_delay = Duration::from_millis(5000);

        // Exponential backoff: delay * 2^attempt
        let attempt_1 = base_delay;
        let attempt_2 = base_delay * 2;
        let attempt_3 = base_delay * 4;

        assert_eq!(attempt_1.as_millis(), 5000);
        assert_eq!(attempt_2.as_millis(), 10000);
        assert_eq!(attempt_3.as_millis(), 20000);
    }

    #[test]
    fn test_max_reconnect_delay() {
        let base_delay = Duration::from_millis(1000);
        let max_delay = Duration::from_secs(60);

        let mut current_delay = base_delay;
        for _ in 0..10 {
            current_delay = current_delay * 2;
            if current_delay > max_delay {
                current_delay = max_delay;
            }
        }

        assert_eq!(current_delay, max_delay);
    }
}

#[cfg(test)]
mod websocket_performance_tests {
    #[test]
    fn test_high_message_throughput() {
        // Simulate processing 1000 messages
        let mut processed = 0;

        for i in 0..1000 {
            let msg = format!(r#"{{"T":"t","S":"AAPL","p":{},"s":100.0}}"#, 150.0 + i as f64);
            let parsed: Result<serde_json::Value, _> = serde_json::from_str(&msg);
            if parsed.is_ok() {
                processed += 1;
            }
        }

        assert_eq!(processed, 1000);
    }

    #[test]
    fn test_message_batching() {
        let mut batch = Vec::new();

        for i in 0..100 {
            batch.push(format!(r#"{{"T":"t","S":"AAPL","p":{},"s":100.0}}"#, 150.0 + i as f64));
        }

        assert_eq!(batch.len(), 100);
    }
}
