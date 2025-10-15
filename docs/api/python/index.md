# Python API Reference

Complete API reference for all Python modules in the py_rt trading system.

## Overview

The Python layer provides:
- Trading strategy development
- Backtesting framework
- ML model integration
- Data analysis tools
- Alpaca API client

## Module Structure

```
src/
├── api/                   # API clients
│   └── alpaca_client.py  # Alpaca Markets integration
├── strategies/            # Trading strategies
│   ├── base.py           # Base strategy class
│   ├── momentum.py       # Momentum strategy
│   ├── mean_reversion.py # Mean reversion strategy
│   └── ml/               # ML-based strategies
├── backtesting/          # Backtesting engine
│   ├── engine.py         # Backtest execution
│   ├── metrics.py        # Performance metrics
│   └── walk_forward.py   # Walk-forward analysis
├── data/                 # Data management
│   ├── fetcher.py        # Data fetching
│   └── preprocessor.py   # Data preprocessing
└── utils/                # Utilities
    ├── logger.py         # Logging configuration
    └── helpers.py        # Helper functions
```

## Quick Links

### Core Modules
- [Strategies](strategies.md) - Trading strategy base classes
- [Backtesting](backtesting.md) - Backtesting engine
- [Data](data.md) - Data fetching and preprocessing
- [API Clients](api-clients.md) - External API integrations

### ML Modules
- [Features](ml/features.md) - Feature engineering
- [Models](ml/models.md) - ML model classes
- [Validation](ml/validation.md) - Model validation

### Utilities
- [Logger](utils/logger.md) - Logging configuration
- [Helpers](utils/helpers.md) - Utility functions

## Installation

```bash
# Install with uv
uv sync

# Install development dependencies
uv sync --dev
```

## Basic Usage

### Strategy Development

```python
from src.strategies.base import Strategy
from src.data.fetcher import DataFetcher
import pandas as pd

class MyStrategy(Strategy):
    """Custom trading strategy."""

    def __init__(self, short_window: int = 10, long_window: int = 30):
        super().__init__("MyStrategy")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals."""
        # Calculate moving averages
        short_ma = data['close'].rolling(self.short_window).mean()
        long_ma = data['close'].rolling(self.long_window).mean()

        # Generate signals
        signals = pd.Series(0, index=data.index)
        signals[short_ma > long_ma] = 1   # Buy signal
        signals[short_ma < long_ma] = -1  # Sell signal

        return signals

    def calculate_position_size(self, signal: int,
                               capital: float,
                               price: float) -> int:
        """Calculate position size based on signal."""
        if signal == 0:
            return 0

        # Use 10% of capital per trade
        position_value = capital * 0.1
        shares = int(position_value / price)

        return shares * signal  # Positive for long, negative for short
```

### Backtesting

```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.metrics import calculate_metrics
from datetime import datetime, timedelta

# Initialize backtest engine
engine = BacktestEngine(
    initial_capital=100000.0,
    commission=0.001,  # 0.1% commission
    slippage=0.0005    # 0.05% slippage
)

# Fetch historical data
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

fetcher = DataFetcher()
data = fetcher.get_bars(
    symbol="AAPL",
    start=start_date,
    end=end_date,
    timeframe="1Day"
)

# Run backtest
strategy = MyStrategy(short_window=10, long_window=30)
results = engine.run(strategy, data)

# Calculate metrics
metrics = calculate_metrics(results)
print(f"Total Return: {metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
```

### ML Integration

```python
from src.strategies.ml.models.price_predictor import PricePredictor
from src.strategies.ml.features.feature_engineering import FeatureEngineer

# Create feature engineer
feature_eng = FeatureEngineer()
features = feature_eng.create_features(data)

# Train price predictor
model = PricePredictor(
    lookback_window=20,
    prediction_horizon=5
)

X_train, X_test, y_train, y_test = feature_eng.train_test_split(
    features, test_size=0.2
)

model.fit(X_train, y_train)

# Generate predictions
predictions = model.predict(X_test)
```

## API Classes

### Strategy Base Class

```python
class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals from market data."""
        pass

    @abstractmethod
    def calculate_position_size(self, signal: int,
                               capital: float,
                               price: float) -> int:
        """Calculate position size based on signal."""
        pass

    def on_bar(self, bar: dict) -> Optional[dict]:
        """Called on each new bar. Returns order or None."""
        pass

    def on_fill(self, fill: dict):
        """Called when an order is filled."""
        pass
```

### BacktestEngine Class

```python
class BacktestEngine:
    """Backtesting engine for strategy evaluation."""

    def __init__(self,
                 initial_capital: float = 100000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0,
                 enable_short: bool = True):
        """Initialize backtest engine."""
        pass

    def run(self,
            strategy: Strategy,
            data: pd.DataFrame) -> BacktestResults:
        """Run backtest on historical data."""
        pass

    def run_walk_forward(self,
                        strategy: Strategy,
                        data: pd.DataFrame,
                        train_period: int,
                        test_period: int) -> WalkForwardResults:
        """Run walk-forward optimization."""
        pass
```

### DataFetcher Class

```python
class DataFetcher:
    """Fetch historical market data."""

    def __init__(self, api_key: str = None, secret_key: str = None):
        """Initialize data fetcher with API credentials."""
        pass

    def get_bars(self,
                 symbol: str,
                 start: datetime,
                 end: datetime,
                 timeframe: str = "1Day") -> pd.DataFrame:
        """Fetch OHLCV bar data."""
        pass

    def get_trades(self,
                   symbol: str,
                   start: datetime,
                   end: datetime) -> pd.DataFrame:
        """Fetch individual trade data."""
        pass
```

## Data Structures

### Bar (OHLCV)

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Bar:
    """OHLCV bar data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float = None
```

### Signal

```python
@dataclass
class Signal:
    """Trading signal."""
    symbol: str
    timestamp: datetime
    signal: int  # 1 = buy, -1 = sell, 0 = hold
    confidence: float  # 0.0 to 1.0
    metadata: dict = None
```

### Position

```python
@dataclass
class Position:
    """Trading position."""
    symbol: str
    quantity: int  # Positive = long, negative = short
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
```

## Configuration

### Environment Variables

```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""

    # Alpaca API
    alpaca_api_key: str
    alpaca_secret_key: str
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Backtesting
    initial_capital: float = 100000.0
    commission: float = 0.001
    slippage: float = 0.0005

    class Config:
        env_file = ".env"

settings = Settings()
```

## Error Handling

```python
from src.utils.errors import (
    DataError,
    ValidationError,
    APIError,
    BacktestError
)

try:
    data = fetcher.get_bars("AAPL", start, end)
except APIError as e:
    logger.error(f"API error: {e}")
except DataError as e:
    logger.error(f"Data error: {e}")
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/python/test_strategies.py
```

## Examples

See the [examples/](../../examples/) directory for complete examples:

- `basic_backtest.py` - Simple strategy backtest
- `monte_carlo_simulation.py` - Risk analysis
- `strategy_comparison.py` - Compare multiple strategies
- `ml_strategy_example.py` - ML-based strategy

## Type Hints

All Python code uses type hints for better IDE support:

```python
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

def calculate_returns(prices: pd.Series,
                     periods: int = 1) -> pd.Series:
    """Calculate percentage returns."""
    return prices.pct_change(periods)

def generate_signals(data: pd.DataFrame,
                    threshold: float = 0.02) -> pd.Series:
    """Generate trading signals based on threshold."""
    returns = calculate_returns(data['close'])
    signals = pd.Series(0, index=data.index)
    signals[returns > threshold] = 1
    signals[returns < -threshold] = -1
    return signals
```

## Next Steps

- [Rust API Reference](../rust/index.md)
- [REST API](../rest/index.md)
- [WebSocket API](../websocket/index.md)
- [Strategy Development Guide](../../guides/strategy-development.md)

---

**Last Updated**: 2025-10-14
