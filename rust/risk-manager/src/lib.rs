/// Risk Management Component
///
/// Enforces position limits, tracks P&L, and manages stop-loss triggers.

pub mod limits;
pub mod pnl;
pub mod stops;
pub mod circuit_breaker;

pub use limits::LimitChecker;
pub use pnl::PnLTracker;
pub use stops::{StopManager, StopLossConfig, StopLossType, StopLossTrigger};
pub use circuit_breaker::CircuitBreaker;

use common::{Result, types::{Order, Position}};
use tracing::{info, warn};

pub struct RiskManagerService {
    limit_checker: LimitChecker,
    pnl_tracker: PnLTracker,
    stop_manager: StopManager,
    circuit_breaker: CircuitBreaker,
}

impl RiskManagerService {
    pub fn new(config: common::config::RiskConfig) -> Result<Self> {
        info!("Initializing Risk Manager Service");
        Ok(Self {
            limit_checker: LimitChecker::new(config.clone()),
            pnl_tracker: PnLTracker::new(),
            stop_manager: StopManager::new(config.clone()),
            circuit_breaker: CircuitBreaker::new(config),
        })
    }

    pub fn check_order(&self, order: &Order) -> Result<bool> {
        // Check all risk constraints
        self.limit_checker.check(order)?;
        self.circuit_breaker.check()?;
        Ok(true)
    }

    pub fn update_position(&mut self, position: Position) -> Option<StopLossTrigger> {
        // Update P&L tracking
        self.pnl_tracker.update(&position);

        // Check stop-loss and return trigger if activated
        let trigger = self.stop_manager.check(&position);

        if trigger.is_some() {
            warn!("Stop-loss triggered for position: {:?}", position.symbol);
        }

        trigger
    }

    /// Set a custom stop-loss for a position
    pub fn set_stop_loss(&mut self, position: &Position, config: StopLossConfig) -> Result<()> {
        self.stop_manager.set_stop(position, config)
    }

    /// Remove stop-loss for a symbol
    pub fn remove_stop_loss(&mut self, symbol: &common::types::Symbol) {
        self.stop_manager.remove_stop(symbol);
    }

    /// Get stop manager for direct access
    pub fn stop_manager(&self) -> &StopManager {
        &self.stop_manager
    }

    /// Get mutable stop manager for direct access
    pub fn stop_manager_mut(&mut self) -> &mut StopManager {
        &mut self.stop_manager
    }

    /// Get limit checker for direct access
    pub fn limit_checker(&self) -> &LimitChecker {
        &self.limit_checker
    }

    /// Get P&L tracker for direct access
    pub fn pnl_tracker(&self) -> &PnLTracker {
        &self.pnl_tracker
    }
}
