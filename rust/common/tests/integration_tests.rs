// Integration tests for common types and messaging
use common::types::*;
use common::messaging::*;
use chrono::Utc;

#[cfg(test)]
mod type_tests {
    use super::*;

    #[test]
    fn test_symbol_creation() {
        let symbol = Symbol("AAPL".to_string());
        assert_eq!(symbol.0, "AAPL");
        assert_eq!(format!("{}", symbol), "AAPL");
    }

    #[test]
    fn test_symbol_equality() {
        let sym1 = Symbol("BTCUSDT".to_string());
        let sym2 = Symbol("BTCUSDT".to_string());
        let sym3 = Symbol("ETHUSDT".to_string());

        assert_eq!(sym1, sym2);
        assert_ne!(sym1, sym3);
    }

    #[test]
    fn test_price_operations() {
        let price1 = Price(150.0);
        let price2 = Price(150.0);
        let price3 = Price(151.0);

        assert_eq!(price1, price2);
        assert!(price3 > price1);
        assert!(price1 < price3);
    }

    #[test]
    fn test_price_display() {
        let price = Price(123.456789);
        let display = format!("{}", price);
        // Should display with 8 decimal places
        assert!(display.contains("123.45678900"));
    }

    #[test]
    fn test_quantity_operations() {
        let qty1 = Quantity(100.0);
        let qty2 = Quantity(100.0);
        let qty3 = Quantity(200.0);

        assert_eq!(qty1, qty2);
        assert!(qty3 > qty1);
    }

    #[test]
    fn test_side_enum() {
        let bid = Side::Bid;
        let ask = Side::Ask;

        assert_ne!(bid, ask);
    }

    #[test]
    fn test_order_type_enum() {
        assert_ne!(OrderType::Market, OrderType::Limit);
        assert_ne!(OrderType::StopMarket, OrderType::StopLimit);
    }

    #[test]
    fn test_order_status_enum() {
        let statuses = vec![
            OrderStatus::Pending,
            OrderStatus::PartiallyFilled,
            OrderStatus::Filled,
            OrderStatus::Cancelled,
            OrderStatus::Rejected,
        ];

        for (i, status1) in statuses.iter().enumerate() {
            for (j, status2) in statuses.iter().enumerate() {
                if i == j {
                    assert_eq!(status1, status2);
                } else {
                    assert_ne!(status1, status2);
                }
            }
        }
    }
}

#[cfg(test)]
mod level_tests {
    use super::*;

    #[test]
    fn test_level_creation() {
        let level = Level {
            price: Price(150.0),
            quantity: Quantity(100.0),
            timestamp: Utc::now(),
        };

        assert_eq!(level.price.0, 150.0);
        assert_eq!(level.quantity.0, 100.0);
    }

    #[test]
    fn test_level_serialization() {
        let level = Level {
            price: Price(150.0),
            quantity: Quantity(100.0),
            timestamp: Utc::now(),
        };

        let json = serde_json::to_string(&level).expect("Failed to serialize");
        assert!(json.contains("150"));
        assert!(json.contains("100"));
    }

    #[test]
    fn test_level_deserialization() {
        let json = r#"{
            "price": 150.0,
            "quantity": 100.0,
            "timestamp": "2024-01-01T00:00:00Z"
        }"#;

        let level: Level = serde_json::from_str(json).expect("Failed to deserialize");
        assert_eq!(level.price.0, 150.0);
        assert_eq!(level.quantity.0, 100.0);
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
            quantity: Quantity(10.0),
            side: Side::Bid,
            timestamp: Utc::now(),
            trade_id: "trade_123".to_string(),
        };

        assert_eq!(trade.symbol.0, "AAPL");
        assert_eq!(trade.price.0, 150.0);
        assert_eq!(trade.quantity.0, 10.0);
        assert_eq!(trade.side, Side::Bid);
    }

    #[test]
    fn test_trade_serialization_round_trip() {
        let original = Trade {
            symbol: Symbol("BTCUSDT".to_string()),
            price: Price(50000.0),
            quantity: Quantity(0.5),
            side: Side::Ask,
            timestamp: Utc::now(),
            trade_id: "trade_456".to_string(),
        };

        let json = serde_json::to_string(&original).expect("Failed to serialize");
        let deserialized: Trade = serde_json::from_str(&json).expect("Failed to deserialize");

        assert_eq!(original.symbol, deserialized.symbol);
        assert_eq!(original.price, deserialized.price);
        assert_eq!(original.quantity, deserialized.quantity);
        assert_eq!(original.side, deserialized.side);
    }
}

#[cfg(test)]
mod bar_tests {
    use super::*;

    #[test]
    fn test_bar_creation() {
        let bar = Bar {
            symbol: Symbol("AAPL".to_string()),
            open: Price(150.0),
            high: Price(152.0),
            low: Price(149.0),
            close: Price(151.0),
            volume: Quantity(100000.0),
            timestamp: Utc::now(),
        };

        assert_eq!(bar.symbol.0, "AAPL");
        assert_eq!(bar.open.0, 150.0);
        assert_eq!(bar.high.0, 152.0);
        assert_eq!(bar.low.0, 149.0);
        assert_eq!(bar.close.0, 151.0);
    }

    #[test]
    fn test_bar_high_is_highest() {
        let bar = Bar {
            symbol: Symbol("TEST".to_string()),
            open: Price(100.0),
            high: Price(105.0),
            low: Price(95.0),
            close: Price(102.0),
            volume: Quantity(1000.0),
            timestamp: Utc::now(),
        };

        assert!(bar.high.0 >= bar.open.0);
        assert!(bar.high.0 >= bar.close.0);
        assert!(bar.high.0 >= bar.low.0);
    }

    #[test]
    fn test_bar_low_is_lowest() {
        let bar = Bar {
            symbol: Symbol("TEST".to_string()),
            open: Price(100.0),
            high: Price(105.0),
            low: Price(95.0),
            close: Price(102.0),
            volume: Quantity(1000.0),
            timestamp: Utc::now(),
        };

        assert!(bar.low.0 <= bar.open.0);
        assert!(bar.low.0 <= bar.close.0);
        assert!(bar.low.0 <= bar.high.0);
    }
}

#[cfg(test)]
mod orderbook_tests {
    use super::*;

    #[test]
    fn test_orderbook_creation() {
        let orderbook = OrderBook {
            symbol: Symbol("AAPL".to_string()),
            bids: vec![
                Level {
                    price: Price(150.0),
                    quantity: Quantity(100.0),
                    timestamp: Utc::now(),
                },
            ],
            asks: vec![
                Level {
                    price: Price(150.5),
                    quantity: Quantity(50.0),
                    timestamp: Utc::now(),
                },
            ],
            timestamp: Utc::now(),
            sequence: 1,
        };

        assert_eq!(orderbook.symbol.0, "AAPL");
        assert_eq!(orderbook.bids.len(), 1);
        assert_eq!(orderbook.asks.len(), 1);
    }

    #[test]
    fn test_orderbook_best_bid_ask() {
        let orderbook = OrderBook {
            symbol: Symbol("AAPL".to_string()),
            bids: vec![
                Level {
                    price: Price(150.0),
                    quantity: Quantity(100.0),
                    timestamp: Utc::now(),
                },
                Level {
                    price: Price(149.5),
                    quantity: Quantity(200.0),
                    timestamp: Utc::now(),
                },
            ],
            asks: vec![
                Level {
                    price: Price(150.5),
                    quantity: Quantity(50.0),
                    timestamp: Utc::now(),
                },
                Level {
                    price: Price(151.0),
                    quantity: Quantity(100.0),
                    timestamp: Utc::now(),
                },
            ],
            timestamp: Utc::now(),
            sequence: 1,
        };

        // Best bid should be highest
        assert_eq!(orderbook.bids[0].price.0, 150.0);

        // Best ask should be lowest
        assert_eq!(orderbook.asks[0].price.0, 150.5);
    }
}

#[cfg(test)]
mod order_tests {
    use super::*;

    #[test]
    fn test_order_creation() {
        let order = Order {
            order_id: "order_123".to_string(),
            client_order_id: "client_456".to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(10.0),
            price: Some(Price(150.0)),
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(order.symbol.0, "AAPL");
        assert_eq!(order.quantity.0, 10.0);
        assert_eq!(order.status, OrderStatus::Pending);
    }

    #[test]
    fn test_market_order_no_price() {
        let order = Order {
            order_id: "order_789".to_string(),
            client_order_id: "client_789".to_string(),
            symbol: Symbol("GOOGL".to_string()),
            side: Side::Ask,
            order_type: OrderType::Market,
            quantity: Quantity(5.0),
            price: None, // Market orders don't have limit price
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(order.order_type, OrderType::Market);
        assert!(order.price.is_none());
    }

    #[test]
    fn test_order_partial_fill() {
        let mut order = Order {
            order_id: "order_partial".to_string(),
            client_order_id: "client_partial".to_string(),
            symbol: Symbol("MSFT".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(300.0)),
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        // Simulate partial fill
        order.filled_quantity = Quantity(50.0);
        order.status = OrderStatus::PartiallyFilled;
        order.average_price = Some(Price(299.5));

        assert_eq!(order.filled_quantity.0, 50.0);
        assert_eq!(order.status, OrderStatus::PartiallyFilled);
        assert!(order.filled_quantity.0 < order.quantity.0);
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

        assert_eq!(position.symbol.0, "AAPL");
        assert_eq!(position.quantity.0, 100.0);
        assert_eq!(position.unrealized_pnl, 500.0);
    }

    #[test]
    fn test_position_pnl_calculation() {
        let entry_price = 100.0;
        let current_price = 110.0;
        let quantity = 10.0;

        let expected_pnl = (current_price - entry_price) * quantity;

        let position = Position {
            symbol: Symbol("TEST".to_string()),
            side: Side::Bid,
            quantity: Quantity(quantity),
            entry_price: Price(entry_price),
            current_price: Price(current_price),
            unrealized_pnl: expected_pnl,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(position.unrealized_pnl, 100.0);
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
            features: vec![1.2, 3.4, 5.6],
            timestamp: Utc::now(),
        };

        assert_eq!(signal.symbol.0, "AAPL");
        assert_eq!(signal.action, SignalAction::Buy);
        assert_eq!(signal.confidence, 0.85);
        assert_eq!(signal.features.len(), 3);
    }

    #[test]
    fn test_signal_action_types() {
        let buy_signal = Signal {
            symbol: Symbol("TEST".to_string()),
            action: SignalAction::Buy,
            confidence: 0.9,
            features: vec![],
            timestamp: Utc::now(),
        };

        let sell_signal = Signal {
            symbol: Symbol("TEST".to_string()),
            action: SignalAction::Sell,
            confidence: 0.8,
            features: vec![],
            timestamp: Utc::now(),
        };

        let hold_signal = Signal {
            symbol: Symbol("TEST".to_string()),
            action: SignalAction::Hold,
            confidence: 0.5,
            features: vec![],
            timestamp: Utc::now(),
        };

        assert_eq!(buy_signal.action, SignalAction::Buy);
        assert_eq!(sell_signal.action, SignalAction::Sell);
        assert_eq!(hold_signal.action, SignalAction::Hold);
    }

    #[test]
    fn test_signal_confidence_bounds() {
        let signal = Signal {
            symbol: Symbol("TEST".to_string()),
            action: SignalAction::Buy,
            confidence: 0.75,
            features: vec![],
            timestamp: Utc::now(),
        };

        assert!(signal.confidence >= 0.0);
        assert!(signal.confidence <= 1.0);
    }
}
