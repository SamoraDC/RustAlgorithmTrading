# Python-Rust Integration Layer: Technical Specifications

## 1. PyO3 Bindings Implementation

### 1.1 Project Structure

```
rust/
├── Cargo.toml
├── src/
│   ├── lib.rs                  # Main library entry point
│   └── python_bindings/
│       ├── mod.rs              # Module declaration
│       ├── backtesting.rs      # Backtesting functions
│       ├── indicators.rs       # Technical indicators
│       ├── risk.rs             # Risk calculations
│       ├── data_structures.rs  # Shared data types
│       └── conversions.rs      # Type conversions
└── python/
    └── py_rt_core/
        ├── __init__.py
        └── stubs/              # Type stubs (.pyi files)
```

### 1.2 Cargo.toml Configuration

```toml
[package]
name = "py_rt_core"
version = "0.1.0"
edition = "2021"

[lib]
name = "py_rt_core"
crate-type = ["cdylib"]  # Dynamic library for Python

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module", "abi3-py38"] }
numpy = "0.20"           # NumPy integration
ndarray = "0.15"         # Multi-dimensional arrays
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Core dependencies
tokio = { version = "1.35", features = ["full"] }
chrono = "0.4"
```

### 1.3 Core Bindings (lib.rs)

```rust
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

mod python_bindings;

use python_bindings::{
    backtesting::*,
    indicators::*,
    risk::*,
};

#[pymodule]
fn py_rt_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // Backtesting functions
    m.add_function(wrap_pyfunction!(backtest_strategy, m)?)?;
    m.add_function(wrap_pyfunction!(simulate_fills, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_slippage, m)?)?;

    // Technical indicators
    m.add_function(wrap_pyfunction!(sma, m)?)?;
    m.add_function(wrap_pyfunction!(ema, m)?)?;
    m.add_function(wrap_pyfunction!(rsi, m)?)?;
    m.add_function(wrap_pyfunction!(macd, m)?)?;
    m.add_function(wrap_pyfunction!(bollinger_bands, m)?)?;
    m.add_function(wrap_pyfunction!(atr, m)?)?;

    // Risk calculations
    m.add_function(wrap_pyfunction!(calculate_var, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_sharpe, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_max_drawdown, m)?)?;
    m.add_function(wrap_pyfunction!(position_size, m)?)?;

    // Classes
    m.add_class::<BacktestConfig>()?;
    m.add_class::<BacktestResults>()?;
    m.add_class::<Position>()?;

    Ok(())
}
```

### 1.4 Technical Indicators (indicators.rs)

```rust
use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1};

#[pyfunction]
pub fn sma<'py>(
    py: Python<'py>,
    prices: PyReadonlyArray1<f64>,
    window: usize,
) -> PyResult<&'py PyArray1<f64>> {
    let prices_slice = prices.as_slice()?;

    if window > prices_slice.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Window size cannot be larger than data length"
        ));
    }

    let mut result = vec![f64::NAN; prices_slice.len()];

    // Calculate SMA
    for i in (window - 1)..prices_slice.len() {
        let sum: f64 = prices_slice[(i - window + 1)..=i].iter().sum();
        result[i] = sum / window as f64;
    }

    Ok(PyArray1::from_vec(py, result))
}

#[pyfunction]
pub fn ema<'py>(
    py: Python<'py>,
    prices: PyReadonlyArray1<f64>,
    window: usize,
) -> PyResult<&'py PyArray1<f64>> {
    let prices_slice = prices.as_slice()?;
    let mut result = vec![f64::NAN; prices_slice.len()];

    let alpha = 2.0 / (window as f64 + 1.0);

    // Initialize with first valid price
    result[0] = prices_slice[0];

    // Calculate EMA
    for i in 1..prices_slice.len() {
        result[i] = alpha * prices_slice[i] + (1.0 - alpha) * result[i - 1];
    }

    Ok(PyArray1::from_vec(py, result))
}

#[pyfunction]
pub fn rsi<'py>(
    py: Python<'py>,
    prices: PyReadonlyArray1<f64>,
    window: usize,
) -> PyResult<&'py PyArray1<f64>> {
    let prices_slice = prices.as_slice()?;
    let mut result = vec![f64::NAN; prices_slice.len()];

    if window >= prices_slice.len() {
        return Ok(PyArray1::from_vec(py, result));
    }

    // Calculate price changes
    let mut gains = Vec::new();
    let mut losses = Vec::new();

    for i in 1..prices_slice.len() {
        let change = prices_slice[i] - prices_slice[i - 1];
        if change > 0.0 {
            gains.push(change);
            losses.push(0.0);
        } else {
            gains.push(0.0);
            losses.push(-change);
        }
    }

    // Calculate RSI
    for i in window..gains.len() {
        let avg_gain: f64 = gains[(i - window)..i].iter().sum::<f64>() / window as f64;
        let avg_loss: f64 = losses[(i - window)..i].iter().sum::<f64>() / window as f64;

        if avg_loss == 0.0 {
            result[i + 1] = 100.0;
        } else {
            let rs = avg_gain / avg_loss;
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs));
        }
    }

    Ok(PyArray1::from_vec(py, result))
}

#[pyfunction]
pub fn macd<'py>(
    py: Python<'py>,
    prices: PyReadonlyArray1<f64>,
    fast_period: usize,
    slow_period: usize,
    signal_period: usize,
) -> PyResult<(&'py PyArray1<f64>, &'py PyArray1<f64>, &'py PyArray1<f64>)> {
    // Calculate fast and slow EMAs
    let fast_ema = ema(py, prices.clone(), fast_period)?;
    let slow_ema = ema(py, prices, slow_period)?;

    let fast_slice = fast_ema.readonly().as_slice()?;
    let slow_slice = slow_ema.readonly().as_slice()?;

    // Calculate MACD line
    let mut macd_line = vec![f64::NAN; fast_slice.len()];
    for i in 0..fast_slice.len() {
        if !fast_slice[i].is_nan() && !slow_slice[i].is_nan() {
            macd_line[i] = fast_slice[i] - slow_slice[i];
        }
    }

    // Calculate signal line (EMA of MACD)
    let macd_array = PyArray1::from_vec(py, macd_line.clone());
    let signal_line = ema(py, macd_array.readonly(), signal_period)?;
    let signal_slice = signal_line.readonly().as_slice()?;

    // Calculate histogram
    let mut histogram = vec![f64::NAN; macd_line.len()];
    for i in 0..macd_line.len() {
        if !macd_line[i].is_nan() && !signal_slice[i].is_nan() {
            histogram[i] = macd_line[i] - signal_slice[i];
        }
    }

    Ok((
        PyArray1::from_vec(py, macd_line),
        signal_line,
        PyArray1::from_vec(py, histogram),
    ))
}

#[pyfunction]
pub fn bollinger_bands<'py>(
    py: Python<'py>,
    prices: PyReadonlyArray1<f64>,
    window: usize,
    num_std: f64,
) -> PyResult<(&'py PyArray1<f64>, &'py PyArray1<f64>, &'py PyArray1<f64>)> {
    let prices_slice = prices.as_slice()?;

    let mut upper = vec![f64::NAN; prices_slice.len()];
    let mut middle = vec![f64::NAN; prices_slice.len()];
    let mut lower = vec![f64::NAN; prices_slice.len()];

    for i in (window - 1)..prices_slice.len() {
        let window_data = &prices_slice[(i - window + 1)..=i];

        // Calculate mean
        let mean = window_data.iter().sum::<f64>() / window as f64;

        // Calculate standard deviation
        let variance = window_data.iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>() / window as f64;
        let std = variance.sqrt();

        middle[i] = mean;
        upper[i] = mean + num_std * std;
        lower[i] = mean - num_std * std;
    }

    Ok((
        PyArray1::from_vec(py, upper),
        PyArray1::from_vec(py, middle),
        PyArray1::from_vec(py, lower),
    ))
}

#[pyfunction]
pub fn atr<'py>(
    py: Python<'py>,
    high: PyReadonlyArray1<f64>,
    low: PyReadonlyArray1<f64>,
    close: PyReadonlyArray1<f64>,
    window: usize,
) -> PyResult<&'py PyArray1<f64>> {
    let high_slice = high.as_slice()?;
    let low_slice = low.as_slice()?;
    let close_slice = close.as_slice()?;

    if high_slice.len() != low_slice.len() || low_slice.len() != close_slice.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "All arrays must have the same length"
        ));
    }

    let mut result = vec![f64::NAN; high_slice.len()];
    let mut true_ranges = Vec::new();

    for i in 1..high_slice.len() {
        let tr = (high_slice[i] - low_slice[i])
            .max(f64::abs(high_slice[i] - close_slice[i - 1]))
            .max(f64::abs(low_slice[i] - close_slice[i - 1]));
        true_ranges.push(tr);
    }

    // Calculate ATR using EMA of true ranges
    for i in (window - 1)..true_ranges.len() {
        let atr_value = true_ranges[(i - window + 1)..=i].iter().sum::<f64>() / window as f64;
        result[i + 1] = atr_value;
    }

    Ok(PyArray1::from_vec(py, result))
}
```

### 1.5 Backtesting Functions (backtesting.rs)

```rust
use pyo3::prelude::*;
use numpy::PyReadonlyArray1;
use serde::{Deserialize, Serialize};

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BacktestConfig {
    #[pyo3(get, set)]
    pub initial_capital: f64,
    #[pyo3(get, set)]
    pub commission: f64,
    #[pyo3(get, set)]
    pub slippage_bps: f64,
    #[pyo3(get, set)]
    pub position_size: f64,
}

#[pymethods]
impl BacktestConfig {
    #[new]
    pub fn new(
        initial_capital: f64,
        commission: f64,
        slippage_bps: f64,
        position_size: f64,
    ) -> Self {
        Self {
            initial_capital,
            commission,
            slippage_bps,
            position_size,
        }
    }
}

#[pyclass]
#[derive(Clone, Debug)]
pub struct BacktestResults {
    #[pyo3(get)]
    pub total_return: f64,
    #[pyo3(get)]
    pub sharpe_ratio: f64,
    #[pyo3(get)]
    pub max_drawdown: f64,
    #[pyo3(get)]
    pub win_rate: f64,
    #[pyo3(get)]
    pub num_trades: usize,
    #[pyo3(get)]
    pub final_equity: f64,
}

#[pymethods]
impl BacktestResults {
    fn __repr__(&self) -> String {
        format!(
            "BacktestResults(return={:.2}%, sharpe={:.2}, max_dd={:.2}%, trades={})",
            self.total_return * 100.0,
            self.sharpe_ratio,
            self.max_drawdown * 100.0,
            self.num_trades
        )
    }
}

#[pyfunction]
pub fn backtest_strategy(
    prices: PyReadonlyArray1<f64>,
    signals: PyReadonlyArray1<i32>,  // 1=buy, -1=sell, 0=hold
    config: &BacktestConfig,
) -> PyResult<BacktestResults> {
    let prices_slice = prices.as_slice()?;
    let signals_slice = signals.as_slice()?;

    if prices_slice.len() != signals_slice.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Prices and signals must have the same length"
        ));
    }

    let mut equity = config.initial_capital;
    let mut position: f64 = 0.0;
    let mut trades = Vec::new();
    let mut equity_curve = Vec::new();

    for i in 0..prices_slice.len() {
        let price = prices_slice[i];
        let signal = signals_slice[i];

        // Calculate slippage
        let slippage = price * (config.slippage_bps / 10000.0);

        // Execute trades
        if signal == 1 && position == 0.0 {
            // Buy
            let shares = (equity * config.position_size) / (price + slippage);
            let cost = shares * (price + slippage) + config.commission;

            if cost <= equity {
                position = shares;
                equity -= cost;
                trades.push((i, "buy", price, shares));
            }
        } else if signal == -1 && position > 0.0 {
            // Sell
            let proceeds = position * (price - slippage) - config.commission;
            equity += proceeds;
            trades.push((i, "sell", price, position));
            position = 0.0;
        }

        // Mark to market
        let mtm_value = equity + (position * price);
        equity_curve.push(mtm_value);
    }

    // Close any open position
    if position > 0.0 {
        let last_price = prices_slice[prices_slice.len() - 1];
        let proceeds = position * last_price - config.commission;
        equity += proceeds;
    }

    // Calculate metrics
    let final_equity = equity_curve[equity_curve.len() - 1];
    let total_return = (final_equity - config.initial_capital) / config.initial_capital;

    let sharpe_ratio = calculate_sharpe(&equity_curve);
    let max_drawdown = calculate_max_drawdown_internal(&equity_curve);

    let winning_trades = trades.iter()
        .filter(|(_, action, price, shares)| {
            if *action == "sell" {
                // Find corresponding buy
                true  // Simplified logic
            } else {
                false
            }
        })
        .count();

    let win_rate = if trades.len() > 0 {
        winning_trades as f64 / (trades.len() / 2) as f64
    } else {
        0.0
    };

    Ok(BacktestResults {
        total_return,
        sharpe_ratio,
        max_drawdown,
        win_rate,
        num_trades: trades.len() / 2,
        final_equity,
    })
}

fn calculate_sharpe(equity_curve: &[f64]) -> f64 {
    if equity_curve.len() < 2 {
        return 0.0;
    }

    let returns: Vec<f64> = equity_curve.windows(2)
        .map(|w| (w[1] - w[0]) / w[0])
        .collect();

    let mean_return = returns.iter().sum::<f64>() / returns.len() as f64;

    let variance = returns.iter()
        .map(|r| (r - mean_return).powi(2))
        .sum::<f64>() / returns.len() as f64;

    let std_dev = variance.sqrt();

    if std_dev == 0.0 {
        0.0
    } else {
        (mean_return / std_dev) * (252.0_f64).sqrt()  // Annualized
    }
}

fn calculate_max_drawdown_internal(equity_curve: &[f64]) -> f64 {
    let mut max_drawdown = 0.0;
    let mut peak = equity_curve[0];

    for &equity in equity_curve.iter() {
        if equity > peak {
            peak = equity;
        }
        let drawdown = (peak - equity) / peak;
        if drawdown > max_drawdown {
            max_drawdown = drawdown;
        }
    }

    max_drawdown
}
```

### 1.6 Python Usage Examples

```python
# python-trading/examples/rust_bindings_demo.py

import numpy as np
import py_rt_core

# Generate sample data
np.random.seed(42)
prices = 100 + np.cumsum(np.random.randn(1000) * 2)

# Calculate technical indicators using Rust
sma_20 = py_rt_core.sma(prices, window=20)
ema_12 = py_rt_core.ema(prices, window=12)
rsi_14 = py_rt_core.rsi(prices, window=14)

macd_line, signal_line, histogram = py_rt_core.macd(
    prices, fast_period=12, slow_period=26, signal_period=9
)

upper, middle, lower = py_rt_core.bollinger_bands(
    prices, window=20, num_std=2.0
)

# Generate simple signals (SMA crossover)
signals = np.zeros(len(prices), dtype=np.int32)
for i in range(1, len(prices)):
    if sma_20[i-1] < prices[i-1] and sma_20[i] >= prices[i]:
        signals[i] = 1  # Buy
    elif sma_20[i-1] > prices[i-1] and sma_20[i] <= prices[i]:
        signals[i] = -1  # Sell

# Run backtest using Rust
config = py_rt_core.BacktestConfig(
    initial_capital=100000.0,
    commission=1.0,
    slippage_bps=5.0,
    position_size=0.95
)

results = py_rt_core.backtest_strategy(prices, signals, config)

print(f"Backtest Results:")
print(f"  Total Return: {results.total_return * 100:.2f}%")
print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"  Max Drawdown: {results.max_drawdown * 100:.2f}%")
print(f"  Win Rate: {results.win_rate * 100:.2f}%")
print(f"  Number of Trades: {results.num_trades}")
print(f"  Final Equity: ${results.final_equity:,.2f}")

# Benchmark: Compare Rust vs Python
import time
import pandas as pd

def python_sma(prices, window):
    return pd.Series(prices).rolling(window).mean().values

# Rust implementation
start = time.perf_counter()
for _ in range(1000):
    result_rust = py_rt_core.sma(prices, 20)
rust_time = time.perf_counter() - start

# Python implementation
start = time.perf_counter()
for _ in range(1000):
    result_python = python_sma(prices, 20)
python_time = time.perf_counter() - start

print(f"\nPerformance Comparison (1000 iterations):")
print(f"  Rust:   {rust_time:.4f}s")
print(f"  Python: {python_time:.4f}s")
print(f"  Speedup: {python_time / rust_time:.2f}x")
```

---

## 2. ZeroMQ Messaging

### 2.1 Message Protocol (Protocol Buffers)

```protobuf
// proto/messages.proto

syntax = "proto3";
package py_rt;

// Market data message
message MarketTick {
    string symbol = 1;
    double bid = 2;
    double ask = 3;
    double last = 4;
    double volume = 5;
    int64 timestamp_us = 6;
    string exchange = 7;
}

// Order request
message OrderRequest {
    string order_id = 1;
    string symbol = 2;
    enum Side {
        BUY = 0;
        SELL = 1;
    }
    Side side = 3;
    double quantity = 4;
    double price = 5;  // 0 for market orders
    enum OrderType {
        MARKET = 0;
        LIMIT = 1;
        STOP = 2;
        STOP_LIMIT = 3;
    }
    OrderType order_type = 6;
    string strategy_id = 7;
}

// Fill report
message FillReport {
    string order_id = 1;
    string fill_id = 2;
    string symbol = 3;
    double filled_quantity = 4;
    double fill_price = 5;
    int64 timestamp_us = 6;
    double commission = 7;
}

// Position snapshot
message PositionSnapshot {
    string symbol = 1;
    double quantity = 2;
    double avg_entry_price = 3;
    double current_price = 4;
    double unrealized_pnl = 5;
    double realized_pnl = 6;
    int64 last_update_us = 7;
}

// Trading signal
message TradingSignal {
    string strategy_id = 1;
    string symbol = 2;
    enum Action {
        NONE = 0;
        BUY = 1;
        SELL = 2;
        CLOSE = 3;
    }
    Action action = 3;
    double confidence = 4;  // 0.0 to 1.0
    double suggested_quantity = 5;
    int64 timestamp_us = 6;
    map<string, double> features = 7;  // ML features
}

// Command message (Python → Rust)
message Command {
    enum Type {
        START_TRADING = 0;
        STOP_TRADING = 1;
        UPDATE_STRATEGY = 2;
        UPDATE_RISK_LIMITS = 3;
        RELOAD_MODEL = 4;
    }
    Type type = 1;
    string payload = 2;  // JSON-encoded parameters
    int64 timestamp_us = 3;
}
```

### 2.2 Rust Publisher

```rust
// rust/messaging/publisher.rs

use zmq::{Context, Socket};
use prost::Message;
use crate::proto::py_rt::{FillReport, PositionSnapshot, MarketTick};

pub struct ZmqPublisher {
    socket: Socket,
    topics: Vec<String>,
}

impl ZmqPublisher {
    pub fn new(address: &str, topics: Vec<String>) -> Result<Self, zmq::Error> {
        let context = Context::new();
        let socket = context.socket(zmq::PUB)?;
        socket.bind(address)?;

        Ok(Self { socket, topics })
    }

    pub fn publish_fill(&self, fill: &FillReport) -> Result<(), Box<dyn std::error::Error>> {
        let topic = b"fills";
        let mut buf = Vec::new();
        fill.encode(&mut buf)?;

        self.socket.send(topic, zmq::SNDMORE)?;
        self.socket.send(&buf, 0)?;

        Ok(())
    }

    pub fn publish_position(&self, position: &PositionSnapshot) -> Result<(), Box<dyn std::error::Error>> {
        let topic = b"positions";
        let mut buf = Vec::new();
        position.encode(&mut buf)?;

        self.socket.send(topic, zmq::SNDMORE)?;
        self.socket.send(&buf, 0)?;

        Ok(())
    }

    pub fn publish_market_data(&self, tick: &MarketTick) -> Result<(), Box<dyn std::error::Error>> {
        let topic = format!("market.{}", tick.symbol);
        let mut buf = Vec::new();
        tick.encode(&mut buf)?;

        self.socket.send(topic.as_bytes(), zmq::SNDMORE)?;
        self.socket.send(&buf, 0)?;

        Ok(())
    }
}
```

### 2.3 Python Subscriber

```python
# python-trading/messaging/subscriber.py

import zmq
import logging
from proto.messages_pb2 import FillReport, PositionSnapshot, MarketTick

logger = logging.getLogger(__name__)

class ZmqSubscriber:
    def __init__(self, address: str, topics: list[str]):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)

        for topic in topics:
            self.socket.subscribe(topic.encode())

        logger.info(f"Subscribed to {address} with topics: {topics}")

    def receive_message(self, timeout_ms: int = 1000):
        """Receive and decode message"""
        try:
            # Set receive timeout
            self.socket.setsockopt(zmq.RCVTIMEO, timeout_ms)

            # Receive topic and message
            topic = self.socket.recv_string()
            msg_bytes = self.socket.recv()

            # Decode based on topic
            if topic == "fills":
                fill = FillReport()
                fill.ParseFromString(msg_bytes)
                return ("fill", fill)

            elif topic == "positions":
                position = PositionSnapshot()
                position.ParseFromString(msg_bytes)
                return ("position", position)

            elif topic.startswith("market."):
                tick = MarketTick()
                tick.ParseFromString(msg_bytes)
                return ("market_data", tick)

            else:
                logger.warning(f"Unknown topic: {topic}")
                return (None, None)

        except zmq.Again:
            # Timeout
            return (None, None)
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return (None, None)

    def close(self):
        self.socket.close()
        self.context.term()

# Example usage
if __name__ == "__main__":
    subscriber = ZmqSubscriber(
        address="tcp://localhost:5555",
        topics=["fills", "positions", "market.BTC/USD"]
    )

    while True:
        msg_type, msg = subscriber.receive_message()

        if msg_type == "fill":
            print(f"Fill: {msg.symbol} {msg.filled_quantity} @ {msg.fill_price}")

        elif msg_type == "position":
            print(f"Position: {msg.symbol} qty={msg.quantity} P&L={msg.unrealized_pnl:.2f}")

        elif msg_type == "market_data":
            print(f"Market: {msg.symbol} bid={msg.bid} ask={msg.ask}")
```

---

## 3. Shared Memory IPC

### 3.1 Ring Buffer Implementation

```rust
// rust/ipc/ring_buffer.rs

use std::sync::atomic::{AtomicU64, Ordering};
use std::mem::MaybeUninit;

pub struct RingBuffer<T, const CAPACITY: usize> {
    buffer: Box<[MaybeUninit<T>; CAPACITY]>,
    read_pos: AtomicU64,
    write_pos: AtomicU64,
}

impl<T: Copy, const CAPACITY: usize> RingBuffer<T, CAPACITY> {
    pub fn new() -> Self {
        Self {
            buffer: Box::new(unsafe { MaybeUninit::uninit().assume_init() }),
            read_pos: AtomicU64::new(0),
            write_pos: AtomicU64::new(0),
        }
    }

    pub fn push(&self, item: T) -> bool {
        let write = self.write_pos.load(Ordering::Acquire);
        let read = self.read_pos.load(Ordering::Acquire);

        let next_write = write.wrapping_add(1);

        // Check if buffer is full
        if next_write.wrapping_sub(read) >= CAPACITY as u64 {
            return false;  // Buffer full
        }

        // Write data
        unsafe {
            let ptr = &self.buffer[write as usize % CAPACITY] as *const _ as *mut T;
            ptr.write(item);
        }

        // Update write position
        self.write_pos.store(next_write, Ordering::Release);
        true
    }

    pub fn pop(&self) -> Option<T> {
        let read = self.read_pos.load(Ordering::Acquire);
        let write = self.write_pos.load(Ordering::Acquire);

        // Check if buffer is empty
        if read == write {
            return None;
        }

        // Read data
        let item = unsafe {
            let ptr = &self.buffer[read as usize % CAPACITY] as *const _ as *mut T;
            ptr.read()
        };

        // Update read position
        self.read_pos.store(read.wrapping_add(1), Ordering::Release);
        Some(item)
    }

    pub fn len(&self) -> usize {
        let write = self.write_pos.load(Ordering::Acquire);
        let read = self.read_pos.load(Ordering::Acquire);
        write.wrapping_sub(read) as usize
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

unsafe impl<T: Copy, const CAPACITY: usize> Send for RingBuffer<T, CAPACITY> {}
unsafe impl<T: Copy, const CAPACITY: usize> Sync for RingBuffer<T, CAPACITY> {}
```

### 3.2 Shared Memory Setup

```rust
// rust/ipc/shared_memory.rs

use shared_memory::{Shmem, ShmemConf, ShmemError};
use std::sync::Arc;
use crate::ipc::ring_buffer::RingBuffer;

#[repr(C)]
#[derive(Copy, Clone)]
pub struct MarketDataRecord {
    pub symbol_id: u32,
    pub price: f64,
    pub volume: f64,
    pub timestamp_us: u64,
}

const BUFFER_SIZE: usize = 10000;

pub struct SharedMarketData {
    _shmem: Shmem,
    buffer: Arc<RingBuffer<MarketDataRecord, BUFFER_SIZE>>,
}

impl SharedMarketData {
    pub fn create(name: &str) -> Result<Self, ShmemError> {
        let size = std::mem::size_of::<RingBuffer<MarketDataRecord, BUFFER_SIZE>>();

        let shmem = ShmemConf::new()
            .size(size)
            .flink(name)
            .create()?;

        let buffer = unsafe {
            let ptr = shmem.as_ptr() as *mut RingBuffer<MarketDataRecord, BUFFER_SIZE>;
            ptr.write(RingBuffer::new());
            Arc::from_raw(ptr)
        };

        Ok(Self { _shmem: shmem, buffer })
    }

    pub fn open(name: &str) -> Result<Self, ShmemError> {
        let shmem = ShmemConf::new()
            .flink(name)
            .open()?;

        let buffer = unsafe {
            let ptr = shmem.as_ptr() as *mut RingBuffer<MarketDataRecord, BUFFER_SIZE>;
            Arc::from_raw(ptr)
        };

        Ok(Self { _shmem: shmem, buffer })
    }

    pub fn push(&self, record: MarketDataRecord) -> bool {
        self.buffer.push(record)
    }

    pub fn pop(&self) -> Option<MarketDataRecord> {
        self.buffer.pop()
    }
}
```

### 3.3 Python Shared Memory Access

```python
# python-trading/ipc/shared_memory.py

import mmap
import struct
import ctypes
from dataclasses import dataclass

@dataclass
class MarketDataRecord:
    symbol_id: int
    price: float
    volume: float
    timestamp_us: int

    STRUCT_FORMAT = "=Iddd"  # uint32, 3x double
    STRUCT_SIZE = struct.calcsize(STRUCT_FORMAT)

class SharedMarketData:
    def __init__(self, name: str, create: bool = False):
        self.name = name
        self.buffer_size = 10000
        self.record_size = MarketDataRecord.STRUCT_SIZE

        # Size includes ring buffer metadata (read/write positions)
        self.total_size = (
            self.buffer_size * self.record_size +
            16  # 2x u64 for read/write positions
        )

        if create:
            # Create new shared memory
            self.shm = mmap.mmap(-1, self.total_size, self.name)
        else:
            # Open existing shared memory
            self.shm = mmap.mmap(-1, self.total_size, self.name)

    def read_positions(self):
        """Read atomic counters"""
        read_pos = struct.unpack("=Q", self.shm[0:8])[0]
        write_pos = struct.unpack("=Q", self.shm[8:16])[0]
        return read_pos, write_pos

    def pop(self) -> MarketDataRecord | None:
        """Pop record from ring buffer"""
        read_pos, write_pos = self.read_positions()

        if read_pos == write_pos:
            return None  # Empty

        # Calculate offset
        index = read_pos % self.buffer_size
        offset = 16 + (index * self.record_size)

        # Read record
        data = self.shm[offset:offset + self.record_size]
        symbol_id, price, volume, timestamp_us = struct.unpack(
            MarketDataRecord.STRUCT_FORMAT, data
        )

        # Update read position (atomic)
        new_read_pos = read_pos + 1
        self.shm[0:8] = struct.pack("=Q", new_read_pos)

        return MarketDataRecord(symbol_id, price, volume, timestamp_us)

    def close(self):
        self.shm.close()
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-14
