//! Unit tests for common types module
//!
//! Tests cover:
//! - Type construction and validation
//! - Serialization and deserialization
//! - Display formatting
//! - Edge cases and boundary values

use chrono::Utc;
use common::types::*;

#[cfg(test)]
mod symbol_tests {
    use super::*;

    #[test]
    fn test_symbol_creation() {
        let symbol = Symbol("AAPL".to_string());
        assert_eq!(symbol.0, "AAPL");
    }

    #[test]
    fn test_symbol_display() {
        let symbol = Symbol("BTCUSDT".to_string());
        assert_eq!(format!("{}", symbol), "BTCUSDT");
    }

    #[test]
    fn test_symbol_equality() {
        let s1 = Symbol("MSFT".to_string());
        let s2 = Symbol("MSFT".to_string());
        let s3 = Symbol("GOOGL".to_string());

        assert_eq!(s1, s2);
        assert_ne!(s1, s3);
    }

    #[test]
    fn test_symbol_clone() {
        let s1 = Symbol("AAPL".to_string());
        let s2 = s1.clone();
        assert_eq!(s1, s2);
    }

    #[test]
    fn test_symbol_serialization() {
        let symbol = Symbol("AAPL".to_string());
        let json = serde_json::to_string(&symbol).unwrap();
        assert!(json.contains("AAPL"));

        let deserialized: Symbol = serde_json::from_str(&json).unwrap();
        assert_eq!(symbol, deserialized);
    }

    #[test]
    fn test_symbol_empty_string() {
        let symbol = Symbol("".to_string());
        assert_eq!(symbol.0, "");
    }

    #[test]
    fn test_symbol_special_characters() {
        let symbol = Symbol("BTC-USD".to_string());
        assert_eq!(symbol.0, "BTC-USD");
    }
}

#[cfg(test)]
mod price_tests {
    use super::*;

    #[test]
    fn test_price_creation() {
        let price = Price(100.50);
        assert_eq!(price.0, 100.50);
    }

    #[test]
    fn test_price_display() {
        let price = Price(100.12345678);
        assert_eq!(format!("{}", price), "100.12345678");
    }

    #[test]
    fn test_price_comparison() {
        let p1 = Price(100.0);
        let p2 = Price(100.0);
        let p3 = Price(99.0);

        assert_eq!(p1, p2);
        assert!(p1 > p3);
        assert!(p3 < p1);
    }

    #[test]
    fn test_price_zero() {
        let price = Price(0.0);
        assert_eq!(price.0, 0.0);
    }

    #[test]
    fn test_price_negative() {
        // Negative prices should be allowed (e.g., for spreads, P&L)
        let price = Price(-10.5);
        assert_eq!(price.0, -10.5);
    }

    #[test]
    fn test_price_very_small() {
        let price = Price(0.00000001);
        assert_eq!(price.0, 0.00000001);
    }

    #[test]
    fn test_price_very_large() {
        let price = Price(1_000_000_000.0);
        assert_eq!(price.0, 1_000_000_000.0);
    }

    #[test]
    fn test_price_serialization() {
        let price = Price(123.456);
        let json = serde_json::to_string(&price).unwrap();
        let deserialized: Price = serde_json::from_str(&json).unwrap();
        assert_eq!(price, deserialized);
    }

    #[test]
    fn test_price_ordering() {
        let prices = vec![Price(100.0), Price(50.0), Price(200.0)];
        let mut sorted = prices.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

        assert_eq!(sorted[0], Price(50.0));
        assert_eq!(sorted[1], Price(100.0));
        assert_eq!(sorted[2], Price(200.0));
    }
}

#[cfg(test)]
mod quantity_tests {
    use super::*;

    #[test]
    fn test_quantity_creation() {
        let qty = Quantity(10.5);
        assert_eq!(qty.0, 10.5);
    }

    #[test]
    fn test_quantity_display() {
        let qty = Quantity(100.12345678);
        assert_eq!(format!("{}", qty), "100.12345678");
    }

    #[test]
    fn test_quantity_comparison() {
        let q1 = Quantity(100.0);
        let q2 = Quantity(100.0);
        let q3 = Quantity(50.0);

        assert_eq!(q1, q2);
        assert!(q1 > q3);
    }

    #[test]
    fn test_quantity_zero() {
        let qty = Quantity(0.0);
        assert_eq!(qty.0, 0.0);
    }

    #[test]
    fn test_quantity_fractional() {
        let qty = Quantity(0.00000001);
        assert_eq!(qty.0, 0.00000001);
    }
}

#[cfg(test)]
mod side_tests {
    use super::*;

    #[test]
    fn test_side_variants() {
        let bid = Side::Bid;
        let ask = Side::Ask;

        assert_eq!(bid, Side::Bid);
        assert_eq!(ask, Side::Ask);
        assert_ne!(bid, ask);
    }

    #[test]
    fn test_side_serialization() {
        let bid = Side::Bid;
        let json = serde_json::to_string(&bid).unwrap();
        let deserialized: Side = serde_json::from_str(&json).unwrap();
        assert_eq!(bid, deserialized);
    }
}

#[cfg(test)]
mod order_type_tests {
    use super::*;

    #[test]
    fn test_order_type_variants() {
        assert_eq!(OrderType::Market, OrderType::Market);
        assert_eq!(OrderType::Limit, OrderType::Limit);
        assert_eq!(OrderType::StopMarket, OrderType::StopMarket);
        assert_eq!(OrderType::StopLimit, OrderType::StopLimit);
    }

    #[test]
    fn test_order_type_serialization() {
        let order_type = OrderType::Limit;
        let json = serde_json::to_string(&order_type).unwrap();
        let deserialized: OrderType = serde_json::from_str(&json).unwrap();
        assert_eq!(order_type, deserialized);
    }
}

#[cfg(test)]
mod order_status_tests {
    use super::*;

    #[test]
    fn test_order_status_variants() {
        assert_eq!(OrderStatus::Pending, OrderStatus::Pending);
        assert_eq!(OrderStatus::PartiallyFilled, OrderStatus::PartiallyFilled);
        assert_eq!(OrderStatus::Filled, OrderStatus::Filled);
        assert_eq!(OrderStatus::Cancelled, OrderStatus::Cancelled);
        assert_eq!(OrderStatus::Rejected, OrderStatus::Rejected);
    }

    #[test]
    fn test_order_status_transitions() {
        // Test logical status transitions
        let statuses = vec![
            OrderStatus::Pending,
            OrderStatus::PartiallyFilled,
            OrderStatus::Filled,
        ];
        assert_eq!(statuses.len(), 3);
    }
}

#[cfg(test)]
mod level_tests {
    use super::*;

    #[test]
    fn test_level_creation() {
        let level = Level {
            price: Price(100.0),
            quantity: Quantity(10.0),
            timestamp: Utc::now(),
        };

        assert_eq!(level.price, Price(100.0));
        assert_eq!(level.quantity, Quantity(10.0));
    }

    #[test]
    fn test_level_serialization() {
        let level = Level {
            price: Price(100.0),
            quantity: Quantity(10.0),
            timestamp: Utc::now(),
        };

        let json = serde_json::to_string(&level).unwrap();
        let deserialized: Level = serde_json::from_str(&json).unwrap();

        assert_eq!(level.price, deserialized.price);
        assert_eq!(level.quantity, deserialized.quantity);
    }
}

#[cfg(test)]
mod trade_tests {
    use super::*;

    #[test]
    fn test_trade_creation() {
        let trade = Trade {
            symbol: Symbol("AAPL".to_string()),
            price: Price(150.0),
            quantity: Quantity(100.0),
            side: Side::Bid,
            timestamp: Utc::now(),
            trade_id: "12345".to_string(),
        };

        assert_eq!(trade.symbol, Symbol("AAPL".to_string()));
        assert_eq!(trade.price, Price(150.0));
        assert_eq!(trade.quantity, Quantity(100.0));
    }

    #[test]
    fn test_trade_serialization() {
        let trade = Trade {
            symbol: Symbol("AAPL".to_string()),
            price: Price(150.0),
            quantity: Quantity(100.0),
            side: Side::Bid,
            timestamp: Utc::now(),
            trade_id: "12345".to_string(),
        };

        let json = serde_json::to_string(&trade).unwrap();
        let deserialized: Trade = serde_json::from_str(&json).unwrap();

        assert_eq!(trade.symbol, deserialized.symbol);
        assert_eq!(trade.price, deserialized.price);
    }
}

#[cfg(test)]
mod bar_tests {
    use super::*;

    #[test]
    fn test_bar_creation() {
        let bar = Bar {
            symbol: Symbol("AAPL".to_string()),
            open: Price(100.0),
            high: Price(105.0),
            low: Price(99.0),
            close: Price(103.0),
            volume: Quantity(1000.0),
            timestamp: Utc::now(),
        };

        assert_eq!(bar.open, Price(100.0));
        assert_eq!(bar.high, Price(105.0));
        assert_eq!(bar.low, Price(99.0));
        assert_eq!(bar.close, Price(103.0));
    }

    #[test]
    fn test_bar_ohlc_relationships() {
        let bar = Bar {
            symbol: Symbol("AAPL".to_string()),
            open: Price(100.0),
            high: Price(105.0),
            low: Price(99.0),
            close: Price(103.0),
            volume: Quantity(1000.0),
            timestamp: Utc::now(),
        };

        // High should be >= all other prices
        assert!(bar.high >= bar.open);
        assert!(bar.high >= bar.close);
        assert!(bar.high >= bar.low);

        // Low should be <= all other prices
        assert!(bar.low <= bar.open);
        assert!(bar.low <= bar.close);
        assert!(bar.low <= bar.high);
    }

    #[test]
    fn test_bar_serialization() {
        let bar = Bar {
            symbol: Symbol("AAPL".to_string()),
            open: Price(100.0),
            high: Price(105.0),
            low: Price(99.0),
            close: Price(103.0),
            volume: Quantity(1000.0),
            timestamp: Utc::now(),
        };

        let json = serde_json::to_string(&bar).unwrap();
        let deserialized: Bar = serde_json::from_str(&json).unwrap();

        assert_eq!(bar.symbol, deserialized.symbol);
        assert_eq!(bar.open, deserialized.open);
    }
}

#[cfg(test)]
mod order_tests {
    use super::*;

    #[test]
    fn test_order_creation() {
        let now = Utc::now();
        let order = Order {
            order_id: "ord123".to_string(),
            client_order_id: "client123".to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(150.0)),
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: now,
            updated_at: now,
        };

        assert_eq!(order.symbol, Symbol("AAPL".to_string()));
        assert_eq!(order.quantity, Quantity(100.0));
        assert_eq!(order.status, OrderStatus::Pending);
    }

    #[test]
    fn test_market_order() {
        let order = Order {
            order_id: "ord123".to_string(),
            client_order_id: "client123".to_string(),
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

        assert_eq!(order.order_type, OrderType::Market);
        assert_eq!(order.price, None);
    }

    #[test]
    fn test_limit_order() {
        let order = Order {
            order_id: "ord123".to_string(),
            client_order_id: "client123".to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(150.0)),
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(order.order_type, OrderType::Limit);
        assert!(order.price.is_some());
    }

    #[test]
    fn test_partially_filled_order() {
        let order = Order {
            order_id: "ord123".to_string(),
            client_order_id: "client123".to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(150.0)),
            stop_price: None,
            status: OrderStatus::PartiallyFilled,
            filled_quantity: Quantity(50.0),
            average_price: Some(Price(150.0)),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert!(order.filled_quantity.0 < order.quantity.0);
        assert!(order.filled_quantity.0 > 0.0);
    }
}

#[cfg(test)]
mod position_tests {
    use super::*;

    #[test]
    fn test_position_creation() {
        let position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(155.0),
            unrealized_pnl: 500.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(position.quantity, Quantity(100.0));
        assert_eq!(position.entry_price, Price(150.0));
    }

    #[test]
    fn test_position_pnl_calculation() {
        // Long position with profit
        let position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(155.0),
            unrealized_pnl: (155.0 - 150.0) * 100.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(position.unrealized_pnl, 500.0);
    }

    #[test]
    fn test_position_loss() {
        // Long position with loss
        let position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(145.0),
            unrealized_pnl: (145.0 - 150.0) * 100.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(position.unrealized_pnl, -500.0);
    }
}

#[cfg(test)]
mod signal_tests {
    use super::*;

    #[test]
    fn test_signal_creation() {
        let signal = Signal {
            symbol: Symbol("AAPL".to_string()),
            action: SignalAction::Buy,
            confidence: 0.85,
            features: vec![1.0, 2.0, 3.0],
            timestamp: Utc::now(),
        };

        assert_eq!(signal.action, SignalAction::Buy);
        assert_eq!(signal.confidence, 0.85);
    }

    #[test]
    fn test_signal_confidence_range() {
        let signal = Signal {
            symbol: Symbol("AAPL".to_string()),
            action: SignalAction::Buy,
            confidence: 0.95,
            features: vec![],
            timestamp: Utc::now(),
        };

        assert!(signal.confidence >= 0.0 && signal.confidence <= 1.0);
    }

    #[test]
    fn test_signal_actions() {
        assert_eq!(SignalAction::Buy, SignalAction::Buy);
        assert_eq!(SignalAction::Sell, SignalAction::Sell);
        assert_eq!(SignalAction::Hold, SignalAction::Hold);
        assert_ne!(SignalAction::Buy, SignalAction::Sell);
    }
}
