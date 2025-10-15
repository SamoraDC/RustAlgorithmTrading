/// Signal Bridge Component
///
/// Bridges Python ML models with Rust for feature engineering.
/// Provides PyO3 bindings for Python to call Rust feature computation.

pub mod features;
pub mod indicators;
pub mod bridge;

pub use features::FeatureEngine;
pub use indicators::*;

use common::Result;
use pyo3::prelude::*;

/// Main signal bridge service
pub struct SignalBridgeService {
    feature_engine: FeatureEngine,
}

impl SignalBridgeService {
    pub fn new(config: common::config::SignalConfig) -> Result<Self> {
        let feature_engine = FeatureEngine::new();

        Ok(Self {
            feature_engine,
        })
    }
}

/// Python module for feature computation
#[pymodule]
fn signal_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<bridge::FeatureComputer>()?;
    Ok(())
}
