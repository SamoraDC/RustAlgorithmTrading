/// High-performance technical indicators with SIMD optimization
use wide::f64x4;

/// Simple Moving Average (SMA)
pub struct SMA {
    window: usize,
    buffer: Vec<f64>,
    position: usize,
    sum: f64,
    count: usize,
}

impl SMA {
    pub fn new(window: usize) -> Self {
        Self {
            window,
            buffer: vec![0.0; window],
            position: 0,
            sum: 0.0,
            count: 0,
        }
    }

    #[inline]
    pub fn update(&mut self, value: f64) -> Option<f64> {
        let old_value = self.buffer[self.position];
        self.buffer[self.position] = value;
        self.position = (self.position + 1) % self.window;

        if self.count < self.window {
            self.sum += value;
            self.count += 1;
            if self.count == self.window {
                Some(self.sum / self.window as f64)
            } else {
                None
            }
        } else {
            self.sum = self.sum - old_value + value;
            Some(self.sum / self.window as f64)
        }
    }
}

/// Exponential Moving Average (EMA)
pub struct EMA {
    alpha: f64,
    value: Option<f64>,
}

impl EMA {
    pub fn new(period: usize) -> Self {
        let alpha = 2.0 / (period as f64 + 1.0);
        Self { alpha, value: None }
    }

    #[inline]
    pub fn update(&mut self, price: f64) -> f64 {
        match self.value {
            Some(prev) => {
                let new_value = self.alpha * price + (1.0 - self.alpha) * prev;
                self.value = Some(new_value);
                new_value
            }
            None => {
                self.value = Some(price);
                price
            }
        }
    }
}

/// Relative Strength Index (RSI)
pub struct RSI {
    gains: SMA,
    losses: SMA,
    last_price: Option<f64>,
}

impl RSI {
    pub fn new(period: usize) -> Self {
        Self {
            gains: SMA::new(period),
            losses: SMA::new(period),
            last_price: None,
        }
    }

    pub fn update(&mut self, price: f64) -> Option<f64> {
        if let Some(last) = self.last_price {
            let change = price - last;
            let gain = if change > 0.0 { change } else { 0.0 };
            let loss = if change < 0.0 { -change } else { 0.0 };

            if let (Some(avg_gain), Some(avg_loss)) =
                (self.gains.update(gain), self.losses.update(loss))
            {
                if avg_loss == 0.0 {
                    Some(100.0)
                } else {
                    let rs = avg_gain / avg_loss;
                    Some(100.0 - (100.0 / (1.0 + rs)))
                }
            } else {
                None
            }
        } else {
            self.last_price = Some(price);
            None
        }
    }
}

/// MACD (Moving Average Convergence Divergence)
pub struct MACD {
    fast_ema: EMA,
    slow_ema: EMA,
    signal_ema: EMA,
}

impl MACD {
    pub fn new(fast_period: usize, slow_period: usize, signal_period: usize) -> Self {
        Self {
            fast_ema: EMA::new(fast_period),
            slow_ema: EMA::new(slow_period),
            signal_ema: EMA::new(signal_period),
        }
    }

    /// Returns (MACD line, Signal line, Histogram)
    pub fn update(&mut self, price: f64) -> (f64, f64, f64) {
        let fast = self.fast_ema.update(price);
        let slow = self.slow_ema.update(price);
        let macd = fast - slow;
        let signal = self.signal_ema.update(macd);
        let histogram = macd - signal;

        (macd, signal, histogram)
    }
}

/// Bollinger Bands
pub struct BollingerBands {
    sma: SMA,
    window: usize,
    buffer: Vec<f64>,
    position: usize,
    count: usize,
}

impl BollingerBands {
    pub fn new(window: usize) -> Self {
        Self {
            sma: SMA::new(window),
            window,
            buffer: vec![0.0; window],
            position: 0,
            count: 0,
        }
    }

    pub fn update(&mut self, value: f64) -> Option<(f64, f64, f64)> {
        self.buffer[self.position] = value;
        self.position = (self.position + 1) % self.window;

        if self.count < self.window {
            self.count += 1;
        }

        if let Some(middle) = self.sma.update(value) {
            let variance = self.calculate_variance(middle);
            let std_dev = variance.sqrt();

            Some((middle - 2.0 * std_dev, middle, middle + 2.0 * std_dev))
        } else {
            None
        }
    }

    fn calculate_variance(&self, mean: f64) -> f64 {
        let mut sum_squared_diff = 0.0;

        for &value in &self.buffer[..self.count] {
            let diff = value - mean;
            sum_squared_diff += diff * diff;
        }

        sum_squared_diff / self.count as f64
    }
}

/// SIMD-accelerated price momentum calculation
#[inline]
pub fn calculate_momentum_simd(prices: &[f64], period: usize) -> Vec<f64> {
    if prices.len() < period {
        return vec![];
    }

    let mut momentum = vec![0.0; prices.len() - period];

    // Process 4 elements at a time with SIMD
    let chunks = (prices.len() - period) / 4;
    for i in 0..chunks {
        let idx = i * 4;

        let current = f64x4::new([
            prices[idx + period],
            prices[idx + period + 1],
            prices[idx + period + 2],
            prices[idx + period + 3],
        ]);
        let old = f64x4::new([
            prices[idx],
            prices[idx + 1],
            prices[idx + 2],
            prices[idx + 3],
        ]);

        let diff = current - old;
        let result = (diff / old) * f64x4::splat(100.0);

        let result_array = result.to_array();
        momentum[idx..idx + 4].copy_from_slice(&result_array);
    }

    // Handle remaining elements
    let remainder_start = chunks * 4;
    for i in remainder_start..(prices.len() - period) {
        let current = prices[i + period];
        let old = prices[i];
        momentum[i] = (current - old) / old * 100.0;
    }

    momentum
}

/// SIMD-accelerated returns calculation
#[inline]
pub fn calculate_returns_simd(prices: &[f64]) -> Vec<f64> {
    if prices.len() < 2 {
        return vec![];
    }

    let mut returns = vec![0.0; prices.len() - 1];

    let chunks = (prices.len() - 1) / 4;
    for i in 0..chunks {
        let idx = i * 4;

        let p1 = f64x4::new([
            prices[idx + 1],
            prices[idx + 2],
            prices[idx + 3],
            prices[idx + 4],
        ]);
        let p0 = f64x4::new([
            prices[idx],
            prices[idx + 1],
            prices[idx + 2],
            prices[idx + 3],
        ]);

        let ratio = p1 / p0;
        let log_returns = ratio.ln();

        let result_array = log_returns.to_array();
        returns[idx..idx + 4].copy_from_slice(&result_array);
    }

    let remainder_start = chunks * 4;
    for i in remainder_start..(prices.len() - 1) {
        returns[i] = (prices[i + 1] / prices[i]).ln();
    }

    returns
}

/// Legacy function interfaces
pub fn rsi(prices: &[f64], period: usize) -> Vec<f64> {
    let mut rsi_calc = RSI::new(period);
    let mut results = Vec::new();

    for &price in prices {
        if let Some(value) = rsi_calc.update(price) {
            results.push(value);
        }
    }

    results
}

pub fn macd(prices: &[f64], fast: usize, slow: usize, signal: usize) -> Vec<f64> {
    let mut macd_calc = MACD::new(fast, slow, signal);
    let mut results = Vec::new();

    for &price in prices {
        let (line, _, _) = macd_calc.update(price);
        results.push(line);
    }

    results
}

pub fn bollinger_bands(prices: &[f64], period: usize, _std_dev: f64) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let mut bb = BollingerBands::new(period);
    let mut lower = Vec::new();
    let mut middle = Vec::new();
    let mut upper = Vec::new();

    for &price in prices {
        if let Some((l, m, u)) = bb.update(price) {
            lower.push(l);
            middle.push(m);
            upper.push(u);
        }
    }

    (lower, middle, upper)
}

pub fn atr(highs: &[f64], lows: &[f64], closes: &[f64], period: usize) -> Vec<f64> {
    let mut results = Vec::new();
    let mut sma = SMA::new(period);

    for i in 1..closes.len() {
        let tr = (highs[i] - lows[i])
            .max((highs[i] - closes[i - 1]).abs())
            .max((lows[i] - closes[i - 1]).abs());

        if let Some(atr_value) = sma.update(tr) {
            results.push(atr_value);
        }
    }

    results
}
