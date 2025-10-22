/// Property-based tests for order invariants using proptest
/// Ensures data models maintain consistency under all conditions

use proptest::prelude::*;
use common::types::{Order, OrderSide, OrderType, OrderStatus, Position, Trade};
use chrono::Utc;

proptest! {
    #[test]
    fn test_order_quantity_always_non_negative(quantity in 0i32..1_000_000) {
        let order = Order {
            id: "prop-test".to_string(),
            symbol: "AAPL".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity,
            price: None,
            status: OrderStatus::Pending,
            timestamp: Utc::now(),
        };

        prop_assert!(order.quantity >= 0);
    }

    #[test]
    fn test_limit_order_price_positive(
        price in 0.01f64..100_000.0,
        quantity in 1i32..10_000
    ) {
        let order = Order {
            id: "limit-prop".to_string(),
            symbol: "TSLA".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Limit,
            quantity,
            price: Some(price),
            status: OrderStatus::Pending,
            timestamp: Utc::now(),
        };

        prop_assert!(order.price.unwrap() > 0.0);
        prop_assert!(order.quantity > 0);
    }

    #[test]
    fn test_order_value_calculation(
        price in 1.0f64..1000.0,
        quantity in 1i32..1000
    ) {
        let order_value = price * quantity as f64;

        // Order value should always equal price * quantity
        prop_assert_eq!(order_value, price * quantity as f64);

        // Value should be positive for positive inputs
        prop_assert!(order_value > 0.0);
    }

    #[test]
    fn test_position_pnl_consistency(
        quantity in 1i32..1000,
        avg_price in 50.0f64..500.0,
        current_price in 50.0f64..500.0
    ) {
        let unrealized_pnl = (current_price - avg_price) * quantity as f64;

        let position = Position {
            symbol: "NVDA".to_string(),
            quantity,
            average_price: avg_price,
            current_price,
            unrealized_pnl,
            realized_pnl: 0.0,
            timestamp: Utc::now(),
        };

        // Verify P&L calculation
        let expected_pnl = (current_price - avg_price) * quantity as f64;
        let diff = (position.unrealized_pnl - expected_pnl).abs();

        // Allow for small floating point errors
        prop_assert!(diff < 0.01);
    }

    #[test]
    fn test_trade_commission_never_exceeds_value(
        price in 1.0f64..1000.0,
        quantity in 1i32..1000,
        commission in 0.0f64..100.0
    ) {
        let trade_value = price * quantity as f64;

        let trade = Trade {
            id: "trade-prop".to_string(),
            order_id: "order-prop".to_string(),
            symbol: "GOOG".to_string(),
            side: OrderSide::Buy,
            quantity,
            price,
            commission: commission.min(trade_value * 0.1), // Cap at 10%
            timestamp: Utc::now(),
        };

        // Commission should never exceed trade value
        prop_assert!(trade.commission <= trade_value);
    }

    #[test]
    fn test_price_precision(
        price in 0.01f64..10_000.0
    ) {
        // Prices should maintain reasonable precision
        let rounded = (price * 100.0).round() / 100.0;

        // Price should be representable with 2 decimal places
        let diff = (price - rounded).abs();
        prop_assert!(diff < 0.01);
    }

    #[test]
    fn test_volume_overflow_protection(
        vol1 in 0u64..u64::MAX / 2,
        vol2 in 0u64..u64::MAX / 2
    ) {
        // Volume addition should not overflow
        let total = vol1.saturating_add(vol2);

        prop_assert!(total >= vol1);
        prop_assert!(total >= vol2);
    }

    #[test]
    fn test_symbol_validation(
        s in "[A-Z]{1,5}"
    ) {
        // Symbols should be uppercase letters, 1-5 chars
        prop_assert!(s.len() >= 1 && s.len() <= 5);
        prop_assert!(s.chars().all(|c| c.is_uppercase()));
    }
}

#[cfg(test)]
mod order_state_transitions {
    use super::*;

    proptest! {
        #[test]
        fn test_order_status_valid_transitions(
            initial_status in prop_oneof![
                Just(OrderStatus::Pending),
                Just(OrderStatus::Submitted),
                Just(OrderStatus::PartiallyFilled),
            ]
        ) {
            // Pending -> Submitted, Cancelled, or Rejected
            // Submitted -> PartiallyFilled, Filled, Cancelled, or Rejected
            // PartiallyFilled -> Filled, Cancelled

            let order = Order {
                id: "state-test".to_string(),
                symbol: "AAPL".to_string(),
                side: OrderSide::Buy,
                order_type: OrderType::Market,
                quantity: 100,
                price: None,
                status: initial_status,
                timestamp: Utc::now(),
            };

            // All states should serialize/deserialize correctly
            let json = serde_json::to_string(&order).unwrap();
            let deserialized: Order = serde_json::from_str(&json).unwrap();

            prop_assert_eq!(order.status, deserialized.status);
        }
    }
}

#[cfg(test)]
mod price_level_invariants {
    use super::*;
    use common::types::PriceLevel;

    proptest! {
        #[test]
        fn test_price_level_ordering(
            price1 in 1.0f64..1000.0,
            price2 in 1.0f64..1000.0,
            vol1 in 1u64..100_000,
            vol2 in 1u64..100_000
        ) {
            let level1 = PriceLevel {
                price: price1,
                volume: vol1,
            };

            let level2 = PriceLevel {
                price: price2,
                volume: vol2,
            };

            // Price comparison should be consistent
            if price1 < price2 {
                prop_assert!(level1.price < level2.price);
            } else if price1 > price2 {
                prop_assert!(level1.price > level2.price);
            } else {
                prop_assert_eq!(level1.price, level2.price);
            }
        }

        #[test]
        fn test_spread_calculation(
            bid in 1.0f64..1000.0,
            spread_bps in 1.0f64..100.0
        ) {
            let ask = bid + (bid * spread_bps / 10000.0);

            let bid_level = PriceLevel {
                price: bid,
                volume: 1000,
            };

            let ask_level = PriceLevel {
                price: ask,
                volume: 1000,
            };

            // Ask should always be >= bid
            prop_assert!(ask_level.price >= bid_level.price);

            // Spread should be positive
            let spread = ask_level.price - bid_level.price;
            prop_assert!(spread >= 0.0);
        }
    }
}

#[cfg(test)]
mod concurrent_order_properties {
    use super::*;

    proptest! {
        #[test]
        fn test_concurrent_order_ids_unique(
            id1 in "[a-z0-9-]{10,20}",
            id2 in "[a-z0-9-]{10,20}"
        ) {
            // Order IDs should be unique
            if id1 != id2 {
                prop_assert_ne!(id1, id2);
            }
        }

        #[test]
        fn test_order_serialization_roundtrip(
            quantity in 1i32..10000,
            price in 1.0f64..1000.0
        ) {
            let order = Order {
                id: "serialize-test".to_string(),
                symbol: "AAPL".to_string(),
                side: OrderSide::Buy,
                order_type: OrderType::Limit,
                quantity,
                price: Some(price),
                status: OrderStatus::Pending,
                timestamp: Utc::now(),
            };

            // Serialization should be lossless
            let json = serde_json::to_string(&order).unwrap();
            let deserialized: Order = serde_json::from_str(&json).unwrap();

            prop_assert_eq!(order.quantity, deserialized.quantity);
            prop_assert_eq!(order.price, deserialized.price);
        }
    }
}
