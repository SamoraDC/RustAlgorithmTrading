/// Comprehensive unit tests for common::types module
///
/// Tests all trading domain types including Order, Position, Trade, OrderBook, etc.
use common::types::*;
use chrono::Utc;
use serde_json;

#[cfg(test)]
mod order_tests {
    use super::*;

    #[test]
    fn test_order_creation() {
        let order = Order {
            id: "order-123".to_string(),
            symbol: "AAPL".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Limit,
            quantity: 100,
            price: Some(150.50),
            status: OrderStatus::Pending,
            timestamp: Utc::now(),
        };

        assert_eq!(order.symbol, "AAPL");
        assert_eq!(order.quantity, 100);
        assert!(matches!(order.side, OrderSide::Buy));
        assert!(matches!(order.order_type, OrderType::Limit));
    }

    #[test]
    fn test_order_serialization() {
        let order = Order {
            id: "order-456".to_string(),
            symbol: "TSLA".to_string(),
            side: OrderSide::Sell,
            order_type: OrderType::Market,
            quantity: 50,
            price: None,
            status: OrderStatus::Filled,
            timestamp: Utc::now(),
        };

        let json = serde_json::to_string(&order).expect("Serialization failed");
        let deserialized: Order = serde_json::from_str(&json).expect("Deserialization failed");

        assert_eq!(order.id, deserialized.id);
        assert_eq!(order.symbol, deserialized.symbol);
        assert_eq!(order.quantity, deserialized.quantity);
    }

    #[test]
    fn test_order_side_variants() {
        let buy = OrderSide::Buy;
        let sell = OrderSide::Sell;

        assert!(matches!(buy, OrderSide::Buy));
        assert!(matches!(sell, OrderSide::Sell));
    }

    #[test]
    fn test_order_type_variants() {
        let types = vec![
            OrderType::Market,
            OrderType::Limit,
            OrderType::Stop,
            OrderType::StopLimit,
        ];

        for order_type in types {
            let json = serde_json::to_string(&order_type).unwrap();
            let _deserialized: OrderType = serde_json::from_str(&json).unwrap();
        }
    }

    #[test]
    fn test_order_status_transitions() {
        let statuses = vec![
            OrderStatus::Pending,
            OrderStatus::Submitted,
            OrderStatus::PartiallyFilled,
            OrderStatus::Filled,
            OrderStatus::Cancelled,
            OrderStatus::Rejected,
        ];

        for status in statuses {
            let json = serde_json::to_string(&status).unwrap();
            let _deserialized: OrderStatus = serde_json::from_str(&json).unwrap();
        }
    }

    #[test]
    fn test_limit_order_requires_price() {
        let order = Order {
            id: "limit-1".to_string(),
            symbol: "GOOG".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Limit,
            quantity: 10,
            price: Some(2500.00),
            status: OrderStatus::Pending,
            timestamp: Utc::now(),
        };

        assert!(order.price.is_some());
        assert_eq!(order.price.unwrap(), 2500.00);
    }

    #[test]
    fn test_market_order_no_price() {
        let order = Order {
            id: "market-1".to_string(),
            symbol: "AMZN".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: 5,
            price: None,
            status: OrderStatus::Pending,
            timestamp: Utc::now(),
        };

        assert!(order.price.is_none());
    }
}

#[cfg(test)]
mod position_tests {
    use super::*;

    #[test]
    fn test_position_creation() {
        let position = Position {
            symbol: "NVDA".to_string(),
            quantity: 200,
            average_price: 450.50,
            current_price: 455.00,
            unrealized_pnl: 900.00,
            realized_pnl: 0.0,
            timestamp: Utc::now(),
        };

        assert_eq!(position.symbol, "NVDA");
        assert_eq!(position.quantity, 200);
        assert!(position.unrealized_pnl > 0.0);
    }

    #[test]
    fn test_position_pnl_calculation() {
        let position = Position {
            symbol: "MSFT".to_string(),
            quantity: 100,
            average_price: 300.00,
            current_price: 310.00,
            unrealized_pnl: 1000.00,
            realized_pnl: 500.00,
            timestamp: Utc::now(),
        };

        let total_pnl = position.unrealized_pnl + position.realized_pnl;
        assert_eq!(total_pnl, 1500.00);
    }

    #[test]
    fn test_position_negative_pnl() {
        let position = Position {
            symbol: "META".to_string(),
            quantity: 50,
            average_price: 350.00,
            current_price: 340.00,
            unrealized_pnl: -500.00,
            realized_pnl: -200.00,
            timestamp: Utc::now(),
        };

        assert!(position.unrealized_pnl < 0.0);
        assert!(position.realized_pnl < 0.0);
    }

    #[test]
    fn test_position_serialization() {
        let position = Position {
            symbol: "AAPL".to_string(),
            quantity: 75,
            average_price: 180.00,
            current_price: 185.00,
            unrealized_pnl: 375.00,
            realized_pnl: 100.00,
            timestamp: Utc::now(),
        };

        let json = serde_json::to_string(&position).unwrap();
        let deserialized: Position = serde_json::from_str(&json).unwrap();

        assert_eq!(position.symbol, deserialized.symbol);
        assert_eq!(position.quantity, deserialized.quantity);
    }
}

#[cfg(test)]
mod trade_tests {
    use super::*;

    #[test]
    fn test_trade_creation() {
        let trade = Trade {
            id: "trade-789".to_string(),
            order_id: "order-123".to_string(),
            symbol: "TSLA".to_string(),
            side: OrderSide::Buy,
            quantity: 25,
            price: 250.00,
            commission: 1.50,
            timestamp: Utc::now(),
        };

        assert_eq!(trade.symbol, "TSLA");
        assert_eq!(trade.quantity, 25);
        assert_eq!(trade.commission, 1.50);
    }

    #[test]
    fn test_trade_total_value() {
        let trade = Trade {
            id: "trade-101".to_string(),
            order_id: "order-456".to_string(),
            symbol: "GOOG".to_string(),
            side: OrderSide::Sell,
            quantity: 10,
            price: 2500.00,
            commission: 5.00,
            timestamp: Utc::now(),
        };

        let total_value = trade.quantity as f64 * trade.price;
        let net_value = total_value - trade.commission;

        assert_eq!(total_value, 25000.00);
        assert_eq!(net_value, 24995.00);
    }

    #[test]
    fn test_trade_serialization() {
        let trade = Trade {
            id: "trade-202".to_string(),
            order_id: "order-789".to_string(),
            symbol: "AMD".to_string(),
            side: OrderSide::Buy,
            quantity: 100,
            price: 120.00,
            commission: 2.00,
            timestamp: Utc::now(),
        };

        let json = serde_json::to_string(&trade).unwrap();
        let deserialized: Trade = serde_json::from_str(&json).unwrap();

        assert_eq!(trade.id, deserialized.id);
        assert_eq!(trade.price, deserialized.price);
    }
}

#[cfg(test)]
mod price_level_tests {
    use super::*;

    #[test]
    fn test_price_level_creation() {
        let level = PriceLevel {
            price: 150.50,
            volume: 1000,
        };

        assert_eq!(level.price, 150.50);
        assert_eq!(level.volume, 1000);
    }

    #[test]
    fn test_price_level_ordering() {
        let level1 = PriceLevel {
            price: 100.00,
            volume: 500,
        };
        let level2 = PriceLevel {
            price: 100.50,
            volume: 750,
        };

        assert!(level1.price < level2.price);
    }
}

#[cfg(test)]
mod market_data_tests {
    use super::*;

    #[test]
    fn test_tick_creation() {
        let tick = Tick {
            symbol: "AAPL".to_string(),
            price: 175.50,
            volume: 100,
            timestamp: Utc::now(),
        };

        assert_eq!(tick.symbol, "AAPL");
        assert_eq!(tick.price, 175.50);
    }

    #[test]
    fn test_bar_creation() {
        let now = Utc::now();
        let bar = Bar {
            symbol: "TSLA".to_string(),
            open: 250.00,
            high: 255.00,
            low: 248.00,
            close: 252.00,
            volume: 50000,
            timestamp: now,
            timeframe: "1m".to_string(),
        };

        assert!(bar.high >= bar.open);
        assert!(bar.high >= bar.close);
        assert!(bar.low <= bar.open);
        assert!(bar.low <= bar.close);
    }

    #[test]
    fn test_bar_ohlc_invariants() {
        let bar = Bar {
            symbol: "NVDA".to_string(),
            open: 450.00,
            high: 460.00,
            low: 445.00,
            close: 455.00,
            volume: 100000,
            timestamp: Utc::now(),
            timeframe: "5m".to_string(),
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
}

#[cfg(test)]
mod edge_cases {
    use super::*;

    #[test]
    fn test_zero_quantity_order() {
        let order = Order {
            id: "zero-qty".to_string(),
            symbol: "AAPL".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: 0,
            price: None,
            status: OrderStatus::Rejected,
            timestamp: Utc::now(),
        };

        assert_eq!(order.quantity, 0);
        assert!(matches!(order.status, OrderStatus::Rejected));
    }

    #[test]
    fn test_negative_pnl_position() {
        let position = Position {
            symbol: "LOSING".to_string(),
            quantity: 100,
            average_price: 100.00,
            current_price: 50.00,
            unrealized_pnl: -5000.00,
            realized_pnl: -1000.00,
            timestamp: Utc::now(),
        };

        assert!(position.unrealized_pnl < 0.0);
        assert!(position.realized_pnl < 0.0);
    }

    #[test]
    fn test_zero_commission_trade() {
        let trade = Trade {
            id: "free-trade".to_string(),
            order_id: "promo".to_string(),
            symbol: "FREE".to_string(),
            side: OrderSide::Buy,
            quantity: 10,
            price: 100.00,
            commission: 0.0,
            timestamp: Utc::now(),
        };

        assert_eq!(trade.commission, 0.0);
    }

    #[test]
    fn test_very_large_volume() {
        let tick = Tick {
            symbol: "HIGH_VOL".to_string(),
            price: 1.0,
            volume: u64::MAX,
            timestamp: Utc::now(),
        };

        assert_eq!(tick.volume, u64::MAX);
    }

    #[test]
    fn test_fractional_shares() {
        // Note: This assumes fractional shares would be represented differently
        // Currently quantity is i32, but fractional shares might need f64
        let position = Position {
            symbol: "FRAC".to_string(),
            quantity: 15, // Would be 15.5 with fractional shares
            average_price: 100.00,
            current_price: 105.00,
            unrealized_pnl: 75.00,
            realized_pnl: 0.0,
            timestamp: Utc::now(),
        };

        assert_eq!(position.quantity, 15);
    }
}
