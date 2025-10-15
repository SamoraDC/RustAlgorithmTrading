# API Documentation

## Core Modules

### 1. Alpaca Client (`src/api/alpaca_client.py`)

#### `AlpacaClient`

Main client for interacting with Alpaca API.

**Initialization:**
```python
from src.api.alpaca_client import AlpacaClient

client = AlpacaClient(
    api_key="your_key",          # Optional: reads from .env
    secret_key="your_secret",    # Optional: reads from .env
    base_url="https://...",      # Optional: reads from .env
    paper=True                   # Use paper trading
)
```

**Methods:**

- `get_account() -> Dict[str, Any]` - Get account information
- `get_positions() -> List[Dict[str, Any]]` - Get all open positions
- `get_historical_bars(symbol, start, end, timeframe) -> DataFrame` - Fetch historical data
- `place_market_order(symbol, qty, side, time_in_force) -> Dict` - Place market order
- `get_orders(status) -> List[Dict]` - Get orders
- `cancel_all_orders() -> bool` - Cancel all open orders
- `close_all_positions() -> bool` - Close all positions

---

### 2. Data Fetcher (`src/data/fetcher.py`)

#### `DataFetcher`

Fetches market data from Alpaca.

**Initialization:**
```python
from src.data.fetcher import DataFetcher

fetcher = DataFetcher(client)
```

**Methods:**

- `fetch_multiple_symbols(symbols, start, end, timeframe) -> Dict[str, DataFrame]`
- `fetch_last_n_days(symbol, days, timeframe) -> DataFrame`
- `get_latest_price(symbol) -> Optional[float]`

---

### 3. Data Preprocessor (`src/data/preprocessor.py`)

#### `DataPreprocessor`

Preprocesses and transforms market data.

**Static Methods:**

- `add_technical_indicators(df) -> DataFrame` - Add SMA, EMA, MACD, RSI, Bollinger Bands, ATR
- `calculate_returns(df, periods) -> DataFrame` - Calculate returns and log returns
- `normalize_data(df, columns, method) -> DataFrame` - Normalize using minmax or zscore
- `handle_missing_data(df, method) -> DataFrame` - Handle missing data
- `detect_outliers(df, column, threshold) -> Series` - Detect outliers using z-score
- `split_train_test(df, train_ratio) -> Tuple[DataFrame, DataFrame]` - Split data

---

### 4. Strategies (`src/strategies/`)

#### Base Strategy Class

All strategies inherit from `Strategy` base class.

**Required Methods:**
- `generate_signals(data: DataFrame) -> List[Signal]`
- `calculate_position_size(signal, account_value, current_position) -> float`

**Built-in Strategies:**

##### MovingAverageCrossover
```python
from src.strategies.moving_average import MovingAverageCrossover

strategy = MovingAverageCrossover(
    fast_period=20,
    slow_period=50,
    position_size=0.95
)
```

##### MeanReversion
```python
from src.strategies.mean_reversion import MeanReversion

strategy = MeanReversion(
    bb_period=20,
    bb_std=2.0,
    rsi_period=14,
    rsi_oversold=30,
    rsi_overbought=70
)
```

##### MomentumStrategy
```python
from src.strategies.momentum import MomentumStrategy

strategy = MomentumStrategy(
    rsi_period=14,
    ema_fast=12,
    ema_slow=26,
    macd_signal=9
)
```

---

### 5. Backtest Engine (`src/backtesting/engine.py`)

#### `BacktestEngine`

Validates strategies on historical data.

**Initialization:**
```python
from src.backtesting.engine import BacktestEngine

engine = BacktestEngine(
    initial_capital=100000.0,
    commission_rate=0.001,
    slippage=0.0005
)
```

**Methods:**

- `run(strategy, data, symbol) -> Dict[str, Any]` - Run backtest

**Returns:**
```python
{
    'symbol': str,
    'initial_capital': float,
    'final_equity': float,
    'total_return': float,
    'total_return_pct': float,
    'annual_return': float,
    'num_trades': int,
    'win_rate': float,
    'sharpe_ratio': float,
    'max_drawdown_pct': float,
    # ... and more metrics
}
```

---

### 6. Monte Carlo Simulator (`src/simulations/monte_carlo.py`)

#### `MonteCarloSimulator`

Risk analysis using Monte Carlo simulations.

**Initialization:**
```python
from src.simulations.monte_carlo import MonteCarloSimulator

simulator = MonteCarloSimulator(
    num_simulations=1000,
    confidence_level=0.95,
    random_seed=42
)
```

**Methods:**

- `simulate_price_paths(initial_price, num_days, mu, sigma, num_paths) -> ndarray`
  - Generate price paths using Geometric Brownian Motion

- `simulate_strategy(strategy, base_data, initial_capital, resample_method) -> Dict`
  - Run Monte Carlo simulation on strategy
  - Resample methods: 'bootstrap', 'block_bootstrap', 'parametric'

- `plot_results(save_path, show_plot) -> None`
  - Generate visualization of results

- `get_percentile_scenarios(percentiles) -> Dict`
  - Get specific percentile scenarios

**Returns from `simulate_strategy`:**
```python
{
    'expected_return': float,
    'median_return': float,
    'var_95': float,  # Value at Risk
    'cvar_95': float,  # Conditional VaR
    'prob_profit': float,
    'percentiles': dict,
    'all_results': list,
    # ... more statistics
}
```

---

### 7. Configuration (`config/config.py`)

#### `ConfigManager`

Manages application configuration from .env file.

**Usage:**
```python
from config.config import get_config

config = get_config()

# Get configuration values
api_key = config.get('alpaca.api_key')
initial_capital = config.get('backtest.initial_capital')

# Convert to dictionary
config_dict = config.to_dict()
```

**Configuration Structure:**
- `alpaca.*` - Alpaca API settings
- `backtest.*` - Backtesting parameters
- `monte_carlo.*` - Monte Carlo settings
- `risk.*` - Risk management parameters
- `logging.*` - Logging configuration

---

### 8. Utilities (`src/utils/`)

#### Logger Setup
```python
from src.utils.logger import setup_logger

setup_logger(
    log_level="INFO",
    log_file="logs/trading.log",
    rotation="10 MB",
    retention="1 week"
)
```

#### Helper Functions
```python
from src.utils.helpers import (
    calculate_position_size,
    format_currency,
    calculate_kelly_criterion,
    calculate_compound_annual_growth_rate,
    annualize_metric
)

# Risk-based position sizing
shares = calculate_position_size(
    account_value=100000,
    risk_per_trade=0.02,
    entry_price=150.0,
    stop_loss_price=145.0
)

# Format currency
formatted = format_currency(12345.67)  # "$12,345.67"

# Kelly criterion
kelly = calculate_kelly_criterion(
    win_rate=0.55,
    avg_win=100,
    avg_loss=50
)
```

---

## Signal Types

```python
from src.strategies.base import SignalType

SignalType.BUY    # Buy signal
SignalType.SELL   # Sell signal
SignalType.HOLD   # Hold/no action
```

## Signal Object

```python
@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    price: float
    quantity: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
```

## Trade Object

```python
@dataclass
class Trade:
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    commission: float = 0.0
```

---

## Error Handling

All modules use loguru for logging. Errors are logged and raised with descriptive messages.

```python
from loguru import logger

try:
    results = engine.run(strategy, data)
except Exception as e:
    logger.error(f"Backtest failed: {e}")
    raise
```

---

## Environment Variables

Required `.env` file variables:

```bash
# Alpaca API
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Backtest (optional)
BACKTEST_INITIAL_CAPITAL=100000
BACKTEST_COMMISSION_RATE=0.001
BACKTEST_SLIPPAGE=0.0005

# Monte Carlo (optional)
MC_NUM_SIMULATIONS=1000
MC_CONFIDENCE_LEVEL=0.95
MC_RANDOM_SEED=42

# Risk Management (optional)
RISK_MAX_POSITION_SIZE=0.95
RISK_PER_TRADE=0.02
RISK_MAX_DRAWDOWN=0.20

# Logging (optional)
LOG_LEVEL=INFO
LOG_FILE=logs/trading.log
```
