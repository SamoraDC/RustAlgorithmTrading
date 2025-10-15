use common::types::{Bar, OrderBook};
use crate::indicators::{RSI, MACD, EMA, SMA, BollingerBands, calculate_returns_simd, calculate_momentum_simd};

pub struct FeatureEngine {
    rsi_14: RSI,
    macd: MACD,
    ema_9: EMA,
    ema_21: EMA,
    sma_50: SMA,
    sma_200: SMA,
    bb: BollingerBands,
}

impl FeatureEngine {
    pub fn new() -> Self {
        Self {
            rsi_14: RSI::new(14),
            macd: MACD::new(12, 26, 9),
            ema_9: EMA::new(9),
            ema_21: EMA::new(21),
            sma_50: SMA::new(50),
            sma_200: SMA::new(200),
            bb: BollingerBands::new(20),
        }
    }

    pub fn compute_features(&mut self, bars: &[Bar], orderbook: &OrderBook) -> Vec<f64> {
        let mut features = Vec::with_capacity(30);

        if bars.is_empty() {
            return features;
        }

        let current = &bars[bars.len() - 1];
        let close = current.close.0;

        // 1. Price features
        features.push(close);
        features.push(current.open.0);
        features.push(current.high.0);
        features.push(current.low.0);

        // 2. Technical indicators (streaming)
        if let Some(rsi) = self.rsi_14.update(close) {
            features.push(rsi);
        } else {
            features.push(50.0);
        }

        let (macd_line, signal, histogram) = self.macd.update(close);
        features.push(macd_line);
        features.push(signal);
        features.push(histogram);

        let ema9 = self.ema_9.update(close);
        let ema21 = self.ema_21.update(close);
        features.push(ema9);
        features.push(ema21);
        features.push(ema9 - ema21); // EMA spread

        if let Some(sma50) = self.sma_50.update(close) {
            features.push(sma50);
            features.push((close - sma50) / sma50 * 100.0);
        } else {
            features.push(close);
            features.push(0.0);
        }

        if let Some(sma200) = self.sma_200.update(close) {
            features.push(sma200);
        } else {
            features.push(close);
        }

        if let Some((lower, middle, upper)) = self.bb.update(close) {
            features.push(lower);
            features.push(middle);
            features.push(upper);
            // %B indicator
            let pct_b = if upper - lower > 0.0 {
                (close - lower) / (upper - lower)
            } else {
                0.5
            };
            features.push(pct_b);
        } else {
            features.push(close);
            features.push(close);
            features.push(close);
            features.push(0.5);
        }

        // 3. Volume features
        features.push(current.volume.0);

        if bars.len() > 1 {
            let prev_volume = bars[bars.len() - 2].volume.0;
            let volume_change = (current.volume.0 - prev_volume) / prev_volume;
            features.push(volume_change);
        } else {
            features.push(0.0);
        }

        // 4. Order book features
        if !orderbook.bids.is_empty() && !orderbook.asks.is_empty() {
            let best_bid = orderbook.bids[0].price.0;
            let best_ask = orderbook.asks[0].price.0;
            let mid = (best_bid + best_ask) / 2.0;
            let spread = best_ask - best_bid;
            let spread_bps = (spread / mid) * 10000.0;

            features.push(best_bid);
            features.push(best_ask);
            features.push(mid);
            features.push(spread);
            features.push(spread_bps);

            // Order book depth (top 5 levels)
            let bid_depth: f64 = orderbook.bids.iter().take(5).map(|l| l.quantity.0).sum();
            let ask_depth: f64 = orderbook.asks.iter().take(5).map(|l| l.quantity.0).sum();
            let total_depth = bid_depth + ask_depth;

            features.push(bid_depth);
            features.push(ask_depth);

            // Depth imbalance
            let imbalance = if total_depth > 0.0 {
                (bid_depth - ask_depth) / total_depth
            } else {
                0.0
            };
            features.push(imbalance);
        } else {
            // Fill with zeros if no order book data
            for _ in 0..8 {
                features.push(0.0);
            }
        }

        // 5. SIMD-accelerated batch features (if enough bars)
        if bars.len() >= 10 {
            let closes: Vec<f64> = bars.iter().map(|b| b.close.0).collect();
            let returns = calculate_returns_simd(&closes);
            let momentum = calculate_momentum_simd(&closes, 10);

            if !returns.is_empty() {
                features.push(returns[returns.len() - 1]);
            } else {
                features.push(0.0);
            }

            if !momentum.is_empty() {
                features.push(momentum[momentum.len() - 1]);
            } else {
                features.push(0.0);
            }
        } else {
            features.push(0.0);
            features.push(0.0);
        }

        features
    }
}

impl Default for FeatureEngine {
    fn default() -> Self {
        Self::new()
    }
}
