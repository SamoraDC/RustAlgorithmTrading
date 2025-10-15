use common::types::Order;

pub struct SlippageEstimator {
}

impl SlippageEstimator {
    pub fn new() -> Self {
        Self {}
    }

    pub fn estimate(&self, order: &Order) -> f64 {
        // TODO: Implement slippage estimation
        // - Walk the order book
        // - Estimate market impact
        0.0
    }
}

impl Default for SlippageEstimator {
    fn default() -> Self {
        Self::new()
    }
}
