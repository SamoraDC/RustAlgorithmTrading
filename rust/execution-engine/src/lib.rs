/// Execution Engine Component
///
/// Handles order routing, smart order execution, and slippage minimization.

pub mod router;
pub mod retry;
pub mod slippage;

pub use router::OrderRouter;
pub use retry::RetryPolicy;
pub use slippage::SlippageEstimator;

use common::{Result, types::Order};

pub struct ExecutionEngineService {
    router: OrderRouter,
    slippage_estimator: SlippageEstimator,
}

impl ExecutionEngineService {
    pub async fn new(config: common::config::ExecutionConfig) -> Result<Self> {
        Ok(Self {
            router: OrderRouter::new(config)?,
            slippage_estimator: SlippageEstimator::new(),
        })
    }

    pub async fn submit_order(&self, order: Order) -> Result<()> {
        // Estimate slippage
        let _estimated_slippage = self.slippage_estimator.estimate(&order);

        // Route order (current market price would come from market data feed in production)
        self.router.route(order, None).await?;

        Ok(())
    }
}
