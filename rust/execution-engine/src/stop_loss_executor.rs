use common::{
    types::{Order, OrderStatus, OrderType, Price, Quantity, Side, Symbol},
    Result, TradingError,
};
use chrono::Utc;
use tracing::{info, warn};

/// Handles execution of stop-loss triggered orders
pub struct StopLossExecutor {
    /// Whether to use market or limit orders for stop execution
    use_market_orders: bool,
    /// Slippage tolerance for limit orders (percentage)
    slippage_tolerance: f64,
}

impl StopLossExecutor {
    pub fn new(use_market_orders: bool, slippage_tolerance: f64) -> Self {
        info!(
            "Initializing StopLossExecutor: market_orders={}, slippage={}%",
            use_market_orders, slippage_tolerance
        );
        Self {
            use_market_orders,
            slippage_tolerance,
        }
    }

    /// Create a closing order from a stop-loss trigger
    pub fn create_stop_loss_order(
        &self,
        symbol: Symbol,
        close_side: Side,
        quantity: Quantity,
        current_price: Price,
        trigger_price: Price,
    ) -> Result<Order> {
        let (order_type, price, stop_price) = if self.use_market_orders {
            // Market order for immediate execution
            (OrderType::Market, None, None)
        } else {
            // Limit order with slippage tolerance
            let limit_price = self.calculate_limit_price(close_side, current_price);
            (OrderType::Limit, Some(limit_price), Some(trigger_price))
        };

        let order_id = format!("stop-{}-{}", symbol.0, Utc::now().timestamp_millis());
        let client_order_id = format!("stop-loss-{}", Utc::now().timestamp_nanos_opt().unwrap_or(0));

        info!(
            "Creating stop-loss order: {} {} {} @ {:?} (trigger: {:.8})",
            order_id, close_side as u8, quantity.0, price, trigger_price.0
        );

        Ok(Order {
            order_id: order_id.clone(),
            client_order_id,
            symbol,
            side: close_side,
            order_type,
            quantity,
            price,
            stop_price,
            status: OrderStatus::Pending,
            filled_quantity: Quantity(0.0),
            average_price: None,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        })
    }

    /// Calculate limit price with slippage tolerance
    fn calculate_limit_price(&self, side: Side, current_price: Price) -> Price {
        let slippage_multiplier = match side {
            Side::Bid => 1.0 + (self.slippage_tolerance / 100.0), // Buy: add slippage
            Side::Ask => 1.0 - (self.slippage_tolerance / 100.0), // Sell: subtract slippage
        };

        Price(current_price.0 * slippage_multiplier)
    }

    /// Validate that the stop-loss order can be executed
    pub fn validate_stop_order(&self, order: &Order) -> Result<()> {
        if order.quantity.0 <= 0.0 {
            return Err(TradingError::OrderValidation(
                "Stop-loss order quantity must be positive".to_string(),
            ));
        }

        if matches!(order.order_type, OrderType::Limit) && order.price.is_none() {
            return Err(TradingError::OrderValidation(
                "Limit stop-loss order must have a price".to_string(),
            ));
        }

        Ok(())
    }

    /// Execute the stop-loss order (to be integrated with actual execution engine)
    pub async fn execute_stop_order(&self, order: Order) -> Result<Order> {
        self.validate_stop_order(&order)?;

        info!(
            "Executing stop-loss order: {} for {} {}",
            order.order_id, order.quantity.0, order.symbol.0
        );

        // TODO: Integrate with actual order router/execution engine
        // For now, return the order as-is (would be filled by actual execution)

        warn!(
            "Stop-loss execution stub - integrate with OrderRouter for live execution"
        );

        let mut executed_order = order;
        executed_order.status = OrderStatus::Pending;
        executed_order.updated_at = Utc::now();

        Ok(executed_order)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_market_order() {
        let executor = StopLossExecutor::new(true, 0.5);

        let order = executor
            .create_stop_loss_order(
                Symbol("BTCUSDT".to_string()),
                Side::Ask,
                Quantity(1.0),
                Price(50000.0),
                Price(47500.0),
            )
            .unwrap();

        assert_eq!(order.order_type, OrderType::Market);
        assert_eq!(order.side, Side::Ask);
        assert_eq!(order.quantity.0, 1.0);
        assert!(order.price.is_none());
    }

    #[test]
    fn test_create_limit_order() {
        let executor = StopLossExecutor::new(false, 0.5);

        let order = executor
            .create_stop_loss_order(
                Symbol("BTCUSDT".to_string()),
                Side::Ask,
                Quantity(1.0),
                Price(50000.0),
                Price(47500.0),
            )
            .unwrap();

        assert_eq!(order.order_type, OrderType::Limit);
        assert_eq!(order.side, Side::Ask);
        assert!(order.price.is_some());

        // Sell order should have price below current (0.5% slippage)
        let limit_price = order.price.unwrap();
        assert!(limit_price.0 < 50000.0);
        assert!((limit_price.0 - 49750.0).abs() < 1.0); // ~0.5% below
    }

    #[test]
    fn test_calculate_limit_price_buy() {
        let executor = StopLossExecutor::new(false, 1.0);

        let limit = executor.calculate_limit_price(Side::Bid, Price(100.0));
        assert_eq!(limit.0, 101.0); // 1% above for buy
    }

    #[test]
    fn test_calculate_limit_price_sell() {
        let executor = StopLossExecutor::new(false, 1.0);

        let limit = executor.calculate_limit_price(Side::Ask, Price(100.0));
        assert_eq!(limit.0, 99.0); // 1% below for sell
    }

    #[test]
    fn test_validate_order_zero_quantity() {
        let executor = StopLossExecutor::new(true, 0.5);

        let mut order = executor
            .create_stop_loss_order(
                Symbol("BTCUSDT".to_string()),
                Side::Ask,
                Quantity(1.0),
                Price(50000.0),
                Price(47500.0),
            )
            .unwrap();

        order.quantity = Quantity(0.0);
        assert!(executor.validate_stop_order(&order).is_err());
    }

    #[test]
    fn test_validate_limit_order_no_price() {
        let executor = StopLossExecutor::new(false, 0.5);

        let mut order = executor
            .create_stop_loss_order(
                Symbol("BTCUSDT".to_string()),
                Side::Ask,
                Quantity(1.0),
                Price(50000.0),
                Price(47500.0),
            )
            .unwrap();

        order.price = None;
        assert!(executor.validate_stop_order(&order).is_err());
    }
}
