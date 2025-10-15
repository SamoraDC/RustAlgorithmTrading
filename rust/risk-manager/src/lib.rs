/// Risk Management Component
///
/// Enforces position limits, tracks P&L, and manages stop-loss triggers.

pub mod limits;
pub mod pnl;
pub mod stops;
pub mod circuit_breaker;

pub use limits::LimitChecker;
pub use pnl::PnLTracker;
pub use stops::StopManager;
pub use circuit_breaker::CircuitBreaker;

use common::{Result, types::{Order, Position}};

pub struct RiskManagerService {
    limit_checker: LimitChecker,
    pnl_tracker: PnLTracker,
    stop_manager: StopManager,
    circuit_breaker: CircuitBreaker,
}

impl RiskManagerService {
    pub fn new(config: common::config::RiskConfig) -> Result<Self> {
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

    pub fn update_position(&mut self, position: Position) {
        self.pnl_tracker.update(&position);
        self.stop_manager.check(&position);
    }
}
