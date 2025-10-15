# Python Backtesting Framework Guide

## Overview

This document describes the comprehensive Python backtesting framework implemented for the py_rt algorithmic trading system. The framework follows quantitative research best practices and provides an event-driven architecture for realistic strategy backtesting.

## Architecture

### Event-Driven Design

The backtesting engine uses an event queue to process market data, signals, orders, and fills sequentially, mimicking live trading execution:

```
Market Data → Signal Generation → Order Creation → Risk Check → Order Execution → Portfolio Update
```

### Core Components

1. **BacktestEngine** (`src/backtesting/engine.py`)
   - Event queue management
   - Event dispatch and routing
   - Performance metrics calculation

2. **HistoricalDataHandler** (`src/backtesting/data_handler.py`)
   - CSV/Parquet data loading
   - Historical data replay
   - Bar aggregation

3. **SimulatedExecutionHandler** (`src/backtesting/execution_handler.py`)
   - Realistic fill simulation
   - Commission modeling
   - Slippage and market impact

4. **PortfolioHandler** (`src/backtesting/portfolio_handler.py`)
   - Position tracking
   - Cash management
   - Equity curve generation
   - Position sizing strategies

5. **PerformanceAnalyzer** (`src/backtesting/performance.py`)
   - Sharpe/Sortino ratio
   - Maximum drawdown
   - Win rate, profit factor
   - Trade-level statistics

## Data Models

### Pydantic-Based Type Safety

All models use Pydantic for validation:

```python
from src.models.events import MarketEvent, SignalEvent, OrderEvent, FillEvent
from src.models.portfolio import Portfolio, Position, PerformanceMetrics
from src.models.market import Bar, Trade, Quote
```

### Event Types

1. **MarketEvent**: Price updates
2. **SignalEvent**: Trading signals with strength (0-1)
3. **OrderEvent**: Order placement requests
4. **FillEvent**: Execution confirmations

## Strategy Implementation

### Base Strategy Class

All strategies inherit from `BaseStrategy`:

```python
from src.models.events import MarketEvent, SignalEvent
from src.strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def calculate_signals(self, event: MarketEvent) -> List[SignalEvent]:
        # Implement signal logic
        pass
```

### Built-in Strategies

1. **MeanReversionStrategy**
   - Bollinger Bands
   - Z-score threshold
   - Mean reversion entry/exit

2. **MomentumStrategy**
   - Moving average crossovers
   - RSI confirmation
   - Trend following

3. **StatisticalArbitrageStrategy**
   - Pairs trading
   - Cointegration testing
   - Spread-based signals

## Data Pipeline

### DataLoader

Unified data loading with caching:

```python
from src.data import DataLoader

loader = DataLoader(data_dir='data/historical')
df = loader.load_ohlcv(
    symbol='AAPL',
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    timeframe='1D'
)
```

### FeatureEngine

ML-ready feature engineering:

```python
from src.data import FeatureEngine

engine = FeatureEngine(
    include_indicators=True,
    include_price_features=True,
    include_volume_features=True,
)

features_df = engine.create_features(ohlcv_df)
```

Features include:
- Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR)
- Price features (returns, volatility, momentum)
- Volume features (OBV, VWAP, MFI)
- Time features (cyclical encoding)

### TechnicalIndicators

NumPy-vectorized indicator calculations:

```python
from src.data import TechnicalIndicators

indicators = TechnicalIndicators()

# RSI
rsi = indicators.rsi(prices, period=14)

# MACD
macd, signal, hist = indicators.macd(prices, fast=12, slow=26, signal=9)

# Bollinger Bands
upper, middle, lower = indicators.bollinger_bands(prices, period=20, std=2)
```

## Position Sizing

### Available Sizers

1. **FixedAmountSizer**: Fixed dollar amount per trade
2. **PercentageOfEquitySizer**: Percentage of portfolio equity
3. **KellyPositionSizer**: Kelly Criterion with fractional Kelly

Example:

```python
from src.backtesting.portfolio_handler import PercentageOfEquitySizer

sizer = PercentageOfEquitySizer(percentage=0.33)  # 33% per position
portfolio_handler = PortfolioHandler(
    initial_capital=100_000,
    position_sizer=sizer
)
```

## Performance Metrics

### Calculated Metrics

- **Returns**: Total return, annualized return
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Drawdown**: Maximum drawdown, drawdown duration
- **Trade Statistics**: Win rate, profit factor, avg win/loss
- **Execution**: Events processed, events/second

### Example Output

```
==================================================
PERFORMANCE METRICS
==================================================
Total Return (%)       15.24
Sharpe Ratio           1.82
Sortino Ratio          2.45
Max Drawdown (%)       -8.32
Calmar Ratio           1.83

==================================================
TRADE STATISTICS
==================================================
Total Trades           127
Win Rate (%)           58.27
Profit Factor          1.85
Avg Win ($)            324.52
Avg Loss ($)           -189.34
```

## Visualization

### Built-in Plots

```python
from src.utils.visualization import (
    plot_equity_curve,
    plot_drawdown,
    plot_returns_distribution
)

# Equity curve
plot_equity_curve(
    equity_curve=results['equity_curve'],
    title="Strategy Performance",
    save_path="outputs/equity.png"
)

# Drawdown analysis
plot_drawdown(
    equity_curve=results['equity_curve'],
    save_path="outputs/drawdown.png"
)

# Returns distribution
plot_returns_distribution(
    equity_curve=results['equity_curve'],
    save_path="outputs/returns.png"
)
```

## Running a Backtest

### Complete Example

```python
from datetime import datetime
from pathlib import Path

from src.backtesting import (
    BacktestEngine,
    HistoricalDataHandler,
    SimulatedExecutionHandler,
    PortfolioHandler,
)
from src.strategies.mean_reversion import MeanReversionStrategy

# Configuration
symbols = ['AAPL', 'MSFT']
initial_capital = 100_000.0
data_dir = Path('data/historical')

# Initialize components
data_handler = HistoricalDataHandler(
    symbols=symbols,
    data_dir=data_dir,
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
)

execution_handler = SimulatedExecutionHandler(
    commission_rate=0.001,
    slippage_bps=5.0,
    market_impact_bps=2.0,
)

portfolio_handler = PortfolioHandler(
    initial_capital=initial_capital,
)

strategy = MeanReversionStrategy(
    symbols=symbols,
    lookback_period=20,
    num_std=2.0,
)

# Run backtest
engine = BacktestEngine(
    data_handler=data_handler,
    execution_handler=execution_handler,
    portfolio_handler=portfolio_handler,
    strategy=strategy,
)

results = engine.run()

# Analyze results
print(f"Total Return: {results['metrics']['total_return']:.2f}%")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['metrics']['max_drawdown']:.2f}%")
```

## Best Practices

### 1. Data Quality

- Validate OHLC relationships
- Handle missing data appropriately
- Remove outliers and bad ticks
- Use survivorship bias-free data

### 2. Realistic Simulation

- Model transaction costs (commission + slippage)
- Include market impact for large orders
- Use appropriate fill assumptions
- Account for liquidity constraints

### 3. Performance Analysis

- Calculate multiple risk metrics
- Analyze trade-level statistics
- Check for overfitting
- Validate on out-of-sample data

### 4. Position Sizing

- Use risk-based position sizing
- Implement portfolio-level risk limits
- Consider correlation between positions
- Avoid over-concentration

## Integration with Rust

The Python backtesting framework is designed for **offline research and optimization**. Once a strategy is validated:

1. **Python**: Backtest, optimize, train ML models
2. **Export**: Save strategy parameters, ONNX models
3. **Rust**: Implement validated strategy for live trading

### PyO3 Integration

Strategy logic can be exposed to Rust:

```python
# Python strategy
@pyfunction
def generate_signal(price: float, indicators: dict) -> float:
    # Strategy logic
    return signal_strength
```

```rust
// Rust integration
use pyo3::prelude::*;

let signal: f64 = py_module.call_method1("generate_signal", (price, indicators))?;
```

## File Structure

```
src/
├── backtesting/
│   ├── __init__.py
│   ├── engine.py              # Main backtest engine
│   ├── data_handler.py        # Historical data replay
│   ├── execution_handler.py   # Order execution simulation
│   ├── portfolio_handler.py   # Position and cash management
│   └── performance.py         # Performance metrics
├── data/
│   ├── __init__.py
│   ├── loader.py              # Data loading pipeline
│   ├── features.py            # Feature engineering
│   └── indicators.py          # Technical indicators
├── models/
│   ├── __init__.py
│   ├── base.py               # Base Pydantic model
│   ├── events.py             # Event types
│   ├── market.py             # Market data models
│   └── portfolio.py          # Portfolio models
├── strategies/
│   ├── __init__.py
│   ├── base.py               # Base strategy class
│   ├── mean_reversion.py     # Mean reversion strategy
│   ├── momentum.py           # Momentum strategy
│   └── statistical_arbitrage.py  # Pairs trading
└── utils/
    ├── __init__.py
    ├── visualization.py      # Plotting utilities
    └── metrics.py            # Metrics calculation

examples/
└── run_backtest.py           # Complete backtest example
```

## Performance Characteristics

- **Event Processing**: 10,000-50,000 events/second
- **Memory Usage**: ~100MB for 1M bars
- **Vectorized Operations**: NumPy/Pandas for efficiency
- **Type Safety**: Pydantic validation throughout

## Future Enhancements

1. **Multi-asset Portfolio Optimization**
   - Mean-variance optimization
   - Risk parity
   - Black-Litterman model

2. **Walk-Forward Analysis**
   - Rolling window optimization
   - Out-of-sample validation
   - Adaptive parameter tuning

3. **Advanced Execution**
   - TWAP/VWAP algorithms
   - Iceberg orders
   - Dark pool simulation

4. **ML Integration**
   - PyTorch/TensorFlow model training
   - ONNX export for Rust inference
   - Feature importance analysis

## References

- **Event-Driven Architecture**: Michael Halls-Moore, "Advanced Algorithmic Trading"
- **Performance Metrics**: Pardo, "The Evaluation and Optimization of Trading Strategies"
- **Position Sizing**: Ralph Vince, "The Leverage Space Trading Model"
- **Statistical Arbitrage**: Pole, "Statistical Arbitrage: Algorithmic Trading Insights"

---

**Last Updated**: 2025-10-14 | **Version**: 1.0.0
