//! Test fixtures and mock data generators
//!
//! Provides utilities for creating test data:
//! - Mock orders
//! - Mock trades
//! - Mock order books
//! - Mock positions
//! - Mock signals

use chrono::Utc;
use common::types::*;

/// Create a mock symbol
pub fn mock_symbol(name: &str) -> Symbol {
    Symbol(name.to_string())
}

/// Create a mock price
pub fn mock_price(value: f64) -> Price {
    Price(value)
}

/// Create a mock quantity
pub fn mock_quantity(value: f64) -> Quantity {
    Quantity(value)
}

/// Create a mock order book level
pub fn mock_level(price: f64, quantity: f64) -> Level {
    Level {
        price: Price(price),
        quantity: Quantity(quantity),
        timestamp: Utc::now(),
    }
}

/// Create a mock trade
pub fn mock_trade(symbol: &str, price: f64, quantity: f64, side: Side) -> Trade {
    Trade {
        symbol: Symbol(symbol.to_string()),
        price: Price(price),
        quantity: Quantity(quantity),
        side,
        timestamp: Utc::now(),
        trade_id: uuid::Uuid::new_v4().to_string(),
    }
}

/// Create a mock OHLCV bar
pub fn mock_bar(symbol: &str, open: f64, high: f64, low: f64, close: f64, volume: f64) -> Bar {
    Bar {
        symbol: Symbol(symbol.to_string()),
        open: Price(open),
        high: Price(high),
        low: Price(low),
        close: Price(close),
        volume: Quantity(volume),
        timestamp: Utc::now(),
    }
}

/// Create a mock order book
pub fn mock_orderbook(symbol: &str, sequence: u64) -> OrderBook {
    OrderBook {
        symbol: Symbol(symbol.to_string()),
        bids: vec![
            mock_level(100.0, 10.0),
            mock_level(99.5, 20.0),
            mock_level(99.0, 30.0),
        ],
        asks: vec![
            mock_level(100.5, 15.0),
            mock_level(101.0, 25.0),
            mock_level(101.5, 35.0),
        ],
        timestamp: Utc::now(),
        sequence,
    }
}

/// Create a mock market order
pub fn mock_market_order(symbol: &str, side: Side, quantity: f64) -> Order {
    let now = Utc::now();
    Order {
        order_id: uuid::Uuid::new_v4().to_string(),
        client_order_id: uuid::Uuid::new_v4().to_string(),
        symbol: Symbol(symbol.to_string()),
        side,
        order_type: OrderType::Market,
        quantity: Quantity(quantity),
        price: None,
        stop_price: None,
        status: OrderStatus::Pending,
        filled_quantity: Quantity(0.0),
        average_price: None,
        created_at: now,
        updated_at: now,
    }
}

/// Create a mock limit order
pub fn mock_limit_order(symbol: &str, side: Side, quantity: f64, price: f64) -> Order {
    let now = Utc::now();
    Order {
        order_id: uuid::Uuid::new_v4().to_string(),
        client_order_id: uuid::Uuid::new_v4().to_string(),
        symbol: Symbol(symbol.to_string()),
        side,
        order_type: OrderType::Limit,
        quantity: Quantity(quantity),
        price: Some(Price(price)),
        stop_price: None,
        status: OrderStatus::Pending,
        filled_quantity: Quantity(0.0),
        average_price: None,
        created_at: now,
        updated_at: now,
    }
}

/// Create a mock stop order
pub fn mock_stop_order(symbol: &str, side: Side, quantity: f64, stop_price: f64) -> Order {
    let now = Utc::now();
    Order {
        order_id: uuid::Uuid::new_v4().to_string(),
        client_order_id: uuid::Uuid::new_v4().to_string(),
        symbol: Symbol(symbol.to_string()),
        side,
        order_type: OrderType::StopMarket,
        quantity: Quantity(quantity),
        price: None,
        stop_price: Some(Price(stop_price)),
        status: OrderStatus::Pending,
        filled_quantity: Quantity(0.0),
        average_price: None,
        created_at: now,
        updated_at: now,
    }
}

/// Create a mock filled order
pub fn mock_filled_order(symbol: &str, side: Side, quantity: f64, price: f64) -> Order {
    let now = Utc::now();
    Order {
        order_id: uuid::Uuid::new_v4().to_string(),
        client_order_id: uuid::Uuid::new_v4().to_string(),
        symbol: Symbol(symbol.to_string()),
        side,
        order_type: OrderType::Limit,
        quantity: Quantity(quantity),
        price: Some(Price(price)),
        stop_price: None,
        status: OrderStatus::Filled,
        filled_quantity: Quantity(quantity),
        average_price: Some(Price(price)),
        created_at: now,
        updated_at: now,
    }
}

/// Create a mock partially filled order
pub fn mock_partially_filled_order(
    symbol: &str,
    side: Side,
    total_quantity: f64,
    filled_quantity: f64,
    price: f64,
) -> Order {
    let now = Utc::now();
    Order {
        order_id: uuid::Uuid::new_v4().to_string(),
        client_order_id: uuid::Uuid::new_v4().to_string(),
        symbol: Symbol(symbol.to_string()),
        side,
        order_type: OrderType::Limit,
        quantity: Quantity(total_quantity),
        price: Some(Price(price)),
        stop_price: None,
        status: OrderStatus::PartiallyFilled,
        filled_quantity: Quantity(filled_quantity),
        average_price: Some(Price(price)),
        created_at: now,
        updated_at: now,
    }
}

/// Create a mock position
pub fn mock_position(
    symbol: &str,
    side: Side,
    quantity: f64,
    entry_price: f64,
    current_price: f64,
) -> Position {
    let unrealized_pnl = match side {
        Side::Bid => (current_price - entry_price) * quantity,
        Side::Ask => (entry_price - current_price) * quantity,
    };

    let now = Utc::now();
    Position {
        symbol: Symbol(symbol.to_string()),
        side,
        quantity: Quantity(quantity),
        entry_price: Price(entry_price),
        current_price: Price(current_price),
        unrealized_pnl,
        realized_pnl: 0.0,
        opened_at: now,
        updated_at: now,
    }
}

/// Create a mock trading signal
pub fn mock_signal(symbol: &str, action: SignalAction, confidence: f64) -> Signal {
    Signal {
        symbol: Symbol(symbol.to_string()),
        action,
        confidence,
        features: vec![1.0, 2.0, 3.0, 4.0, 5.0],
        timestamp: Utc::now(),
    }
}

/// Create a sequence of mock bars (time series)
pub fn mock_bar_sequence(symbol: &str, count: usize, start_price: f64) -> Vec<Bar> {
    let mut bars = Vec::new();
    let mut price = start_price;

    for i in 0..count {
        let volatility = 0.02; // 2% volatility
        let change = (i as f64 * 0.123).sin() * price * volatility;

        let open = price;
        let close = price + change;
        let high = open.max(close) * 1.005;
        let low = open.min(close) * 0.995;

        bars.push(mock_bar(symbol, open, high, low, close, 1000.0 + i as f64 * 10.0));

        price = close;
    }

    bars
}

/// Create a sequence of mock trades
pub fn mock_trade_sequence(symbol: &str, count: usize, start_price: f64) -> Vec<Trade> {
    let mut trades = Vec::new();
    let mut price = start_price;

    for i in 0..count {
        let side = if i % 2 == 0 { Side::Bid } else { Side::Ask };
        let price_change = ((i as f64 * 0.5).sin() * 0.1).max(-0.05);
        price = price * (1.0 + price_change);

        trades.push(mock_trade(symbol, price, 10.0 + i as f64, side));
    }

    trades
}

#[cfg(test)]
mod fixture_tests {
    use super::*;

    #[test]
    fn test_mock_symbol() {
        let symbol = mock_symbol("AAPL");
        assert_eq!(symbol.0, "AAPL");
    }

    #[test]
    fn test_mock_price() {
        let price = mock_price(100.50);
        assert_eq!(price.0, 100.50);
    }

    #[test]
    fn test_mock_trade() {
        let trade = mock_trade("AAPL", 150.0, 100.0, Side::Bid);
        assert_eq!(trade.symbol, Symbol("AAPL".to_string()));
        assert_eq!(trade.price, Price(150.0));
        assert_eq!(trade.quantity, Quantity(100.0));
        assert_eq!(trade.side, Side::Bid);
    }

    #[test]
    fn test_mock_bar() {
        let bar = mock_bar("AAPL", 100.0, 105.0, 99.0, 103.0, 1000.0);
        assert_eq!(bar.open, Price(100.0));
        assert_eq!(bar.high, Price(105.0));
        assert_eq!(bar.low, Price(99.0));
        assert_eq!(bar.close, Price(103.0));
        assert_eq!(bar.volume, Quantity(1000.0));
    }

    #[test]
    fn test_mock_orderbook() {
        let book = mock_orderbook("AAPL", 1);
        assert_eq!(book.symbol, Symbol("AAPL".to_string()));
        assert_eq!(book.sequence, 1);
        assert_eq!(book.bids.len(), 3);
        assert_eq!(book.asks.len(), 3);
    }

    #[test]
    fn test_mock_market_order() {
        let order = mock_market_order("AAPL", Side::Bid, 100.0);
        assert_eq!(order.order_type, OrderType::Market);
        assert_eq!(order.quantity, Quantity(100.0));
        assert!(order.price.is_none());
    }

    #[test]
    fn test_mock_limit_order() {
        let order = mock_limit_order("AAPL", Side::Bid, 100.0, 150.0);
        assert_eq!(order.order_type, OrderType::Limit);
        assert_eq!(order.quantity, Quantity(100.0));
        assert_eq!(order.price, Some(Price(150.0)));
    }

    #[test]
    fn test_mock_position() {
        let position = mock_position("AAPL", Side::Bid, 100.0, 150.0, 155.0);
        assert_eq!(position.quantity, Quantity(100.0));
        assert_eq!(position.unrealized_pnl, 500.0); // (155-150) * 100
    }

    #[test]
    fn test_mock_signal() {
        let signal = mock_signal("AAPL", SignalAction::Buy, 0.85);
        assert_eq!(signal.action, SignalAction::Buy);
        assert_eq!(signal.confidence, 0.85);
        assert_eq!(signal.features.len(), 5);
    }

    #[test]
    fn test_mock_bar_sequence() {
        let bars = mock_bar_sequence("AAPL", 10, 100.0);
        assert_eq!(bars.len(), 10);
        // Verify OHLC relationships
        for bar in bars {
            assert!(bar.high >= bar.open);
            assert!(bar.high >= bar.close);
            assert!(bar.low <= bar.open);
            assert!(bar.low <= bar.close);
        }
    }

    #[test]
    fn test_mock_trade_sequence() {
        let trades = mock_trade_sequence("AAPL", 20, 100.0);
        assert_eq!(trades.len(), 20);
        // Verify alternating sides
        for (i, trade) in trades.iter().enumerate() {
            let expected_side = if i % 2 == 0 { Side::Bid } else { Side::Ask };
            assert_eq!(trade.side, expected_side);
        }
    }
}
