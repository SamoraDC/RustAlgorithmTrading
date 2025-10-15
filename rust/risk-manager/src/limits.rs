use common::{Result, TradingError, types::{Order, Position, OrderType}, config::RiskConfig};
use std::collections::HashMap;

pub struct LimitChecker {
    config: RiskConfig,
    positions: HashMap<String, Position>,
    open_order_count: usize,
    daily_pnl: f64,
}

impl LimitChecker {
    pub fn new(config: RiskConfig) -> Self {
        Self {
            config,
            positions: HashMap::new(),
            open_order_count: 0,
            daily_pnl: 0.0,
        }
    }

    /// Multi-level risk check
    pub fn check(&self, order: &Order) -> Result<()> {
        // Level 1: Order size check
        self.check_order_size(order)?;

        // Level 2: Position size check
        self.check_position_size(order)?;

        // Level 3: Notional exposure check
        self.check_notional_exposure(order)?;

        // Level 4: Open positions count check
        self.check_open_positions()?;

        // Level 5: Daily loss limit check
        self.check_daily_loss()?;

        Ok(())
    }

    fn check_order_size(&self, order: &Order) -> Result<()> {
        let order_value = match order.price {
            Some(price) => price.0 * order.quantity.0,
            None => {
                // Market order - estimate with a buffer
                0.0 // Will be checked at execution time
            }
        };

        if order_value > self.config.max_position_size {
            return Err(TradingError::Risk(format!(
                "Order size {} exceeds max position size {}",
                order_value, self.config.max_position_size
            )));
        }

        Ok(())
    }

    fn check_position_size(&self, order: &Order) -> Result<()> {
        if let Some(position) = self.positions.get(&order.symbol.0) {
            let current_value = position.quantity.0 * position.current_price.0;
            let order_value = order.quantity.0 * order.price.unwrap_or(position.current_price).0;

            let new_value = current_value + order_value;

            if new_value > self.config.max_position_size {
                return Err(TradingError::Risk(format!(
                    "Position size {} would exceed max {}",
                    new_value, self.config.max_position_size
                )));
            }
        }

        Ok(())
    }

    fn check_notional_exposure(&self, order: &Order) -> Result<()> {
        let total_exposure: f64 = self
            .positions
            .values()
            .map(|p| p.quantity.0 * p.current_price.0)
            .sum();

        let order_value = order.quantity.0
            * order
                .price
                .unwrap_or_else(|| self.positions.get(&order.symbol.0).map(|p| p.current_price).unwrap_or(common::types::Price(0.0)))
                .0;

        if total_exposure + order_value > self.config.max_notional_exposure {
            return Err(TradingError::Risk(format!(
                "Total exposure {} would exceed max {}",
                total_exposure + order_value,
                self.config.max_notional_exposure
            )));
        }

        Ok(())
    }

    fn check_open_positions(&self) -> Result<()> {
        if self.open_order_count >= self.config.max_open_positions {
            return Err(TradingError::Risk(format!(
                "Open positions {} would exceed max {}",
                self.open_order_count, self.config.max_open_positions
            )));
        }

        Ok(())
    }

    fn check_daily_loss(&self) -> Result<()> {
        if self.daily_pnl < -self.config.max_loss_threshold {
            return Err(TradingError::Risk(format!(
                "Daily loss {} exceeds threshold {}",
                self.daily_pnl, self.config.max_loss_threshold
            )));
        }

        Ok(())
    }

    /// Update position tracking
    pub fn update_position(&mut self, position: Position) {
        let symbol = position.symbol.0.clone();
        self.daily_pnl += position.realized_pnl;

        if position.quantity.0 == 0.0 {
            self.positions.remove(&symbol);
            if self.open_order_count > 0 {
                self.open_order_count -= 1;
            }
        } else {
            if !self.positions.contains_key(&symbol) {
                self.open_order_count += 1;
            }
            self.positions.insert(symbol, position);
        }
    }

    /// Reset daily P&L (call at start of trading day)
    pub fn reset_daily_pnl(&mut self) {
        self.daily_pnl = 0.0;
    }

    /// Get current positions
    pub fn get_positions(&self) -> &HashMap<String, Position> {
        &self.positions
    }

    /// Get current daily P&L
    pub fn get_daily_pnl(&self) -> f64 {
        self.daily_pnl
    }
}
