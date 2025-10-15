use common::{config::RiskConfig, types::Position};

pub struct StopManager {
    config: RiskConfig,
}

impl StopManager {
    pub fn new(config: RiskConfig) -> Self {
        Self { config }
    }

    pub fn check(&self, position: &Position) {
        // TODO: Implement stop-loss checks
        // - Static stops
        // - Trailing stops
    }
}
