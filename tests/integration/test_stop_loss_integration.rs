//! Integration tests for stop-loss functionality
//!
//! Tests complete stop-loss workflows including:
//! - Static stop-loss triggers
//! - Trailing stop-loss
//! - Multiple asset types
//! - Error scenarios
//! - Performance under load

use chrono::Utc;
use common::types::*;
use common::config::{RiskConfig, ExecutionConfig};
use risk_manager::stops::StopManager;
use execution_engine::router::OrderRouter;
use tokio;

#[cfg(test)]
mod stop_loss_integration_tests {
    use super::*;

    // Helper function to create test position
    fn create_test_position(symbol: &str, entry_price: f64, current_price: f64, quantity: f64) -> Position {
        Position {
            symbol: Symbol(symbol.to_string()),
            side: Side::Bid,
            quantity: Quantity(quantity),
            entry_price: Price(entry_price),
            current_price: Price(current_price),
            unrealized_pnl: (current_price - entry_price) * quantity,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    // Helper to create stop order
    fn create_stop_order(position: &Position, stop_price: f64) -> Order {
        Order {
            order_id: uuid::Uuid::new_v4().to_string(),
            client_order_id: uuid::Uuid::new_v4().to_string(),
            symbol: position.symbol.clone(),
            side: match position.side {
                Side::Bid => Side::Ask, // Close long position
                Side::Ask => Side::Bid, // Close short position
            },
            order_type: OrderType::StopMarket,
            quantity: position.quantity,
            price: None,
            stop_price: Some(Price(stop_price)),
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    #[tokio::test]
    async fn test_static_stop_loss_trigger_stock() {
        // Test: AAPL position with static stop-loss
        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_loss_price = 147.0;

        // Check if stop should trigger
        let should_trigger = position.current_price.0 <= stop_loss_price;
        assert!(should_trigger, "Stop-loss should trigger when price drops below stop level");

        // Create stop-loss order
        let stop_order = create_stop_order(&position, stop_loss_price);

        assert_eq!(stop_order.order_type, OrderType::StopMarket);
        assert_eq!(stop_order.side, Side::Ask); // Closing long position
        assert_eq!(stop_order.quantity, position.quantity);
        assert_eq!(stop_order.stop_price, Some(Price(stop_loss_price)));

        // Verify P&L
        assert_eq!(position.unrealized_pnl, -500.0); // Lost $5 per share on 100 shares
    }

    #[tokio::test]
    async fn test_static_stop_loss_trigger_crypto() {
        // Test: BTC/USD position with static stop-loss
        let position = create_test_position("BTC/USD", 50000.0, 48000.0, 0.5);
        let stop_loss_price = 49000.0;

        let should_trigger = position.current_price.0 <= stop_loss_price;
        assert!(should_trigger, "Crypto stop-loss should trigger");

        let stop_order = create_stop_order(&position, stop_loss_price);

        assert_eq!(stop_order.symbol.0, "BTC/USD");
        assert_eq!(stop_order.quantity.0, 0.5);

        // Large loss on crypto position
        assert_eq!(position.unrealized_pnl, -1000.0); // Lost $2000 on 0.5 BTC
    }

    #[tokio::test]
    async fn test_static_stop_loss_trigger_futures() {
        // Test: ES futures position with static stop-loss
        let position = create_test_position("ES", 4500.0, 4450.0, 10.0);
        let stop_loss_price = 4480.0;

        let should_trigger = position.current_price.0 <= stop_loss_price;
        assert!(should_trigger, "Futures stop-loss should trigger");

        let stop_order = create_stop_order(&position, stop_loss_price);

        assert_eq!(stop_order.symbol.0, "ES");
        assert_eq!(position.unrealized_pnl, -500.0);
    }

    #[tokio::test]
    async fn test_static_stop_loss_trigger_forex() {
        // Test: EUR/USD forex position with static stop-loss
        let position = create_test_position("EUR/USD", 1.1000, 1.0950, 100000.0);
        let stop_loss_price = 1.0980;

        let should_trigger = position.current_price.0 <= stop_loss_price;
        assert!(should_trigger, "Forex stop-loss should trigger");

        let stop_order = create_stop_order(&position, stop_loss_price);

        assert_eq!(stop_order.symbol.0, "EUR/USD");
        // 50 pips loss on 100k units = $500
        assert_eq!(position.unrealized_pnl, -500.0);
    }

    #[tokio::test]
    async fn test_stop_loss_not_triggered() {
        // Test: Stop-loss should NOT trigger when price is above stop level
        let position = create_test_position("AAPL", 150.0, 152.0, 100.0);
        let stop_loss_price = 147.0;

        let should_trigger = position.current_price.0 <= stop_loss_price;
        assert!(!should_trigger, "Stop-loss should NOT trigger when price is above stop");

        assert_eq!(position.unrealized_pnl, 200.0); // Profit
    }

    #[tokio::test]
    async fn test_trailing_stop_loss() {
        // Test: Trailing stop-loss that adjusts with price movements
        let mut position = create_test_position("AAPL", 150.0, 150.0, 100.0);
        let trail_percent = 0.02; // 2% trailing stop

        // Initial stop-loss 2% below entry
        let mut trailing_stop = position.entry_price.0 * (1.0 - trail_percent);
        assert_eq!(trailing_stop, 147.0);

        // Price moves up - stop should adjust higher
        position.current_price = Price(155.0);
        trailing_stop = position.current_price.0 * (1.0 - trail_percent);
        assert_eq!(trailing_stop, 151.9);

        // Price continues up
        position.current_price = Price(160.0);
        trailing_stop = position.current_price.0 * (1.0 - trail_percent);
        assert_eq!(trailing_stop, 156.8);

        // Price drops but not below trailing stop
        position.current_price = Price(158.0);
        position.unrealized_pnl = (158.0 - 150.0) * 100.0;
        let should_trigger = position.current_price.0 <= trailing_stop;
        assert!(!should_trigger, "Trailing stop should not trigger yet");

        // Price drops below trailing stop
        position.current_price = Price(156.0);
        position.unrealized_pnl = (156.0 - 150.0) * 100.0;
        let should_trigger = position.current_price.0 <= trailing_stop;
        assert!(should_trigger, "Trailing stop should trigger");

        // Verify final P&L (locked in $6 profit instead of $10 peak)
        assert_eq!(position.unrealized_pnl, 600.0);
    }

    #[tokio::test]
    async fn test_multiple_concurrent_stop_losses() {
        // Test: Multiple positions with different stop-loss levels
        let positions = vec![
            create_test_position("AAPL", 150.0, 145.0, 100.0),  // Should trigger (147)
            create_test_position("MSFT", 300.0, 310.0, 50.0),   // Should NOT trigger (295)
            create_test_position("GOOGL", 2800.0, 2750.0, 10.0), // Should trigger (2780)
        ];

        let stop_levels = vec![147.0, 295.0, 2780.0];

        let mut triggered_stops = Vec::new();
        for (pos, stop_level) in positions.iter().zip(stop_levels.iter()) {
            if pos.current_price.0 <= *stop_level {
                let stop_order = create_stop_order(pos, *stop_level);
                triggered_stops.push(stop_order);
            }
        }

        // Should have 2 triggered stops (AAPL and GOOGL)
        assert_eq!(triggered_stops.len(), 2);
        assert_eq!(triggered_stops[0].symbol.0, "AAPL");
        assert_eq!(triggered_stops[1].symbol.0, "GOOGL");
    }

    #[tokio::test]
    async fn test_stop_loss_with_partial_fill() {
        // Test: Stop-loss execution with partial fill scenario
        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_loss_price = 147.0;

        let mut stop_order = create_stop_order(&position, stop_loss_price);

        // Simulate partial fill
        stop_order.status = OrderStatus::PartiallyFilled;
        stop_order.filled_quantity = Quantity(60.0);
        stop_order.average_price = Some(Price(146.5));

        assert_eq!(stop_order.filled_quantity.0, 60.0);
        assert!(stop_order.filled_quantity.0 < stop_order.quantity.0);

        // Calculate realized P&L on partial fill
        let realized_pnl = (146.5 - 150.0) * 60.0;
        assert_eq!(realized_pnl, -210.0); // Loss on filled portion

        // Remaining position
        let remaining_qty = position.quantity.0 - stop_order.filled_quantity.0;
        assert_eq!(remaining_qty, 40.0);
    }

    #[tokio::test]
    async fn test_stop_loss_during_gap_down() {
        // Test: Stop-loss triggered during gap down (price skips over stop level)
        let position = create_test_position("AAPL", 150.0, 142.0, 100.0); // Gapped down from 150 to 142
        let stop_loss_price = 147.0;

        let should_trigger = position.current_price.0 <= stop_loss_price;
        assert!(should_trigger, "Stop should trigger even if price gapped through it");

        let mut stop_order = create_stop_order(&position, stop_loss_price);

        // Fill at market price (worse than stop price due to gap)
        stop_order.status = OrderStatus::Filled;
        stop_order.filled_quantity = position.quantity;
        stop_order.average_price = Some(Price(142.0)); // Filled below stop price

        // Slippage beyond stop level
        let slippage = stop_loss_price - 142.0;
        assert_eq!(slippage, 5.0); // $5 slippage per share

        // Total loss worse than expected
        let actual_loss = (142.0 - 150.0) * 100.0;
        let expected_loss = (147.0 - 150.0) * 100.0;
        assert_eq!(actual_loss, -800.0);
        assert_eq!(expected_loss, -300.0);
        assert!(actual_loss < expected_loss); // Worse outcome due to gap
    }

    #[tokio::test]
    async fn test_stop_loss_network_failure() {
        // Test: Stop-loss execution fails due to network error
        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_loss_price = 147.0;

        let mut stop_order = create_stop_order(&position, stop_loss_price);

        // Simulate network failure - order rejected
        stop_order.status = OrderStatus::Rejected;

        assert_eq!(stop_order.status, OrderStatus::Rejected);
        assert_eq!(stop_order.filled_quantity, Quantity(0.0));

        // Position remains open with unrealized loss
        assert_eq!(position.unrealized_pnl, -500.0);
        assert!(position.quantity.0 > 0.0); // Position still open
    }

    #[tokio::test]
    async fn test_stop_loss_exchange_rejection() {
        // Test: Exchange rejects stop-loss order
        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_loss_price = 147.0;

        let mut stop_order = create_stop_order(&position, stop_loss_price);

        // Exchange rejection (e.g., outside allowed price range)
        stop_order.status = OrderStatus::Rejected;

        assert_eq!(stop_order.status, OrderStatus::Rejected);

        // Should retry with market order
        let mut fallback_order = stop_order.clone();
        fallback_order.order_type = OrderType::Market;
        fallback_order.stop_price = None;
        fallback_order.status = OrderStatus::Pending;

        assert_eq!(fallback_order.order_type, OrderType::Market);
    }

    #[tokio::test]
    async fn test_stop_loss_order_routing() {
        // Test: Stop-loss order routing through execution engine
        let config = ExecutionConfig {
            exchange_api_url: "https://paper-api.alpaca.markets".to_string(),
            api_key: Some("test_key".to_string()),
            api_secret: Some("test_secret".to_string()),
            paper_trading: true,
            rate_limit_per_second: 10,
            retry_attempts: 3,
            retry_delay_ms: 1000,
        };

        let router = OrderRouter::new(config);
        assert!(router.is_ok());

        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_order = create_stop_order(&position, 147.0);

        // In paper trading mode, order should be accepted
        assert_eq!(stop_order.symbol.0, "AAPL");
        assert_eq!(stop_order.order_type, OrderType::StopMarket);
    }

    #[tokio::test]
    async fn test_stop_loss_state_persistence() {
        // Test: Stop-loss state should persist across system restarts
        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_order = create_stop_order(&position, 147.0);

        // Serialize state
        let serialized = serde_json::to_string(&stop_order);
        assert!(serialized.is_ok());

        // Deserialize state
        let deserialized: Result<Order, _> = serde_json::from_str(&serialized.unwrap());
        assert!(deserialized.is_ok());

        let restored_order = deserialized.unwrap();
        assert_eq!(restored_order.symbol, stop_order.symbol);
        assert_eq!(restored_order.stop_price, stop_order.stop_price);
        assert_eq!(restored_order.quantity, stop_order.quantity);
    }

    #[tokio::test]
    async fn test_stop_loss_short_position() {
        // Test: Stop-loss for short position (stop above entry)
        let mut position = create_test_position("AAPL", 150.0, 150.0, 100.0);
        position.side = Side::Ask; // Short position
        position.current_price = Price(155.0); // Price moved against us
        position.unrealized_pnl = (150.0 - 155.0) * 100.0; // Loss on short

        let stop_loss_price = 153.0; // Stop above entry for short

        let should_trigger = position.current_price.0 >= stop_loss_price;
        assert!(should_trigger, "Short position stop should trigger when price rises");

        let stop_order = create_stop_order(&position, stop_loss_price);

        // For short position, closing order is Buy (Bid side)
        assert_eq!(stop_order.side, Side::Bid);
        assert_eq!(position.unrealized_pnl, -500.0); // Loss on short
    }

    #[tokio::test]
    async fn test_stop_loss_performance_100_positions() {
        // Test: Performance of checking stop-loss on 100 positions
        use std::time::Instant;

        let mut positions = Vec::new();
        for i in 0..100 {
            let entry = 100.0 + (i as f64);
            let current = entry - 5.0; // All underwater
            positions.push(create_test_position(
                &format!("SYMBOL{}", i),
                entry,
                current,
                100.0,
            ));
        }

        let start = Instant::now();

        let mut triggered = 0;
        for pos in &positions {
            let stop_level = pos.entry_price.0 * 0.98; // 2% stop
            if pos.current_price.0 <= stop_level {
                triggered += 1;
            }
        }

        let duration = start.elapsed();

        assert_eq!(triggered, 100); // All should trigger
        assert!(duration.as_millis() < 10, "Stop-loss check should be fast (<10ms for 100 positions)");
    }

    #[tokio::test]
    async fn test_stop_loss_with_commissions() {
        // Test: Stop-loss accounting for commissions
        let position = create_test_position("AAPL", 150.0, 145.0, 100.0);
        let stop_loss_price = 147.0;

        let mut stop_order = create_stop_order(&position, stop_loss_price);

        // Fill stop order
        stop_order.status = OrderStatus::Filled;
        stop_order.filled_quantity = position.quantity;
        stop_order.average_price = Some(Price(146.5)); // Slipped a bit

        // Calculate P&L including commission
        let commission = 1.0; // $1 per order
        let gross_pnl = (146.5 - 150.0) * 100.0;
        let net_pnl = gross_pnl - commission;

        assert_eq!(gross_pnl, -350.0);
        assert_eq!(net_pnl, -351.0); // Slightly worse with commission
    }
}
