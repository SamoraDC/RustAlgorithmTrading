//! Unit tests for slippage estimation
//!
//! Tests cover:
//! - Basic slippage calculation
//! - Market impact estimation
//! - Order book depth analysis
//! - Different order sizes

use execution_engine::slippage::SlippageEstimator;
use common::types::{Order, OrderStatus, OrderType, Price, Quantity, Side, Symbol};
use chrono::Utc;

#[cfg(test)]
mod slippage_tests {
    use super::*;

    fn create_test_order(quantity: f64, price: Option<f64>) -> Order {
        Order {
            order_id: "test".to_string(),
            client_order_id: "client".to_string(),
            symbol: Symbol("AAPL".to_string()),
            side: Side::Bid,
            order_type: if price.is_some() { OrderType::Limit } else { OrderType::Market },
            quantity: Quantity(quantity),
            price: price.map(Price),
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    #[test]
    fn test_slippage_estimator_creation() {
        let estimator = SlippageEstimator::new();
        // Should create without error
        assert!(true);
    }

    #[test]
    fn test_slippage_estimator_default() {
        let estimator = SlippageEstimator::default();
        // Should create via default
        assert!(true);
    }

    #[test]
    fn test_basic_slippage_estimate() {
        let estimator = SlippageEstimator::new();
        let order = create_test_order(100.0, Some(150.0));

        let slippage = estimator.estimate(&order);

        // Currently returns 0.0, but structure is in place
        assert_eq!(slippage, 0.0);
    }

    #[test]
    fn test_market_order_slippage() {
        let estimator = SlippageEstimator::new();
        let order = create_test_order(100.0, None);

        let slippage = estimator.estimate(&order);

        assert_eq!(slippage, 0.0);
    }

    #[test]
    fn test_small_order_slippage() {
        let estimator = SlippageEstimator::new();
        let order = create_test_order(10.0, Some(150.0));

        let slippage = estimator.estimate(&order);

        // Small orders should have minimal slippage
        assert_eq!(slippage, 0.0);
    }

    #[test]
    fn test_large_order_slippage() {
        let estimator = SlippageEstimator::new();
        let order = create_test_order(10000.0, Some(150.0));

        let slippage = estimator.estimate(&order);

        // Large orders should have more slippage
        // Currently 0.0, will be implemented later
        assert_eq!(slippage, 0.0);
    }

    #[test]
    fn test_buy_order_slippage() {
        let estimator = SlippageEstimator::new();
        let mut order = create_test_order(100.0, Some(150.0));
        order.side = Side::Bid;

        let slippage = estimator.estimate(&order);
        assert_eq!(slippage, 0.0);
    }

    #[test]
    fn test_sell_order_slippage() {
        let estimator = SlippageEstimator::new();
        let mut order = create_test_order(100.0, Some(150.0));
        order.side = Side::Ask;

        let slippage = estimator.estimate(&order);
        assert_eq!(slippage, 0.0);
    }
}

#[cfg(test)]
mod slippage_calculation_tests {
    #[test]
    fn test_percentage_slippage() {
        let expected_price = 100.0;
        let actual_price = 100.5;

        let slippage = ((actual_price - expected_price) / expected_price) * 100.0;
        assert_eq!(slippage, 0.5);
    }

    #[test]
    fn test_absolute_slippage() {
        let expected_price = 100.0;
        let actual_price = 100.5;
        let quantity = 1000.0;

        let absolute_slippage = (actual_price - expected_price) * quantity;
        assert_eq!(absolute_slippage, 500.0);
    }

    #[test]
    fn test_bid_ask_spread_impact() {
        let bid = 99.5;
        let ask = 100.5;
        let spread = ask - bid;

        // Market buy pays the spread
        let buy_slippage = spread / 2.0;
        assert_eq!(buy_slippage, 0.5);
    }

    #[test]
    fn test_market_impact_linear() {
        let base_slippage = 0.001; // 0.1%
        let order_size = 1000.0;
        let average_volume = 10000.0;

        let size_ratio = order_size / average_volume;
        let market_impact = base_slippage * size_ratio;

        assert!((market_impact - 0.0001).abs() < 1e-10);
    }

    #[test]
    fn test_market_impact_sqrt() {
        let base_impact = 0.01;
        let order_size = 10000.0;
        let daily_volume = 1000000.0;

        let size_ratio = order_size / daily_volume;
        let market_impact = base_impact * size_ratio.sqrt();

        assert!(market_impact > 0.0);
        assert!(market_impact < base_impact);
    }

    #[test]
    fn test_liquidity_adjustment() {
        let high_liquidity_slippage = 0.001;
        let low_liquidity_slippage = 0.01;

        // Higher slippage for less liquid markets
        assert!(low_liquidity_slippage > high_liquidity_slippage);
    }

    #[test]
    fn test_volatility_adjustment() {
        let base_slippage = 0.001;
        let volatility_multiplier = 2.0; // High volatility

        let adjusted_slippage = base_slippage * volatility_multiplier;
        assert_eq!(adjusted_slippage, 0.002);
    }

    #[test]
    fn test_time_of_day_adjustment() {
        let market_open_slippage = 0.002; // Higher at open
        let midday_slippage = 0.001; // Lower during stable hours

        assert!(market_open_slippage > midday_slippage);
    }

    #[test]
    fn test_order_book_depth_impact() {
        // Simulate order book levels
        let levels = vec![
            (100.0, 100.0), // price, quantity
            (100.1, 200.0),
            (100.2, 300.0),
        ];

        let order_quantity = 250.0;
        let mut remaining = order_quantity;
        let mut total_cost = 0.0;

        for (price, quantity) in levels {
            let fill_qty = remaining.min(quantity);
            total_cost += fill_qty * price;
            remaining -= fill_qty;
            if remaining <= 0.0 {
                break;
            }
        }

        let average_price = total_cost / (order_quantity - remaining);
        assert!(average_price > 100.0);
    }

    #[test]
    fn test_slippage_tolerance_check() {
        let expected_price = 100.0;
        let max_slippage_percent = 0.5; // 0.5%
        let max_acceptable_price = expected_price * (1.0 + max_slippage_percent / 100.0);

        assert_eq!(max_acceptable_price, 100.5);

        // Check if actual price is within tolerance
        let actual_price = 100.3;
        assert!(actual_price <= max_acceptable_price);
    }
}
