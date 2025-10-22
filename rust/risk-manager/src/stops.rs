use common::{
    config::RiskConfig,
    types::{Position, Price, Side, Symbol},
    Result, TradingError,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::{debug, info, warn};

/// Stop-loss type configuration
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum StopLossType {
    /// Static stop-loss at a fixed percentage from entry
    Static,
    /// Trailing stop-loss that follows price movements
    Trailing,
    /// Absolute stop-loss at a specific price level
    Absolute,
}

/// Stop-loss configuration per position
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StopLossConfig {
    /// Type of stop-loss
    pub stop_type: StopLossType,
    /// Percentage-based stop (for Static and Trailing)
    pub percentage: Option<f64>,
    /// Absolute price level (for Absolute type)
    pub price_level: Option<Price>,
    /// Maximum loss in absolute value (currency units)
    pub max_loss_value: Option<f64>,
}

impl StopLossConfig {
    /// Create a static stop-loss configuration
    pub fn static_stop(percentage: f64) -> Result<Self> {
        if percentage <= 0.0 || percentage > 100.0 {
            return Err(TradingError::Configuration(
                "Stop-loss percentage must be between 0 and 100".to_string(),
            ));
        }
        Ok(Self {
            stop_type: StopLossType::Static,
            percentage: Some(percentage),
            price_level: None,
            max_loss_value: None,
        })
    }

    /// Create a trailing stop-loss configuration
    pub fn trailing_stop(percentage: f64) -> Result<Self> {
        if percentage <= 0.0 || percentage > 100.0 {
            return Err(TradingError::Configuration(
                "Trailing stop percentage must be between 0 and 100".to_string(),
            ));
        }
        Ok(Self {
            stop_type: StopLossType::Trailing,
            percentage: Some(percentage),
            price_level: None,
            max_loss_value: None,
        })
    }

    /// Create an absolute price stop-loss configuration
    pub fn absolute_stop(price_level: Price) -> Result<Self> {
        if price_level.0 <= 0.0 {
            return Err(TradingError::Configuration(
                "Stop-loss price must be positive".to_string(),
            ));
        }
        Ok(Self {
            stop_type: StopLossType::Absolute,
            percentage: None,
            price_level: Some(price_level),
            max_loss_value: None,
        })
    }

    /// Add maximum loss value constraint
    pub fn with_max_loss(mut self, max_loss: f64) -> Result<Self> {
        if max_loss <= 0.0 {
            return Err(TradingError::Configuration(
                "Maximum loss value must be positive".to_string(),
            ));
        }
        self.max_loss_value = Some(max_loss);
        Ok(self)
    }
}

/// Tracked stop-loss state for a position
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StopLossState {
    config: StopLossConfig,
    /// Current stop-loss trigger price
    trigger_price: Price,
    /// Highest price seen (for trailing stops on long positions)
    highest_price: Price,
    /// Lowest price seen (for trailing stops on short positions)
    lowest_price: Price,
    /// Position entry price
    entry_price: Price,
    /// Position side
    side: Side,
    /// Total loss accumulated
    current_loss: f64,
}

impl StopLossState {
    fn new(position: &Position, config: StopLossConfig) -> Result<Self> {
        let trigger_price = Self::calculate_initial_trigger(
            position.entry_price,
            position.side,
            &config,
        )?;

        Ok(Self {
            config,
            trigger_price,
            highest_price: position.current_price,
            lowest_price: position.current_price,
            entry_price: position.entry_price,
            side: position.side,
            current_loss: position.unrealized_pnl,
        })
    }

    /// Calculate initial trigger price based on configuration
    fn calculate_initial_trigger(
        entry_price: Price,
        side: Side,
        config: &StopLossConfig,
    ) -> Result<Price> {
        match config.stop_type {
            StopLossType::Static | StopLossType::Trailing => {
                let percentage = config.percentage.ok_or_else(|| {
                    TradingError::Configuration(
                        "Percentage required for static/trailing stop".to_string(),
                    )
                })?;

                let multiplier = 1.0 + (percentage / 100.0);
                let trigger = match side {
                    Side::Bid => entry_price.0 * (1.0 - percentage / 100.0), // Long: stop below entry
                    Side::Ask => entry_price.0 * multiplier, // Short: stop above entry
                };

                Ok(Price(trigger))
            }
            StopLossType::Absolute => {
                config.price_level.ok_or_else(|| {
                    TradingError::Configuration(
                        "Price level required for absolute stop".to_string(),
                    )
                })
            }
        }
    }

    /// Update stop-loss state with new price
    fn update(&mut self, current_price: Price) -> bool {
        // Track price extremes
        if current_price.0 > self.highest_price.0 {
            self.highest_price = current_price;
        }
        if current_price.0 < self.lowest_price.0 {
            self.lowest_price = current_price;
        }

        // Update trailing stop if applicable
        if self.config.stop_type == StopLossType::Trailing {
            if let Some(percentage) = self.config.percentage {
                match self.side {
                    Side::Bid => {
                        // Long position: trail up with price
                        let new_trigger = self.highest_price.0 * (1.0 - percentage / 100.0);
                        if new_trigger > self.trigger_price.0 {
                            debug!(
                                "Trailing stop updated: {} -> {}",
                                self.trigger_price.0, new_trigger
                            );
                            self.trigger_price = Price(new_trigger);
                        }
                    }
                    Side::Ask => {
                        // Short position: trail down with price
                        let new_trigger = self.lowest_price.0 * (1.0 + percentage / 100.0);
                        if new_trigger < self.trigger_price.0 {
                            debug!(
                                "Trailing stop updated: {} -> {}",
                                self.trigger_price.0, new_trigger
                            );
                            self.trigger_price = Price(new_trigger);
                        }
                    }
                }
            }
        }

        // Check if stop was hit
        self.is_triggered(current_price)
    }

    /// Check if stop-loss is triggered
    fn is_triggered(&self, current_price: Price) -> bool {
        match self.side {
            Side::Bid => current_price.0 <= self.trigger_price.0, // Long: price dropped below stop
            Side::Ask => current_price.0 >= self.trigger_price.0, // Short: price rose above stop
        }
    }

    /// Check if maximum loss value is exceeded
    fn is_max_loss_exceeded(&self, unrealized_pnl: f64) -> bool {
        if let Some(max_loss) = self.config.max_loss_value {
            return unrealized_pnl <= -max_loss;
        }
        false
    }
}

/// Manages stop-loss orders and triggers
pub struct StopManager {
    config: RiskConfig,
    /// Active stop-loss states per symbol
    stops: HashMap<String, StopLossState>,
    /// Triggered stops pending execution
    triggered_stops: Vec<(Symbol, String)>, // (symbol, reason)
}

impl StopManager {
    pub fn new(config: RiskConfig) -> Self {
        info!("Initializing StopManager with config: stop_loss={}%, trailing={}%",
              config.stop_loss_percent, config.trailing_stop_percent);
        Self {
            config,
            stops: HashMap::new(),
            triggered_stops: Vec::new(),
        }
    }

    /// Add or update stop-loss for a position
    pub fn set_stop(&mut self, position: &Position, config: StopLossConfig) -> Result<()> {
        let symbol_key = position.symbol.0.clone();

        // Validate configuration
        match config.stop_type {
            StopLossType::Static | StopLossType::Trailing => {
                if config.percentage.is_none() {
                    return Err(TradingError::Configuration(
                        "Percentage required for static/trailing stop".to_string(),
                    ));
                }
            }
            StopLossType::Absolute => {
                if config.price_level.is_none() {
                    return Err(TradingError::Configuration(
                        "Price level required for absolute stop".to_string(),
                    ));
                }
            }
        }

        let state = StopLossState::new(position, config)?;

        info!(
            "Stop-loss set for {}: type={:?}, trigger_price={:.8}, entry_price={:.8}",
            symbol_key, state.config.stop_type, state.trigger_price.0, state.entry_price.0
        );

        self.stops.insert(symbol_key, state);
        Ok(())
    }

    /// Remove stop-loss for a symbol
    pub fn remove_stop(&mut self, symbol: &Symbol) {
        if self.stops.remove(&symbol.0).is_some() {
            info!("Stop-loss removed for {}", symbol.0);
        }
    }

    /// Check position against stop-loss rules
    pub fn check(&mut self, position: &Position) -> Option<StopLossTrigger> {
        let symbol_key = &position.symbol.0;

        // If no stop configured, use default from config
        if !self.stops.contains_key(symbol_key) {
            // Auto-configure stop based on config
            if self.config.stop_loss_percent > 0.0 {
                let stop_config = StopLossConfig::static_stop(self.config.stop_loss_percent)
                    .expect("Valid stop-loss percentage from config");

                if let Err(e) = self.set_stop(position, stop_config) {
                    warn!("Failed to auto-configure stop for {}: {}", symbol_key, e);
                    return None;
                }
            } else {
                return None;
            }
        }

        let state = self.stops.get_mut(symbol_key)?;

        // Update state with current price
        let price_triggered = state.update(position.current_price);
        let loss_triggered = state.is_max_loss_exceeded(position.unrealized_pnl);

        if price_triggered || loss_triggered {
            let reason = if price_triggered && loss_triggered {
                format!(
                    "Price stop at {:.8} and max loss ${:.2} both triggered",
                    state.trigger_price.0, state.config.max_loss_value.unwrap_or(0.0)
                )
            } else if price_triggered {
                format!(
                    "{:?} stop triggered at {:.8} (current: {:.8})",
                    state.config.stop_type, state.trigger_price.0, position.current_price.0
                )
            } else {
                format!(
                    "Max loss ${:.2} exceeded (current loss: ${:.2})",
                    state.config.max_loss_value.unwrap_or(0.0),
                    -position.unrealized_pnl
                )
            };

            warn!("STOP-LOSS TRIGGERED for {}: {}", symbol_key, reason);

            let trigger = StopLossTrigger {
                symbol: position.symbol.clone(),
                position: position.clone(),
                trigger_price: state.trigger_price,
                current_price: position.current_price,
                unrealized_pnl: position.unrealized_pnl,
                stop_type: state.config.stop_type,
                reason: reason.clone(),
            };

            self.triggered_stops.push((position.symbol.clone(), reason));

            // Remove stop after triggering
            self.stops.remove(symbol_key);

            return Some(trigger);
        }

        None
    }

    /// Get all active stop-loss states
    pub fn get_active_stops(&self) -> &HashMap<String, StopLossState> {
        &self.stops
    }

    /// Get triggered stops (pending execution)
    pub fn get_triggered_stops(&self) -> &Vec<(Symbol, String)> {
        &self.triggered_stops
    }

    /// Clear triggered stops after processing
    pub fn clear_triggered(&mut self) {
        self.triggered_stops.clear();
    }

    /// Get stop-loss state for a specific symbol
    pub fn get_stop(&self, symbol: &Symbol) -> Option<&StopLossState> {
        self.stops.get(&symbol.0)
    }

    /// Check if a position has an active stop
    pub fn has_stop(&self, symbol: &Symbol) -> bool {
        self.stops.contains_key(&symbol.0)
    }
}

/// Stop-loss trigger event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StopLossTrigger {
    pub symbol: Symbol,
    pub position: Position,
    pub trigger_price: Price,
    pub current_price: Price,
    pub unrealized_pnl: f64,
    pub stop_type: StopLossType,
    pub reason: String,
}

impl StopLossTrigger {
    /// Get the quantity to close (full position)
    pub fn close_quantity(&self) -> common::types::Quantity {
        self.position.quantity
    }

    /// Get the side for the closing order (opposite of position side)
    pub fn close_side(&self) -> Side {
        match self.position.side {
            Side::Bid => Side::Ask, // Close long with sell
            Side::Ask => Side::Bid, // Close short with buy
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    fn create_test_position(symbol: &str, side: Side, entry: f64, current: f64, qty: f64) -> Position {
        let entry_price = Price(entry);
        let current_price = Price(current);
        let quantity = common::types::Quantity(qty);

        let unrealized_pnl = match side {
            Side::Bid => (current - entry) * qty,
            Side::Ask => (entry - current) * qty,
        };

        Position {
            symbol: Symbol(symbol.to_string()),
            side,
            quantity,
            entry_price,
            current_price,
            unrealized_pnl,
            realized_pnl: 0.0,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        }
    }

    fn create_test_config() -> RiskConfig {
        RiskConfig {
            max_position_size: 10000.0,
            max_notional_exposure: 50000.0,
            max_open_positions: 5,
            stop_loss_percent: 5.0,
            trailing_stop_percent: 3.0,
            enable_circuit_breaker: true,
            max_loss_threshold: 1000.0,
        }
    }

    #[test]
    fn test_static_stop_long_position() {
        let mut manager = StopManager::new(create_test_config());
        let position = create_test_position("BTCUSDT", Side::Bid, 50000.0, 50000.0, 1.0);

        let config = StopLossConfig::static_stop(5.0).unwrap();
        manager.set_stop(&position, config).unwrap();

        // Price hasn't hit stop
        let mut pos_updated = position.clone();
        pos_updated.current_price = Price(48000.0); // -4% loss
        assert!(manager.check(&pos_updated).is_none());

        // Price hits stop (5% loss)
        pos_updated.current_price = Price(47500.0);
        let trigger = manager.check(&pos_updated);
        assert!(trigger.is_some());

        let trigger = trigger.unwrap();
        assert_eq!(trigger.stop_type, StopLossType::Static);
        assert_eq!(trigger.close_side(), Side::Ask);
    }

    #[test]
    fn test_static_stop_short_position() {
        let mut manager = StopManager::new(create_test_config());
        let position = create_test_position("ETHUSDT", Side::Ask, 3000.0, 3000.0, 10.0);

        let config = StopLossConfig::static_stop(5.0).unwrap();
        manager.set_stop(&position, config).unwrap();

        // Price hasn't hit stop
        let mut pos_updated = position.clone();
        pos_updated.current_price = Price(3100.0); // -3.3% loss
        assert!(manager.check(&pos_updated).is_none());

        // Price hits stop (5% loss)
        pos_updated.current_price = Price(3150.0);
        let trigger = manager.check(&pos_updated);
        assert!(trigger.is_some());

        let trigger = trigger.unwrap();
        assert_eq!(trigger.stop_type, StopLossType::Static);
        assert_eq!(trigger.close_side(), Side::Bid);
    }

    #[test]
    fn test_trailing_stop_follows_price_up() {
        let mut manager = StopManager::new(create_test_config());
        let position = create_test_position("BTCUSDT", Side::Bid, 50000.0, 50000.0, 1.0);

        let config = StopLossConfig::trailing_stop(3.0).unwrap();
        manager.set_stop(&position, config).unwrap();

        // Price moves up - stop should trail
        let mut pos_updated = position.clone();
        pos_updated.current_price = Price(52000.0);
        assert!(manager.check(&pos_updated).is_none());

        // Get updated state
        let state = manager.get_stop(&position.symbol).unwrap();
        assert!(state.trigger_price.0 > 50000.0 * 0.97); // Stop trailed up

        // Price drops but not below new stop
        pos_updated.current_price = Price(51000.0);
        assert!(manager.check(&pos_updated).is_none());

        // Price drops below trailing stop
        pos_updated.current_price = Price(50000.0);
        let trigger = manager.check(&pos_updated);
        assert!(trigger.is_some());
    }

    #[test]
    fn test_absolute_stop() {
        let mut manager = StopManager::new(create_test_config());
        let position = create_test_position("BTCUSDT", Side::Bid, 50000.0, 50000.0, 1.0);

        let config = StopLossConfig::absolute_stop(Price(48000.0)).unwrap();
        manager.set_stop(&position, config).unwrap();

        // Price above absolute stop
        let mut pos_updated = position.clone();
        pos_updated.current_price = Price(49000.0);
        assert!(manager.check(&pos_updated).is_none());

        // Price at absolute stop
        pos_updated.current_price = Price(48000.0);
        let trigger = manager.check(&pos_updated);
        assert!(trigger.is_some());
    }

    #[test]
    fn test_max_loss_value() {
        let mut manager = StopManager::new(create_test_config());
        let position = create_test_position("BTCUSDT", Side::Bid, 50000.0, 50000.0, 1.0);

        let config = StopLossConfig::static_stop(10.0)
            .unwrap()
            .with_max_loss(2000.0)
            .unwrap();
        manager.set_stop(&position, config).unwrap();

        // Loss below max
        let mut pos_updated = position.clone();
        pos_updated.current_price = Price(49000.0);
        pos_updated.unrealized_pnl = -1000.0;
        assert!(manager.check(&pos_updated).is_none());

        // Loss exceeds max value (even if price stop not hit)
        pos_updated.current_price = Price(47000.0);
        pos_updated.unrealized_pnl = -3000.0;
        let trigger = manager.check(&pos_updated);
        assert!(trigger.is_some());
    }

    #[test]
    fn test_auto_configure_from_config() {
        let config = create_test_config();
        let mut manager = StopManager::new(config);

        // Position without explicit stop should use config default
        let position = create_test_position("BTCUSDT", Side::Bid, 50000.0, 50000.0, 1.0);

        // First check auto-configures (doesn't trigger because price at entry)
        let result = manager.check(&position);
        assert!(result.is_none());
        assert!(manager.has_stop(&position.symbol));

        // Second check should trigger (5% from config)
        let mut pos_updated = position.clone();
        pos_updated.current_price = Price(47400.0); // Just below 5% stop (47500 is the trigger)
        let trigger = manager.check(&pos_updated);
        assert!(trigger.is_some());
    }

    #[test]
    fn test_remove_stop() {
        let mut manager = StopManager::new(create_test_config());
        let position = create_test_position("BTCUSDT", Side::Bid, 50000.0, 50000.0, 1.0);

        let config = StopLossConfig::static_stop(5.0).unwrap();
        manager.set_stop(&position, config).unwrap();

        assert!(manager.has_stop(&position.symbol));
        manager.remove_stop(&position.symbol);
        assert!(!manager.has_stop(&position.symbol));
    }

    #[test]
    fn test_invalid_configurations() {
        assert!(StopLossConfig::static_stop(0.0).is_err());
        assert!(StopLossConfig::static_stop(150.0).is_err());
        assert!(StopLossConfig::trailing_stop(-5.0).is_err());
        assert!(StopLossConfig::absolute_stop(Price(-100.0)).is_err());

        let config = StopLossConfig::static_stop(5.0).unwrap();
        assert!(config.with_max_loss(-100.0).is_err());
    }
}
