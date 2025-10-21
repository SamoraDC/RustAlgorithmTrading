//! Unit tests for risk manager components
//!
//! Tests cover:
//! - Position limit checks
//! - Notional exposure limits
//! - Daily loss limits
//! - Risk rule violations
//! - Position tracking

use common::config::RiskConfig;
use common::types::{Order, OrderStatus, OrderType, Position, Price, Quantity, Side, Symbol};
use risk_manager::limits::LimitChecker;
use chrono::Utc;

#[cfg(test)]
mod limit_checker_tests {
    use super::*;

    fn create_test_config() -> RiskConfig {
        RiskConfig {
            max_position_size: 10000.0,
            max_notional_exposure: 50000.0,
            max_open_positions: 5,
            max_loss_threshold: 1000.0,
            stop_loss_percentage: 0.02,
            circuit_breaker_threshold: 0.05,
        }
    }

    fn create_test_order(symbol: &str, quantity: f64, price: f64) -> Order {
        Order {
            order_id: "test_order".to_string(),
            client_order_id: "client_order".to_string(),
            symbol: Symbol(symbol.to_string()),
            side: Side::Bid,
            order_type: OrderType::Limit,
            quantity: Quantity(quantity),
            price: Some(Price(price)),
            stop_price: None,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    fn create_test_position(symbol: &str, quantity: f64, price: f64) -> Position {
        Position {
            symbol: Symbol(symbol.to_string()),
            side: Side::Bid,
            quantity: Quantity(quantity),
            entry_price: Price(price),
            current_price: Price(price),
            unrealized_pnl: 0.0,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    #[test]
    fn test_limit_checker_creation() {
        let config = create_test_config();
        let checker = LimitChecker::new(config.clone());

        assert_eq!(checker.get_daily_pnl(), 0.0);
        assert_eq!(checker.get_positions().len(), 0);
    }

    #[test]
    fn test_order_size_within_limit() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        // Order size: 50 * 100 = 5000, well within 10000 limit
        let order = create_test_order("AAPL", 50.0, 100.0);
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_order_size_exceeds_limit() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        // Order size: 150 * 100 = 15000, exceeds 10000 limit
        let order = create_test_order("AAPL", 150.0, 100.0);
        let result = checker.check(&order);

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("exceeds max position size"));
    }

    #[test]
    fn test_position_size_check_new_position() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        let order = create_test_order("AAPL", 50.0, 100.0);
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_position_size_check_existing_position() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Create existing position: 50 * 100 = 5000
        let position = create_test_position("AAPL", 50.0, 100.0);
        checker.update_position(position);

        // New order: 60 * 100 = 6000
        // Total: 5000 + 6000 = 11000, exceeds 10000 limit
        let order = create_test_order("AAPL", 60.0, 100.0);
        let result = checker.check(&order);

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("would exceed max"));
    }

    #[test]
    fn test_notional_exposure_check() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add positions totaling 40000
        let pos1 = create_test_position("AAPL", 100.0, 200.0); // 20000
        let pos2 = create_test_position("MSFT", 100.0, 200.0); // 20000
        checker.update_position(pos1);
        checker.update_position(pos2);

        // New order: 60 * 200 = 12000
        // Total: 40000 + 12000 = 52000, exceeds 50000 limit
        let order = create_test_order("GOOGL", 60.0, 200.0);
        let result = checker.check(&order);

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Total exposure"));
    }

    #[test]
    fn test_open_positions_limit() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add 5 positions (max limit)
        for i in 0..5 {
            let symbol = format!("SYM{}", i);
            let position = create_test_position(&symbol, 10.0, 100.0);
            checker.update_position(position);
        }

        // Try to add 6th position
        let order = create_test_order("SYM5", 10.0, 100.0);
        let result = checker.check(&order);

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Open positions"));
    }

    #[test]
    fn test_daily_loss_limit() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Create position with loss exceeding threshold
        let mut position = create_test_position("AAPL", 100.0, 100.0);
        position.realized_pnl = -1500.0; // Exceeds -1000 threshold
        checker.update_position(position);

        let order = create_test_order("MSFT", 10.0, 100.0);
        let result = checker.check(&order);

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Daily loss"));
    }

    #[test]
    fn test_market_order_passes_checks() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        let mut order = create_test_order("AAPL", 50.0, 100.0);
        order.order_type = OrderType::Market;
        order.price = None;

        // Market orders with no price should pass (checked at execution)
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_update_position_tracking() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add position
        let position = create_test_position("AAPL", 100.0, 150.0);
        checker.update_position(position);

        assert_eq!(checker.get_positions().len(), 1);
        assert!(checker.get_positions().contains_key("AAPL"));

        // Close position
        let mut closed_position = create_test_position("AAPL", 0.0, 150.0);
        closed_position.realized_pnl = 500.0;
        checker.update_position(closed_position);

        assert_eq!(checker.get_positions().len(), 0);
        assert_eq!(checker.get_daily_pnl(), 500.0);
    }

    #[test]
    fn test_reset_daily_pnl() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add some P&L
        let mut position = create_test_position("AAPL", 0.0, 150.0);
        position.realized_pnl = 500.0;
        checker.update_position(position);

        assert_eq!(checker.get_daily_pnl(), 500.0);

        // Reset
        checker.reset_daily_pnl();
        assert_eq!(checker.get_daily_pnl(), 0.0);
    }

    #[test]
    fn test_multiple_positions_tracking() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add 3 positions
        let symbols = vec!["AAPL", "MSFT", "GOOGL"];
        for symbol in &symbols {
            let position = create_test_position(symbol, 50.0, 100.0);
            checker.update_position(position);
        }

        assert_eq!(checker.get_positions().len(), 3);

        for symbol in symbols {
            assert!(checker.get_positions().contains_key(symbol));
        }
    }

    #[test]
    fn test_position_update_replaces_existing() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Initial position
        let position1 = create_test_position("AAPL", 50.0, 100.0);
        checker.update_position(position1);

        // Updated position
        let position2 = create_test_position("AAPL", 75.0, 105.0);
        checker.update_position(position2);

        assert_eq!(checker.get_positions().len(), 1);
        let aapl_pos = checker.get_positions().get("AAPL").unwrap();
        assert_eq!(aapl_pos.quantity.0, 75.0);
        assert_eq!(aapl_pos.current_price.0, 105.0);
    }

    #[test]
    fn test_all_checks_pass_for_valid_order() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add a small position
        let position = create_test_position("AAPL", 20.0, 100.0);
        checker.update_position(position);

        // Valid order that should pass all checks
        let order = create_test_order("MSFT", 30.0, 100.0);
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_zero_quantity_order() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        let order = create_test_order("AAPL", 0.0, 100.0);
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_edge_case_exact_limit() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        // Order exactly at limit: 100 * 100 = 10000
        let order = create_test_order("AAPL", 100.0, 100.0);
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_edge_case_just_over_limit() {
        let config = create_test_config();
        let checker = LimitChecker::new(config);

        // Order just over limit: 100.01 * 100 = 10001
        let order = create_test_order("AAPL", 100.01, 100.0);
        let result = checker.check(&order);

        assert!(result.is_err());
    }

    #[test]
    fn test_sell_order_with_existing_long() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Add long position
        let position = create_test_position("AAPL", 100.0, 100.0);
        checker.update_position(position);

        // Sell order should pass
        let mut order = create_test_order("AAPL", 50.0, 100.0);
        order.side = Side::Ask;
        assert!(checker.check(&order).is_ok());
    }

    #[test]
    fn test_accumulated_pnl_tracking() {
        let config = create_test_config();
        let mut checker = LimitChecker::new(config);

        // Multiple trades with P&L
        let mut pos1 = create_test_position("AAPL", 0.0, 100.0);
        pos1.realized_pnl = 100.0;
        checker.update_position(pos1);

        let mut pos2 = create_test_position("MSFT", 0.0, 200.0);
        pos2.realized_pnl = 150.0;
        checker.update_position(pos2);

        let mut pos3 = create_test_position("GOOGL", 0.0, 300.0);
        pos3.realized_pnl = -50.0;
        checker.update_position(pos3);

        assert_eq!(checker.get_daily_pnl(), 200.0);
    }
}

#[cfg(test)]
mod risk_calculations_tests {
    use super::*;

    #[test]
    fn test_var_calculation_simple() {
        // Value at Risk calculation test
        let position = create_test_position("AAPL", 100.0, 150.0);
        let position_value = position.quantity.0 * position.current_price.0;

        // 95% VaR with 2% daily volatility
        let confidence_level = 1.645; // 95% confidence
        let volatility = 0.02;
        let var = position_value * volatility * confidence_level;

        assert!((var - 493.5).abs() < 0.1);
    }

    #[test]
    fn test_position_delta_calculation() {
        let entry_price = 100.0;
        let current_price = 105.0;
        let quantity = 100.0;

        let pnl = (current_price - entry_price) * quantity;
        assert_eq!(pnl, 500.0);

        let pnl_percentage = ((current_price - entry_price) / entry_price) * 100.0;
        assert_eq!(pnl_percentage, 5.0);
    }

    #[test]
    fn test_max_drawdown_calculation() {
        let peak_value = 100000.0;
        let current_value = 95000.0;

        let drawdown = (peak_value - current_value) / peak_value;
        assert_eq!(drawdown, 0.05);
    }

    #[test]
    fn test_sharpe_ratio_estimation() {
        let returns = vec![0.01, 0.02, -0.01, 0.03, 0.01];
        let avg_return = returns.iter().sum::<f64>() / returns.len() as f64;

        let variance = returns.iter()
            .map(|r| (r - avg_return).powi(2))
            .sum::<f64>() / returns.len() as f64;

        let std_dev = variance.sqrt();
        let risk_free_rate = 0.02;
        let sharpe = (avg_return - risk_free_rate) / std_dev;

        assert!(sharpe.is_finite());
    }
}
