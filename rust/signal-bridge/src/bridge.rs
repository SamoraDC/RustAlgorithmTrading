use pyo3::prelude::*;
use pyo3::types::PyList;
use crate::features::FeatureEngine;
use crate::indicators::{RSI, MACD, EMA, SMA, calculate_returns_simd, calculate_momentum_simd};

#[pyclass]
#[derive(Clone)]
pub struct Bar {
    #[pyo3(get, set)]
    pub symbol: String,
    #[pyo3(get, set)]
    pub open: f64,
    #[pyo3(get, set)]
    pub high: f64,
    #[pyo3(get, set)]
    pub low: f64,
    #[pyo3(get, set)]
    pub close: f64,
    #[pyo3(get, set)]
    pub volume: f64,
    #[pyo3(get, set)]
    pub timestamp: i64,
}

#[pymethods]
impl Bar {
    #[new]
    fn new(symbol: String, open: f64, high: f64, low: f64, close: f64, volume: f64, timestamp: i64) -> Self {
        Self {
            symbol,
            open,
            high,
            low,
            close,
            volume,
            timestamp,
        }
    }
}

#[pyclass]
pub struct FeatureComputer {
    engine: FeatureEngine,
    rsi: RSI,
    macd: MACD,
    ema_fast: EMA,
    ema_slow: EMA,
    sma: SMA,
}

#[pymethods]
impl FeatureComputer {
    #[new]
    pub fn new() -> Self {
        Self {
            engine: FeatureEngine::new(),
            rsi: RSI::new(14),
            macd: MACD::new(12, 26, 9),
            ema_fast: EMA::new(12),
            ema_slow: EMA::new(26),
            sma: SMA::new(20),
        }
    }

    /// Compute features from a single bar (streaming mode)
    pub fn compute_streaming(&mut self, bar: &Bar) -> PyResult<Vec<f64>> {
        let close = bar.close;

        let mut features = Vec::with_capacity(10);

        // Price-based features
        features.push(close);

        // RSI
        if let Some(rsi_value) = self.rsi.update(close) {
            features.push(rsi_value);
        } else {
            features.push(50.0); // Neutral value when not enough data
        }

        // MACD
        let (macd_line, signal_line, histogram) = self.macd.update(close);
        features.push(macd_line);
        features.push(signal_line);
        features.push(histogram);

        // EMAs
        let ema_fast = self.ema_fast.update(close);
        let ema_slow = self.ema_slow.update(close);
        features.push(ema_fast);
        features.push(ema_slow);
        features.push(ema_fast - ema_slow); // EMA spread

        // SMA
        if let Some(sma_value) = self.sma.update(close) {
            features.push(sma_value);
            features.push((close - sma_value) / sma_value * 100.0); // Distance from SMA
        } else {
            features.push(close);
            features.push(0.0);
        }

        // Volume features
        features.push(bar.volume);
        features.push((bar.high - bar.low) / close * 100.0); // Range %

        Ok(features)
    }

    /// Compute features from a list of bars (batch mode)
    pub fn compute_batch(&self, py: Python, bars: &PyList) -> PyResult<Vec<Vec<f64>>> {
        let bar_count = bars.len();
        let mut all_features = Vec::with_capacity(bar_count);

        // Extract prices
        let mut closes = Vec::with_capacity(bar_count);
        let mut highs = Vec::with_capacity(bar_count);
        let mut lows = Vec::with_capacity(bar_count);
        let mut volumes = Vec::with_capacity(bar_count);

        for item in bars.iter() {
            let bar: Bar = item.extract()?;
            closes.push(bar.close);
            highs.push(bar.high);
            lows.push(bar.low);
            volumes.push(bar.volume);
        }

        // SIMD-accelerated calculations
        let returns = calculate_returns_simd(&closes);
        let momentum_10 = calculate_momentum_simd(&closes, 10);

        for i in 0..bar_count {
            let mut features = Vec::with_capacity(15);

            features.push(closes[i]);

            // Returns
            if i > 0 && i <= returns.len() {
                features.push(returns[i - 1]);
            } else {
                features.push(0.0);
            }

            // Momentum
            if i >= 10 && (i - 10) < momentum_10.len() {
                features.push(momentum_10[i - 10]);
            } else {
                features.push(0.0);
            }

            // Volume
            features.push(volumes[i]);

            // Range
            let range_pct = (highs[i] - lows[i]) / closes[i] * 100.0;
            features.push(range_pct);

            all_features.push(features);
        }

        Ok(all_features)
    }

    /// Compute market microstructure features
    pub fn compute_microstructure(
        &self,
        bid_price: f64,
        ask_price: f64,
        bid_depth: f64,
        ask_depth: f64,
    ) -> PyResult<Vec<f64>> {
        let mid_price = (bid_price + ask_price) / 2.0;
        let spread = ask_price - bid_price;
        let spread_bps = (spread / mid_price) * 10000.0;

        let total_depth = bid_depth + ask_depth;
        let depth_imbalance = if total_depth > 0.0 {
            (bid_depth - ask_depth) / total_depth
        } else {
            0.0
        };

        Ok(vec![
            spread,
            spread_bps,
            depth_imbalance,
            bid_depth,
            ask_depth,
            mid_price,
        ])
    }
}

/// Python module initialization
#[pymodule]
fn signal_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<FeatureComputer>()?;
    m.add_class::<Bar>()?;
    Ok(())
}
