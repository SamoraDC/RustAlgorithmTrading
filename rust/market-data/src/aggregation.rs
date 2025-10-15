use common::types::{Bar, Price, Quantity, Symbol, Trade};
use chrono::{DateTime, Duration, Utc};
use std::collections::HashMap;

/// Time window for bar aggregation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TimeWindow {
    Seconds1,
    Seconds5,
    Seconds15,
    Seconds30,
    Minutes1,
    Minutes5,
    Minutes15,
    Minutes30,
    Hours1,
    Hours4,
    Days1,
}

impl TimeWindow {
    pub fn duration(&self) -> Duration {
        match self {
            TimeWindow::Seconds1 => Duration::seconds(1),
            TimeWindow::Seconds5 => Duration::seconds(5),
            TimeWindow::Seconds15 => Duration::seconds(15),
            TimeWindow::Seconds30 => Duration::seconds(30),
            TimeWindow::Minutes1 => Duration::minutes(1),
            TimeWindow::Minutes5 => Duration::minutes(5),
            TimeWindow::Minutes15 => Duration::minutes(15),
            TimeWindow::Minutes30 => Duration::minutes(30),
            TimeWindow::Hours1 => Duration::hours(1),
            TimeWindow::Hours4 => Duration::hours(4),
            TimeWindow::Days1 => Duration::days(1),
        }
    }

    pub fn floor_timestamp(&self, timestamp: DateTime<Utc>) -> DateTime<Utc> {
        let duration = self.duration();
        let seconds = duration.num_seconds();
        let ts_seconds = timestamp.timestamp();
        let floored = (ts_seconds / seconds) * seconds;
        DateTime::from_timestamp(floored, 0).unwrap_or(timestamp)
    }
}

/// Accumulator for building bars from trades
#[derive(Debug, Clone)]
struct BarAccumulator {
    symbol: Symbol,
    window: TimeWindow,
    window_start: DateTime<Utc>,
    open: Option<Price>,
    high: Price,
    low: Price,
    close: Price,
    volume: Quantity,
    trade_count: u64,
}

impl BarAccumulator {
    fn new(symbol: Symbol, window: TimeWindow, timestamp: DateTime<Utc>) -> Self {
        let window_start = window.floor_timestamp(timestamp);

        Self {
            symbol,
            window,
            window_start,
            open: None,
            high: Price(0.0),
            low: Price(f64::MAX),
            close: Price(0.0),
            volume: Quantity(0.0),
            trade_count: 0,
        }
    }

    fn update(&mut self, trade: &Trade) {
        // Set open price on first trade
        if self.open.is_none() {
            self.open = Some(trade.price);
        }

        // Update OHLC
        self.high = Price(self.high.0.max(trade.price.0));
        self.low = Price(self.low.0.min(trade.price.0));
        self.close = trade.price;

        // Update volume
        self.volume = Quantity(self.volume.0 + trade.quantity.0);
        self.trade_count += 1;
    }

    fn to_bar(&self) -> Option<Bar> {
        self.open.map(|open| Bar {
            symbol: self.symbol.clone(),
            open,
            high: self.high,
            low: self.low,
            close: self.close,
            volume: self.volume,
            timestamp: self.window_start,
        })
    }

    fn is_in_window(&self, timestamp: DateTime<Utc>) -> bool {
        let window_end = self.window_start + self.window.duration();
        timestamp >= self.window_start && timestamp < window_end
    }
}

/// Tick-to-bar aggregator with support for multiple timeframes
pub struct BarAggregator {
    accumulators: HashMap<(String, TimeWindow), BarAccumulator>,
    windows: Vec<TimeWindow>,
}

impl BarAggregator {
    pub fn new(windows: Vec<TimeWindow>) -> Self {
        Self {
            accumulators: HashMap::new(),
            windows,
        }
    }

    /// Process a trade and emit completed bars
    pub fn process_trade(&mut self, trade: &Trade) -> Vec<Bar> {
        let mut completed_bars = Vec::new();

        for &window in &self.windows {
            let key = (trade.symbol.0.clone(), window);

            // Get or create accumulator
            let accumulator = self
                .accumulators
                .entry(key.clone())
                .or_insert_with(|| {
                    BarAccumulator::new(trade.symbol.clone(), window, trade.timestamp)
                });

            // Check if trade is in current window
            if !accumulator.is_in_window(trade.timestamp) {
                // Complete the current bar
                if let Some(bar) = accumulator.to_bar() {
                    completed_bars.push(bar);
                }

                // Start new accumulator for new window
                *accumulator = BarAccumulator::new(trade.symbol.clone(), window, trade.timestamp);
            }

            // Update accumulator
            accumulator.update(trade);
        }

        completed_bars
    }

    /// Get current (incomplete) bar for a symbol and window
    pub fn get_current_bar(&self, symbol: &str, window: TimeWindow) -> Option<Bar> {
        let key = (symbol.to_string(), window);
        self.accumulators.get(&key).and_then(|acc| acc.to_bar())
    }

    /// Force completion of all current bars
    pub fn flush(&mut self) -> Vec<Bar> {
        let mut completed_bars = Vec::new();

        for accumulator in self.accumulators.values() {
            if let Some(bar) = accumulator.to_bar() {
                completed_bars.push(bar);
            }
        }

        self.accumulators.clear();

        completed_bars
    }
}

impl Default for BarAggregator {
    fn default() -> Self {
        Self::new(vec![TimeWindow::Minutes1])
    }
}

/// VWAP (Volume Weighted Average Price) calculator
pub struct VwapCalculator {
    cumulative_pv: f64,
    cumulative_volume: f64,
}

impl VwapCalculator {
    pub fn new() -> Self {
        Self {
            cumulative_pv: 0.0,
            cumulative_volume: 0.0,
        }
    }

    pub fn update(&mut self, price: f64, volume: f64) {
        self.cumulative_pv += price * volume;
        self.cumulative_volume += volume;
    }

    pub fn vwap(&self) -> Option<f64> {
        if self.cumulative_volume > 0.0 {
            Some(self.cumulative_pv / self.cumulative_volume)
        } else {
            None
        }
    }
}

impl Default for VwapCalculator {
    fn default() -> Self {
        Self::new()
    }
}

/// Market microstructure features
#[derive(Debug, Clone)]
pub struct MicrostructureFeatures {
    pub spread: f64,
    pub spread_bps: f64,
    pub depth_imbalance: f64,
    pub bid_depth: f64,
    pub ask_depth: f64,
    pub mid_price: f64,
    pub vwap: Option<f64>,
}

impl MicrostructureFeatures {
    pub fn new(
        bid_price: f64,
        ask_price: f64,
        bid_depth: f64,
        ask_depth: f64,
        vwap: Option<f64>,
    ) -> Self {
        let mid_price = (bid_price + ask_price) / 2.0;
        let spread = ask_price - bid_price;
        let spread_bps = (spread / mid_price) * 10000.0;

        let total_depth = bid_depth + ask_depth;
        let depth_imbalance = if total_depth > 0.0 {
            (bid_depth - ask_depth) / total_depth
        } else {
            0.0
        };

        Self {
            spread,
            spread_bps,
            depth_imbalance,
            bid_depth,
            ask_depth,
            mid_price,
            vwap,
        }
    }
}
