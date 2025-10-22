use common::{Result, TradingError, config::RiskConfig};

pub struct CircuitBreaker {
    #[allow(dead_code)]
    config: RiskConfig,
    is_tripped: bool,
}

impl CircuitBreaker {
    pub fn new(config: RiskConfig) -> Self {
        Self {
            config,
            is_tripped: false,
        }
    }

    pub fn check(&self) -> Result<()> {
        if self.is_tripped {
            return Err(TradingError::RiskCheck("Circuit breaker tripped".to_string()));
        }
        Ok(())
    }

    pub fn trip(&mut self) {
        self.is_tripped = true;
    }

    pub fn reset(&mut self) {
        self.is_tripped = false;
    }
}
