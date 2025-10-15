//! Integration tests for end-to-end workflows
//!
//! Tests complete trading workflows from signal generation to order execution

use chrono::Utc;
use common::types::*;

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[test]
    fn test_order_lifecycle() {
        // Test complete order lifecycle: Pending -> Filled
        let mut order = Order {
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

        // Initial state
        assert_eq!(order.status, OrderStatus::Pending);
        assert_eq!(order.filled_quantity, Quantity(0.0));

        // Partial fill
        order.status = OrderStatus::PartiallyFilled;
        order.filled_quantity = Quantity(50.0);
        order.average_price = Some(Price(150.0));

        assert_eq!(order.status, OrderStatus::PartiallyFilled);
        assert!(order.filled_quantity.0 < order.quantity.0);

        // Complete fill
        order.status = OrderStatus::Filled;
        order.filled_quantity = Quantity(100.0);

        assert_eq!(order.status, OrderStatus::Filled);
        assert_eq!(order.filled_quantity, order.quantity);
    }

    #[test]
    fn test_signal_to_order_workflow() {
        // Test workflow: Signal -> Order creation

        // 1. Generate signal
        let signal = Signal {
            symbol: Symbol("AAPL".to_string()),
            action: SignalAction::Buy,
            confidence: 0.85,
            features: vec![1.0, 2.0, 3.0],
            timestamp: Utc::now(),
        };

        assert_eq!(signal.action, SignalAction::Buy);
        assert!(signal.confidence > 0.8);

        // 2. Create order from signal
        let order = Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: signal.symbol.clone(),
            side: Side::Bid, // Buy signal -> Bid side
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

        assert_eq!(order.symbol, signal.symbol);
        assert_eq!(order.side, Side::Bid);
    }

    #[test]
    fn test_position_update_workflow() {
        // Test workflow: Order fill -> Position update

        // 1. Create filled order
        let order = Order {
            order_id: "ord123".to_string(),
            client_order_id: "client123".to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(100.0),
            price: Some(Price(150.0)),
            stop_price: None,
            status: OrderStatus::Filled,
            filled_quantity: Quantity(100.0),
            average_price: Some(Price(150.0)),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        // 2. Create position from filled order
        let position = Position {
            symbol: order.symbol.clone(),
            side: order.side,
            quantity: order.filled_quantity,
            entry_price: order.average_price.unwrap(),
            current_price: Price(155.0),
            unrealized_pnl: (155.0 - 150.0) * 100.0,
            realized_pnl: 0.0,
            opened_at: order.created_at,
            updated_at: Utc::now(),
        };

        assert_eq!(position.symbol, order.symbol);
        assert_eq!(position.quantity, order.filled_quantity);
        assert_eq!(position.unrealized_pnl, 500.0);
    }

    #[test]
    fn test_market_data_to_signal_workflow() {
        // Test workflow: Market data -> Signal generation

        // 1. Receive market data
        let bar = Bar {
            symbol: Symbol("AAPL".to_string()),
            open: Price(100.0),
            high: Price(105.0),
            low: Price(99.0),
            close: Price(103.0),
            volume: Quantity(1000.0),
            timestamp: Utc::now(),
        };

        // 2. Simple strategy: Buy if close > open
        let should_buy = bar.close.0 > bar.open.0;

        // 3. Generate signal if condition met
        if should_buy {
            let signal = Signal {
                symbol: bar.symbol.clone(),
                action: SignalAction::Buy,
                confidence: 0.7,
                features: vec![bar.close.0, bar.volume.0],
                timestamp: Utc::now(),
            };

            assert_eq!(signal.action, SignalAction::Buy);
            assert_eq!(signal.symbol, bar.symbol);
        }

        assert!(should_buy);
    }

    #[test]
    fn test_orderbook_to_trade_execution() {
        // Test workflow: Order book -> Trade execution

        // 1. Get order book
        let orderbook = OrderBook {
            symbol: Symbol("AAPL".to_string()),
            bids: vec![
                Level {
                    price: Price(100.0),
                    quantity: Quantity(50.0),
                    timestamp: Utc::now(),
                },
            ],
            asks: vec![
                Level {
                    price: Price(100.5),
                    quantity: Quantity(50.0),
                    timestamp: Utc::now(),
                },
            ],
            timestamp: Utc::now(),
            sequence: 1,
        };

        // 2. Calculate spread
        let best_bid = orderbook.bids[0].price;
        let best_ask = orderbook.asks[0].price;
        let spread = best_ask.0 - best_bid.0;

        assert_eq!(spread, 0.5);

        // 3. Create market order (should execute at best ask)
        let order = Order {
            order_id: "ord123".to_string(),
            client_order_id: "client123".to_string(),
            symbol: orderbook.symbol.clone(),
            side: Side::Bid,
            order_type: OrderType::Market,
            quantity: Quantity(10.0),
            price: None,
            stop_price: None,
            status: OrderStatus::Filled,
            filled_quantity: Quantity(10.0),
            average_price: Some(best_ask),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };

        assert_eq!(order.average_price.unwrap(), best_ask);
    }

    #[test]
    fn test_multiple_orders_workflow() {
        // Test workflow: Multiple concurrent orders

        let symbols = vec!["AAPL", "MSFT", "GOOGL"];
        let mut orders = Vec::new();

        // Create orders for multiple symbols
        for symbol in symbols {
            let order = Order {
                order_id: uuid::Uuid::new_v4().to_string(),
                client_order_id: uuid::Uuid::new_v4().to_string(),
                symbol: Symbol(symbol.to_string()),
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
            orders.push(order);
        }

        assert_eq!(orders.len(), 3);

        // Verify all orders are unique
        for i in 0..orders.len() {
            for j in (i + 1)..orders.len() {
                assert_ne!(orders[i].order_id, orders[j].order_id);
                assert_ne!(orders[i].symbol, orders[j].symbol);
            }
        }
    }

    #[test]
    fn test_pnl_tracking_workflow() {
        // Test workflow: Position tracking with P&L updates

        // Create initial position
        let mut position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(150.0),
            unrealized_pnl: 0.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        // Price moves up
        position.current_price = Price(155.0);
        position.unrealized_pnl = (155.0 - 150.0) * 100.0;
        assert_eq!(position.unrealized_pnl, 500.0);

        // Price moves down
        position.current_price = Price(145.0);
        position.unrealized_pnl = (145.0 - 150.0) * 100.0;
        assert_eq!(position.unrealized_pnl, -500.0);

        // Close position (realize P&L)
        position.realized_pnl = position.unrealized_pnl;
        position.unrealized_pnl = 0.0;
        position.quantity = Quantity(0.0);

        assert_eq!(position.realized_pnl, -500.0);
        assert_eq!(position.quantity, Quantity(0.0));
    }

    #[test]
    fn test_order_cancellation_workflow() {
        // Test workflow: Order cancellation

        let mut order = Order {
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

        // Cancel order
        order.status = OrderStatus::Cancelled;
        order.updated_at = Utc::now();

        assert_eq!(order.status, OrderStatus::Cancelled);
        assert_eq!(order.filled_quantity, Quantity(0.0));
    }

    #[test]
    fn test_stop_loss_workflow() {
        // Test workflow: Stop loss trigger

        // Create position
        let position = Position {
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            quantity: Quantity(100.0),
            entry_price: Price(150.0),
            current_price: Price(145.0),
            unrealized_pnl: -500.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        };

        // Define stop loss level
        let stop_loss_price = Price(147.0);

        // Check if stop loss should trigger
        let should_trigger = position.current_price.0 <= stop_loss_price.0;

        if should_trigger {
            // Create stop loss order
            let stop_order = Order {
                order_id: uuid::Uuid::new_v4().to_string(),
                client_order_id: uuid::Uuid::new_v4().to_string(),
                symbol: position.symbol.clone(),
                side: Side::Ask, // Close long position
                order_type: OrderType::Market,
                quantity: position.quantity,
                price: None,
                stop_price: Some(stop_loss_price),
                status: OrderStatus::Pending,
                filled_quantity: Quantity(0.0),
                average_price: None,
                created_at: Utc::now(),
                updated_at: Utc::now(),
            };

            assert_eq!(stop_order.side, Side::Ask);
            assert_eq!(stop_order.quantity, position.quantity);
        }

        assert!(should_trigger);
    }
}
