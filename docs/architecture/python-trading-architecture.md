# Python Algorithmic Trading Platform Architecture
## Backtesting & Monte Carlo Simulation System with Alpaca API Integration

**Document Version:** 1.0
**Created:** 2025-10-14
**Author:** System Architect Agent (Hive Mind Swarm)
**Status:** Design Complete - Ready for Implementation

---

## Executive Summary

This document provides the comprehensive system architecture for a Python-based algorithmic trading platform featuring:

- **Backtesting Engine**: Historical strategy validation with realistic market simulation
- **Monte Carlo Simulator**: Risk assessment and portfolio optimization via simulation
- **Live Trading Integration**: Seamless Alpaca API integration for paper and live trading
- **Strategy Framework**: Modular, extensible framework for trading algorithms
- **Performance Analytics**: Comprehensive metrics and visualization tools

### Key Design Principles

- **Modularity**: Loosely coupled components with clear interfaces
- **Testability**: Comprehensive unit and integration testing
- **Performance**: Vectorized operations with NumPy/Pandas
- **Reproducibility**: Deterministic backtests with seed control
- **Scalability**: From single-symbol to multi-asset portfolios

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Components](#2-architecture-components)
3. [Data Layer Architecture](#3-data-layer-architecture)
4. [Backtesting Engine](#4-backtesting-engine)
5. [Monte Carlo Simulator](#5-monte-carlo-simulator)
6. [Strategy Framework](#6-strategy-framework)
7. [Risk Management](#7-risk-management)
8. [API Integration](#8-api-integration)
9. [Performance & Metrics](#9-performance--metrics)
10. [Deployment & Configuration](#10-deployment--configuration)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL DATA SOURCES                         │
├──────────────────────────────────────────────────────────────────────┤
│  Alpaca API  │  Yahoo Finance  │  Polygon.io  │  CSV/Parquet Files   │
└──────┬──────┴────────┬─────────┴──────┬──────┴──────────┬────────────┘
       │               │                │                  │
       ▼               ▼                ▼                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                          │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │   Alpaca    │  │   Yahoo     │  │  Polygon    │  │   Local     ││
│  │   Client    │  │   Client    │  │   Client    │  │   Loader    ││
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘│
│         │                │                │                  │        │
│         └────────────────┼────────────────┼──────────────────┘        │
│                          ▼                                            │
│                  ┌──────────────┐                                    │
│                  │  Data        │                                    │
│                  │  Normalizer  │                                    │
│                  └──────┬───────┘                                    │
└─────────────────────────┼──────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE LAYER                            │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Time Series Database (Parquet/HDF5)                         │  │
│  │  - Historical OHLCV bars                                      │  │
│  │  - Tick-level data (optional)                                 │  │
│  │  - Fundamental data                                           │  │
│  │  - Alternative data feeds                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────┬────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        STRATEGY FRAMEWORK                             │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Strategy   │  │  Indicators  │  │   Signal     │              │
│  │     Base     │  │   Library    │  │  Generator   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                      │
│         └──────────────────┴──────────────────┘                      │
└─────────────────────────┬────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     EXECUTION MODES (3 PARALLEL PATHS)                │
└──────────────────────────────────────────────────────────────────────┘

PATH 1: BACKTESTING          PATH 2: MONTE CARLO         PATH 3: LIVE TRADING
       │                            │                            │
       ▼                            ▼                            ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│  Backtest    │            │  Monte Carlo │            │    Live      │
│   Engine     │            │  Simulator   │            │   Executor   │
│              │            │              │            │              │
│ - Event Loop │            │ - Scenarios  │            │ - Order Mgmt │
│ - Fills Sim  │            │ - Paths      │            │ - Position   │
│ - Slippage   │            │ - Stats      │            │ - Fill Proc  │
└──────┬───────┘            └──────┬───────┘            └──────┬───────┘
       │                            │                            │
       ▼                            ▼                            ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│   Portfolio  │            │  Risk        │            │   Alpaca     │
│   Simulator  │            │  Analytics   │            │   API        │
└──────┬───────┘            └──────┬───────┘            └──────┬───────┘
       │                            │                            │
       └────────────────────────────┴────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      ANALYTICS & REPORTING LAYER                      │
├──────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Performance  │  │  Visualizer  │  │   Report     │              │
│  │   Metrics    │  │  (Plotly)    │  │  Generator   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| **Package Manager** | uv | Latest | 10-100x faster than pip, consistent environments |
| **Core Data** | Pandas | 2.x | DataFrame operations, time series |
| **Numerical** | NumPy | 1.26+ | Vectorized computations |
| **API Client** | alpaca-py | Latest | Official Alpaca SDK |
| **Backtesting** | Backtrader | 1.9+ | Mature, extensible backtesting framework |
| **Alternative BT** | VectorBT | 0.26+ | Vectorized backtesting (optional) |
| **Visualization** | Plotly | 5.x | Interactive charts and dashboards |
| **Statistics** | SciPy | 1.11+ | Statistical analysis, optimization |
| **ML (Optional)** | scikit-learn | 1.4+ | Feature engineering, ML models |
| **Storage** | PyArrow/Parquet | 15.x | Columnar storage for time series |
| **Config** | Pydantic | 2.x | Type-safe configuration |
| **Testing** | Pytest | 8.x | Unit and integration tests |
| **Logging** | Loguru | 0.7+ | Structured logging |

### 1.3 Project Structure

```
python-trading/
├── pyproject.toml              # uv project configuration
├── uv.lock                     # Dependency lock file
├── README.md
├── .env.example
│
├── src/
│   └── trading/
│       ├── __init__.py
│       │
│       ├── data/                      # Data Layer
│       │   ├── __init__.py
│       │   ├── providers/
│       │   │   ├── alpaca.py          # Alpaca data client
│       │   │   ├── yahoo.py           # Yahoo Finance client
│       │   │   ├── polygon.py         # Polygon.io client
│       │   │   └── base.py            # Abstract data provider
│       │   ├── storage/
│       │   │   ├── parquet.py         # Parquet storage backend
│       │   │   ├── hdf5.py            # HDF5 storage (alternative)
│       │   │   └── cache.py           # In-memory cache
│       │   ├── normalizer.py          # Data normalization
│       │   └── schemas.py             # Pydantic data models
│       │
│       ├── strategies/                # Strategy Framework
│       │   ├── __init__.py
│       │   ├── base.py                # Abstract strategy class
│       │   ├── indicators/
│       │   │   ├── technical.py       # Technical indicators
│       │   │   ├── fundamental.py     # Fundamental indicators
│       │   │   └── custom.py          # Custom indicators
│       │   ├── examples/
│       │   │   ├── sma_crossover.py   # Example: SMA crossover
│       │   │   ├── mean_reversion.py  # Example: Mean reversion
│       │   │   └── momentum.py        # Example: Momentum
│       │   └── signals.py             # Signal generation
│       │
│       ├── backtesting/               # Backtesting Engine
│       │   ├── __init__.py
│       │   ├── engine.py              # Core backtest engine
│       │   ├── event_loop.py          # Event-driven simulation
│       │   ├── portfolio.py           # Portfolio state tracking
│       │   ├── execution/
│       │   │   ├── fills.py           # Fill simulation
│       │   │   ├── slippage.py        # Slippage models
│       │   │   └── commissions.py     # Commission models
│       │   └── validators.py          # Trade validation
│       │
│       ├── monte_carlo/               # Monte Carlo Simulator
│       │   ├── __init__.py
│       │   ├── simulator.py           # Core MC simulator
│       │   ├── path_generator.py      # Price path generation
│       │   ├── scenarios/
│       │   │   ├── geometric_brownian.py  # GBM model
│       │   │   ├── jump_diffusion.py      # Jump diffusion
│       │   │   └── regime_switching.py    # Regime-switching
│       │   └── analysis.py            # MC results analysis
│       │
│       ├── risk/                      # Risk Management
│       │   ├── __init__.py
│       │   ├── position_sizing.py     # Kelly, Fixed fractional
│       │   ├── var.py                 # Value at Risk
│       │   ├── drawdown.py            # Drawdown analysis
│       │   └── constraints.py         # Trading constraints
│       │
│       ├── execution/                 # Live Trading
│       │   ├── __init__.py
│       │   ├── alpaca_executor.py     # Alpaca order execution
│       │   ├── order_manager.py       # Order lifecycle
│       │   └── fill_processor.py      # Fill handling
│       │
│       ├── analytics/                 # Performance Analytics
│       │   ├── __init__.py
│       │   ├── metrics.py             # Performance metrics
│       │   ├── attribution.py         # Return attribution
│       │   ├── tearsheet.py           # Tearsheet generator
│       │   └── comparison.py          # Strategy comparison
│       │
│       ├── visualization/             # Visualization
│       │   ├── __init__.py
│       │   ├── charts.py              # Plotly charts
│       │   ├── dashboard.py           # Interactive dashboard
│       │   └── reports.py             # HTML/PDF reports
│       │
│       └── utils/                     # Utilities
│           ├── __init__.py
│           ├── config.py              # Configuration loader
│           ├── logging.py             # Logging setup
│           └── helpers.py             # Helper functions
│
├── tests/
│   ├── unit/
│   │   ├── test_data.py
│   │   ├── test_strategies.py
│   │   ├── test_backtesting.py
│   │   └── test_monte_carlo.py
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   └── test_api_integration.py
│   └── fixtures/
│       ├── sample_data.parquet
│       └── test_configs.yaml
│
├── examples/
│   ├── 01_data_ingestion.py
│   ├── 02_simple_backtest.py
│   ├── 03_monte_carlo.py
│   ├── 04_optimization.py
│   └── 05_live_trading.py
│
├── notebooks/
│   ├── exploratory_analysis.ipynb
│   ├── strategy_development.ipynb
│   └── performance_review.ipynb
│
├── config/
│   ├── default.yaml               # Default configuration
│   ├── strategies/
│   │   ├── sma_crossover.yaml
│   │   └── mean_reversion.yaml
│   └── data_sources.yaml
│
└── data/                          # Local data storage
    ├── historical/
    ├── cache/
    └── results/
```

---

## 2. Architecture Components

### 2.1 Data Layer

**Responsibility**: Unified interface for market data acquisition, normalization, and storage.

#### 2.1.1 Data Provider Interface

```python
# src/trading/data/providers/base.py

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import pandas as pd
from pydantic import BaseModel

class BarData(BaseModel):
    """Normalized OHLCV bar"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    trade_count: Optional[int] = None

class DataProvider(ABC):
    """Abstract data provider interface"""

    @abstractmethod
    async def get_bars(
        self,
        symbols: List[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1D"
    ) -> pd.DataFrame:
        """Fetch historical OHLCV bars"""
        pass

    @abstractmethod
    async def get_latest_bar(self, symbol: str) -> BarData:
        """Fetch most recent bar"""
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        pass
```

#### 2.1.2 Alpaca Data Provider Implementation

```python
# src/trading/data/providers/alpaca.py

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from .base import DataProvider, BarData
import pandas as pd
from datetime import datetime
from typing import List

class AlpacaDataProvider(DataProvider):
    """Alpaca Markets data provider"""

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.client = StockHistoricalDataClient(api_key, secret_key)
        self.paper = paper

    async def get_bars(
        self,
        symbols: List[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1D"
    ) -> pd.DataFrame:
        """Fetch historical bars from Alpaca"""

        # Convert timeframe string to Alpaca TimeFrame
        tf_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
            "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
            "1H": TimeFrame.Hour,
            "1D": TimeFrame.Day
        }

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            start=start,
            end=end,
            timeframe=tf_map.get(timeframe, TimeFrame.Day)
        )

        bars = self.client.get_stock_bars(request)

        # Convert to normalized DataFrame
        df = bars.df
        df = df.reset_index()
        df = df.rename(columns={
            'symbol': 'symbol',
            'timestamp': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'vwap': 'vwap',
            'trade_count': 'trade_count'
        })

        return df

    async def get_latest_bar(self, symbol: str) -> BarData:
        """Fetch latest bar"""
        from datetime import timedelta

        end = datetime.now()
        start = end - timedelta(days=1)

        df = await self.get_bars([symbol], start, end, "1Min")
        latest = df.iloc[-1]

        return BarData(
            symbol=latest['symbol'],
            timestamp=latest['timestamp'],
            open=latest['open'],
            high=latest['high'],
            low=latest['low'],
            close=latest['close'],
            volume=latest['volume'],
            vwap=latest.get('vwap'),
            trade_count=latest.get('trade_count')
        )

    def is_market_open(self) -> bool:
        """Check if US market is open"""
        from alpaca.trading.client import TradingClient

        trading_client = TradingClient(
            self.client.api_key,
            self.client.secret_key,
            paper=self.paper
        )

        clock = trading_client.get_clock()
        return clock.is_open
```

#### 2.1.3 Data Storage Backend

```python
# src/trading/data/storage/parquet.py

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from typing import List, Optional

class ParquetStorage:
    """Parquet-based time series storage"""

    def __init__(self, base_path: str = "./data/historical"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_bars(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Save OHLCV bars to Parquet with partitioning"""

        # Add partition columns
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month

        # Define file path with partitioning
        file_path = self.base_path / f"{symbol}_{timeframe}.parquet"

        # Write with compression
        table = pa.Table.from_pandas(df)
        pq.write_table(
            table,
            file_path,
            compression='snappy',
            partition_cols=['year', 'month']
        )

    def load_bars(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load bars from Parquet with optional date filtering"""

        file_path = self.base_path / f"{symbol}_{timeframe}.parquet"

        if not file_path.exists():
            return pd.DataFrame()

        # Read with filtering
        filters = []
        if start:
            filters.append(('timestamp', '>=', start))
        if end:
            filters.append(('timestamp', '<=', end))

        df = pq.read_table(
            file_path,
            filters=filters if filters else None
        ).to_pandas()

        # Drop partition columns
        df = df.drop(columns=['year', 'month'], errors='ignore')

        return df

    def append_bars(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Append new bars to existing dataset"""

        existing_df = self.load_bars(symbol, timeframe)

        if not existing_df.empty:
            # Remove duplicates by timestamp
            combined = pd.concat([existing_df, df])
            combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
            combined = combined.sort_values('timestamp')
        else:
            combined = df

        self.save_bars(combined, symbol, timeframe)
```

---

## 3. Data Layer Architecture

### 3.1 Data Schemas (Pydantic Models)

```python
# src/trading/data/schemas.py

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Literal
from decimal import Decimal

class BarData(BaseModel):
    """OHLCV bar with validation"""
    symbol: str = Field(..., min_length=1, max_length=10)
    timestamp: datetime
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    vwap: Optional[Decimal] = None
    trade_count: Optional[int] = None

    @validator('high')
    def high_gte_low(cls, v, values):
        if 'low' in values and v < values['low']:
            raise ValueError('high must be >= low')
        return v

    @validator('high')
    def high_gte_open_close(cls, v, values):
        if 'open' in values and v < values['open']:
            raise ValueError('high must be >= open')
        if 'close' in values and v < values['close']:
            raise ValueError('high must be >= close')
        return v

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }

class Position(BaseModel):
    """Portfolio position"""
    symbol: str
    quantity: int
    avg_entry_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal = Decimal(0)
    side: Literal['long', 'short']

    @property
    def total_pnl(self) -> Decimal:
        return self.unrealized_pnl + self.realized_pnl

class Order(BaseModel):
    """Trading order"""
    order_id: str
    symbol: str
    side: Literal['buy', 'sell']
    quantity: int = Field(..., gt=0)
    order_type: Literal['market', 'limit', 'stop', 'stop_limit']
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: Literal['day', 'gtc', 'ioc', 'fok'] = 'day'
    status: Literal['pending', 'submitted', 'filled', 'canceled', 'rejected']
    filled_quantity: int = 0
    filled_avg_price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

class Signal(BaseModel):
    """Trading signal"""
    symbol: str
    timestamp: datetime
    signal_type: Literal['entry', 'exit', 'add', 'reduce']
    direction: Literal['long', 'short']
    strength: float = Field(..., ge=0, le=1)  # 0 to 1
    reason: str
    metadata: dict = {}
```

### 3.2 Data Normalizer

```python
# src/trading/data/normalizer.py

import pandas as pd
from typing import Dict, Any
from .schemas import BarData

class DataNormalizer:
    """Normalize data from different providers to common schema"""

    @staticmethod
    def normalize_alpaca_bars(raw_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Alpaca bars to standard schema"""
        normalized = raw_df.rename(columns={
            'symbol': 'symbol',
            'timestamp': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'vwap': 'vwap',
            'trade_count': 'trade_count'
        })

        # Ensure datetime index
        normalized['timestamp'] = pd.to_datetime(normalized['timestamp'])
        normalized = normalized.set_index('timestamp')

        return normalized

    @staticmethod
    def normalize_yahoo_bars(raw_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Yahoo Finance bars"""
        normalized = raw_df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        })

        # Yahoo uses index for dates
        normalized = normalized.reset_index()
        normalized = normalized.rename(columns={'Date': 'timestamp'})
        normalized['timestamp'] = pd.to_datetime(normalized['timestamp'])
        normalized = normalized.set_index('timestamp')

        return normalized

    @staticmethod
    def validate_bars(df: pd.DataFrame) -> bool:
        """Validate bar data integrity"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']

        # Check required columns
        if not all(col in df.columns for col in required_cols):
            return False

        # Check high >= low
        if not (df['high'] >= df['low']).all():
            return False

        # Check high >= open, close
        if not ((df['high'] >= df['open']) & (df['high'] >= df['close'])).all():
            return False

        # Check low <= open, close
        if not ((df['low'] <= df['open']) & (df['low'] <= df['close'])).all():
            return False

        # Check for NaN values
        if df[required_cols].isna().any().any():
            return False

        return True
```

---

## 4. Backtesting Engine

### 4.1 Event-Driven Backtesting Architecture

```python
# src/trading/backtesting/engine.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
import pandas as pd
from ..strategies.base import Strategy
from ..data.schemas import BarData, Order, Position, Signal
from .portfolio import Portfolio
from .execution.fills import FillSimulator

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    initial_capital: Decimal = Decimal("100000")
    commission_pct: Decimal = Decimal("0.001")  # 0.1%
    slippage_pct: Decimal = Decimal("0.0005")   # 0.05%
    allow_fractional_shares: bool = False
    max_position_size: Decimal = Decimal("0.25")  # 25% of portfolio
    stop_loss_pct: Optional[Decimal] = None
    take_profit_pct: Optional[Decimal] = None

class BacktestEngine:
    """Event-driven backtesting engine"""

    def __init__(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        config: BacktestConfig
    ):
        self.strategy = strategy
        self.data = data
        self.config = config

        # Initialize components
        self.portfolio = Portfolio(config.initial_capital)
        self.fill_simulator = FillSimulator(
            commission_pct=config.commission_pct,
            slippage_pct=config.slippage_pct
        )

        # State tracking
        self.current_bar: Optional[BarData] = None
        self.bar_index: int = 0
        self.orders: List[Order] = []
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []

    def run(self) -> Dict:
        """Execute backtest"""

        # Initialize strategy
        self.strategy.on_start()

        # Event loop: iterate through each bar
        for idx, row in self.data.iterrows():
            self.bar_index += 1

            # Create bar data
            self.current_bar = BarData(
                symbol=row.get('symbol', 'UNKNOWN'),
                timestamp=idx,
                open=Decimal(str(row['open'])),
                high=Decimal(str(row['high'])),
                low=Decimal(str(row['low'])),
                close=Decimal(str(row['close'])),
                volume=int(row['volume'])
            )

            # Update portfolio with current prices
            self.portfolio.update_prices({
                self.current_bar.symbol: self.current_bar.close
            })

            # Process pending orders
            self._process_pending_orders()

            # Generate signals from strategy
            signals = self.strategy.on_bar(
                self.current_bar,
                self.portfolio
            )

            # Execute signals
            for signal in signals:
                self._execute_signal(signal)

            # Record equity
            self._record_equity()

        # Finalize strategy
        self.strategy.on_stop()

        # Generate results
        return self._generate_results()

    def _execute_signal(self, signal: Signal):
        """Convert signal to order and execute"""

        # Position sizing
        quantity = self._calculate_position_size(signal)

        if quantity == 0:
            return

        # Create order
        order = Order(
            order_id=f"BT-{self.bar_index}-{signal.symbol}",
            symbol=signal.symbol,
            side='buy' if signal.direction == 'long' else 'sell',
            quantity=quantity,
            order_type='market',
            status='pending',
            created_at=self.current_bar.timestamp,
            updated_at=self.current_bar.timestamp
        )

        self.orders.append(order)

    def _process_pending_orders(self):
        """Process pending orders with fill simulation"""

        pending = [o for o in self.orders if o.status == 'pending']

        for order in pending:
            if order.symbol != self.current_bar.symbol:
                continue

            # Simulate fill
            fill = self.fill_simulator.simulate_fill(
                order,
                self.current_bar
            )

            if fill:
                # Update order
                order.status = 'filled'
                order.filled_quantity = fill['quantity']
                order.filled_avg_price = fill['price']
                order.updated_at = self.current_bar.timestamp

                # Update portfolio
                self.portfolio.apply_fill(
                    symbol=order.symbol,
                    quantity=fill['quantity'] if order.side == 'buy' else -fill['quantity'],
                    price=fill['price'],
                    commission=fill['commission']
                )

                # Record trade
                self.trades.append({
                    'timestamp': self.current_bar.timestamp,
                    'symbol': order.symbol,
                    'side': order.side,
                    'quantity': fill['quantity'],
                    'price': fill['price'],
                    'commission': fill['commission'],
                    'order_id': order.order_id
                })

    def _calculate_position_size(self, signal: Signal) -> int:
        """Calculate position size based on risk management rules"""

        # Get available capital
        available_cash = self.portfolio.cash
        current_price = self.current_bar.close

        # Max position value (% of portfolio)
        max_position_value = self.portfolio.total_equity * self.config.max_position_size

        # Calculate quantity
        quantity = int(max_position_value / current_price)

        # Ensure we have enough cash
        total_cost = current_price * Decimal(quantity)
        if total_cost > available_cash:
            quantity = int(available_cash / current_price)

        return quantity

    def _record_equity(self):
        """Record equity curve data point"""
        self.equity_curve.append({
            'timestamp': self.current_bar.timestamp,
            'equity': float(self.portfolio.total_equity),
            'cash': float(self.portfolio.cash),
            'positions_value': float(self.portfolio.positions_value)
        })

    def _generate_results(self) -> Dict:
        """Generate backtest results"""

        equity_df = pd.DataFrame(self.equity_curve)
        trades_df = pd.DataFrame(self.trades)

        return {
            'config': self.config,
            'equity_curve': equity_df,
            'trades': trades_df,
            'final_equity': self.portfolio.total_equity,
            'total_return': (self.portfolio.total_equity / self.config.initial_capital) - 1,
            'num_trades': len(self.trades),
            'positions': self.portfolio.positions
        }
```

### 4.2 Portfolio State Tracker

```python
# src/trading/backtesting/portfolio.py

from decimal import Decimal
from typing import Dict, Optional
from ..data.schemas import Position

class Portfolio:
    """Portfolio state tracker for backtesting"""

    def __init__(self, initial_capital: Decimal):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.realized_pnl = Decimal(0)

    @property
    def positions_value(self) -> Decimal:
        """Total value of all positions"""
        return sum(
            pos.market_value
            for pos in self.positions.values()
        )

    @property
    def total_equity(self) -> Decimal:
        """Total portfolio equity (cash + positions)"""
        return self.cash + self.positions_value

    @property
    def unrealized_pnl(self) -> Decimal:
        """Total unrealized P&L across all positions"""
        return sum(
            pos.unrealized_pnl
            for pos in self.positions.values()
        )

    def update_prices(self, prices: Dict[str, Decimal]):
        """Update current prices for all positions"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                position = self.positions[symbol]
                position.current_price = price
                position.market_value = price * Decimal(abs(position.quantity))

                # Recalculate unrealized P&L
                if position.quantity > 0:  # Long
                    position.unrealized_pnl = (
                        price - position.avg_entry_price
                    ) * Decimal(position.quantity)
                else:  # Short
                    position.unrealized_pnl = (
                        position.avg_entry_price - price
                    ) * Decimal(abs(position.quantity))

    def apply_fill(
        self,
        symbol: str,
        quantity: int,
        price: Decimal,
        commission: Decimal
    ):
        """Apply fill to portfolio state"""

        if symbol not in self.positions:
            # Opening new position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_entry_price=price,
                current_price=price,
                market_value=price * Decimal(abs(quantity)),
                unrealized_pnl=Decimal(0),
                realized_pnl=Decimal(0),
                side='long' if quantity > 0 else 'short'
            )

            # Deduct cost from cash
            total_cost = price * Decimal(abs(quantity)) + commission
            self.cash -= total_cost

        else:
            # Modifying existing position
            position = self.positions[symbol]

            if (position.quantity > 0 and quantity > 0) or \
               (position.quantity < 0 and quantity < 0):
                # Adding to position - recalculate avg entry price
                old_cost = position.avg_entry_price * Decimal(abs(position.quantity))
                new_cost = price * Decimal(abs(quantity))
                total_quantity = position.quantity + quantity

                position.avg_entry_price = (old_cost + new_cost) / Decimal(abs(total_quantity))
                position.quantity = total_quantity

                # Deduct from cash
                self.cash -= (price * Decimal(abs(quantity)) + commission)

            else:
                # Closing/reducing position - realize P&L
                close_quantity = min(abs(quantity), abs(position.quantity))

                if position.quantity > 0:  # Closing long
                    pnl = (price - position.avg_entry_price) * Decimal(close_quantity)
                else:  # Closing short
                    pnl = (position.avg_entry_price - price) * Decimal(close_quantity)

                position.realized_pnl += pnl
                self.realized_pnl += pnl
                position.quantity += quantity

                # Add proceeds to cash
                self.cash += (price * Decimal(abs(quantity)) - commission)

                # Remove position if fully closed
                if position.quantity == 0:
                    del self.positions[symbol]

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
```

### 4.3 Fill Simulator

```python
# src/trading/backtesting/execution/fills.py

from decimal import Decimal
from typing import Dict, Optional
from ...data.schemas import BarData, Order
import random

class FillSimulator:
    """Simulate order fills with slippage and commissions"""

    def __init__(
        self,
        commission_pct: Decimal = Decimal("0.001"),
        slippage_pct: Decimal = Decimal("0.0005")
    ):
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    def simulate_fill(
        self,
        order: Order,
        bar: BarData
    ) -> Optional[Dict]:
        """Simulate order fill for current bar"""

        if order.order_type == 'market':
            return self._fill_market_order(order, bar)
        elif order.order_type == 'limit':
            return self._fill_limit_order(order, bar)
        elif order.order_type == 'stop':
            return self._fill_stop_order(order, bar)

        return None

    def _fill_market_order(self, order: Order, bar: BarData) -> Dict:
        """Fill market order at open with slippage"""

        # Use bar open price as fill price
        base_price = bar.open

        # Apply slippage
        if order.side == 'buy':
            # Slippage increases cost for buys
            fill_price = base_price * (Decimal(1) + self.slippage_pct)
        else:
            # Slippage decreases proceeds for sells
            fill_price = base_price * (Decimal(1) - self.slippage_pct)

        # Calculate commission
        notional = fill_price * Decimal(order.quantity)
        commission = notional * self.commission_pct

        return {
            'quantity': order.quantity,
            'price': fill_price,
            'commission': commission
        }

    def _fill_limit_order(self, order: Order, bar: BarData) -> Optional[Dict]:
        """Fill limit order if price touched"""

        if order.limit_price is None:
            return None

        # Check if limit price was touched during bar
        if order.side == 'buy':
            # Buy limit: fill if low <= limit price
            if bar.low <= order.limit_price:
                fill_price = order.limit_price
            else:
                return None
        else:
            # Sell limit: fill if high >= limit price
            if bar.high >= order.limit_price:
                fill_price = order.limit_price
            else:
                return None

        # Calculate commission
        notional = fill_price * Decimal(order.quantity)
        commission = notional * self.commission_pct

        return {
            'quantity': order.quantity,
            'price': fill_price,
            'commission': commission
        }

    def _fill_stop_order(self, order: Order, bar: BarData) -> Optional[Dict]:
        """Fill stop order if triggered"""

        if order.stop_price is None:
            return None

        # Check if stop was triggered
        if order.side == 'buy':
            # Buy stop: triggered if high >= stop price
            if bar.high >= order.stop_price:
                fill_price = order.stop_price * (Decimal(1) + self.slippage_pct)
            else:
                return None
        else:
            # Sell stop: triggered if low <= stop price
            if bar.low <= order.stop_price:
                fill_price = order.stop_price * (Decimal(1) - self.slippage_pct)
            else:
                return None

        # Calculate commission
        notional = fill_price * Decimal(order.quantity)
        commission = notional * self.commission_pct

        return {
            'quantity': order.quantity,
            'price': fill_price,
            'commission': commission
        }
```

---

## 5. Monte Carlo Simulator

### 5.1 Monte Carlo Engine

```python
# src/trading/monte_carlo/simulator.py

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Callable
import numpy as np
import pandas as pd
from scipy import stats

@dataclass
class MonteCarloConfig:
    """Monte Carlo simulation configuration"""
    num_simulations: int = 1000
    num_periods: int = 252  # Trading days in a year
    initial_capital: Decimal = Decimal("100000")
    confidence_levels: List[float] = None
    random_seed: int = None

    def __post_init__(self):
        if self.confidence_levels is None:
            self.confidence_levels = [0.90, 0.95, 0.99]

class MonteCarloSimulator:
    """Monte Carlo portfolio simulator"""

    def __init__(
        self,
        returns: pd.Series,
        config: MonteCarloConfig
    ):
        self.returns = returns
        self.config = config

        # Set random seed for reproducibility
        if config.random_seed is not None:
            np.random.seed(config.random_seed)

        # Calculate statistics from historical returns
        self.mean_return = returns.mean()
        self.std_return = returns.std()
        self.skewness = returns.skew()
        self.kurtosis = returns.kurtosis()

    def run_geometric_brownian_motion(self) -> pd.DataFrame:
        """Run GBM-based Monte Carlo simulation"""

        simulations = []

        for sim in range(self.config.num_simulations):
            # Generate random returns using GBM
            dt = 1 / 252  # Daily time step
            drift = self.mean_return - 0.5 * (self.std_return ** 2)
            diffusion = self.std_return * np.sqrt(dt)

            # Generate random shocks
            shocks = np.random.normal(0, 1, self.config.num_periods)

            # Calculate returns
            simulated_returns = drift * dt + diffusion * shocks

            # Calculate equity path
            equity_path = [float(self.config.initial_capital)]
            for ret in simulated_returns:
                equity_path.append(equity_path[-1] * (1 + ret))

            simulations.append(equity_path)

        # Convert to DataFrame
        df = pd.DataFrame(simulations).T
        df.index.name = 'period'

        return df

    def run_bootstrap(self, block_size: int = 5) -> pd.DataFrame:
        """Run block bootstrap Monte Carlo simulation"""

        simulations = []
        returns_array = self.returns.values

        for sim in range(self.config.num_simulations):
            # Block bootstrap to preserve autocorrelation
            sampled_returns = []

            while len(sampled_returns) < self.config.num_periods:
                # Random start index
                start_idx = np.random.randint(0, len(returns_array) - block_size)

                # Extract block
                block = returns_array[start_idx:start_idx + block_size]
                sampled_returns.extend(block)

            # Trim to exact size
            sampled_returns = sampled_returns[:self.config.num_periods]

            # Calculate equity path
            equity_path = [float(self.config.initial_capital)]
            for ret in sampled_returns:
                equity_path.append(equity_path[-1] * (1 + ret))

            simulations.append(equity_path)

        df = pd.DataFrame(simulations).T
        df.index.name = 'period'

        return df

    def analyze_results(self, simulations: pd.DataFrame) -> Dict:
        """Analyze Monte Carlo simulation results"""

        final_values = simulations.iloc[-1]

        # Calculate percentiles
        percentiles = {}
        for conf_level in self.config.confidence_levels:
            lower_pct = (1 - conf_level) / 2
            upper_pct = 1 - lower_pct

            percentiles[f"lower_{int(conf_level*100)}"] = np.percentile(
                final_values, lower_pct * 100
            )
            percentiles[f"upper_{int(conf_level*100)}"] = np.percentile(
                final_values, upper_pct * 100
            )

        # Calculate statistics
        results = {
            'mean_final_value': float(final_values.mean()),
            'median_final_value': float(final_values.median()),
            'std_final_value': float(final_values.std()),
            'min_final_value': float(final_values.min()),
            'max_final_value': float(final_values.max()),
            'percentiles': percentiles,
            'prob_positive': float((final_values > self.config.initial_capital).mean()),
            'prob_loss_50pct': float((final_values < self.config.initial_capital * 0.5).mean()),
            'expected_return': float((final_values.mean() / float(self.config.initial_capital)) - 1),
            'sharpe_ratio': self._calculate_sharpe_ratio(simulations)
        }

        return results

    def _calculate_sharpe_ratio(self, simulations: pd.DataFrame) -> float:
        """Calculate average Sharpe ratio across simulations"""

        sharpe_ratios = []

        for col in simulations.columns:
            path = simulations[col]
            returns = path.pct_change().dropna()

            if len(returns) > 0 and returns.std() > 0:
                sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
                sharpe_ratios.append(sharpe)

        return float(np.mean(sharpe_ratios))

    def calculate_var(
        self,
        simulations: pd.DataFrame,
        confidence_level: float = 0.95,
        time_horizon: int = 1
    ) -> float:
        """Calculate Value at Risk"""

        # Get values at time horizon
        if time_horizon < len(simulations):
            values = simulations.iloc[time_horizon]
        else:
            values = simulations.iloc[-1]

        # Calculate VaR
        var = float(self.config.initial_capital) - np.percentile(
            values, (1 - confidence_level) * 100
        )

        return float(var)

    def calculate_cvar(
        self,
        simulations: pd.DataFrame,
        confidence_level: float = 0.95,
        time_horizon: int = 1
    ) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""

        # Get values at time horizon
        if time_horizon < len(simulations):
            values = simulations.iloc[time_horizon]
        else:
            values = simulations.iloc[-1]

        # Calculate VaR threshold
        var_threshold = np.percentile(values, (1 - confidence_level) * 100)

        # Calculate CVaR as average of losses beyond VaR
        tail_losses = values[values <= var_threshold]
        cvar = float(self.config.initial_capital) - float(tail_losses.mean())

        return cvar
```

### 5.2 Path Generation Models

```python
# src/trading/monte_carlo/scenarios/geometric_brownian.py

import numpy as np
from typing import Tuple

class GeometricBrownianMotion:
    """Geometric Brownian Motion price path generator"""

    def __init__(
        self,
        mu: float,          # Drift (expected return)
        sigma: float,       # Volatility
        S0: float,          # Initial price
        T: float = 1.0,     # Time horizon (years)
        dt: float = 1/252   # Time step (daily)
    ):
        self.mu = mu
        self.sigma = sigma
        self.S0 = S0
        self.T = T
        self.dt = dt
        self.num_steps = int(T / dt)

    def generate_path(self, seed: int = None) -> np.ndarray:
        """Generate single price path"""

        if seed is not None:
            np.random.seed(seed)

        # Generate random shocks
        Z = np.random.standard_normal(self.num_steps)

        # Calculate price path
        S = np.zeros(self.num_steps + 1)
        S[0] = self.S0

        for t in range(1, self.num_steps + 1):
            drift = (self.mu - 0.5 * self.sigma**2) * self.dt
            diffusion = self.sigma * np.sqrt(self.dt) * Z[t-1]
            S[t] = S[t-1] * np.exp(drift + diffusion)

        return S

    def generate_paths(self, num_paths: int, seed: int = None) -> np.ndarray:
        """Generate multiple price paths"""

        if seed is not None:
            np.random.seed(seed)

        paths = np.zeros((self.num_steps + 1, num_paths))

        for i in range(num_paths):
            paths[:, i] = self.generate_path()

        return paths

    @staticmethod
    def calibrate_from_returns(returns: np.ndarray) -> Tuple[float, float]:
        """Calibrate mu and sigma from historical returns"""

        # Annualized mean return
        mu = returns.mean() * 252

        # Annualized volatility
        sigma = returns.std() * np.sqrt(252)

        return mu, sigma


# src/trading/monte_carlo/scenarios/jump_diffusion.py

class JumpDiffusionModel:
    """Merton's Jump Diffusion Model"""

    def __init__(
        self,
        mu: float,          # Drift
        sigma: float,       # Volatility
        lambda_: float,     # Jump intensity (jumps per year)
        mu_j: float,        # Mean jump size
        sigma_j: float,     # Jump size volatility
        S0: float,          # Initial price
        T: float = 1.0,
        dt: float = 1/252
    ):
        self.mu = mu
        self.sigma = sigma
        self.lambda_ = lambda_
        self.mu_j = mu_j
        self.sigma_j = sigma_j
        self.S0 = S0
        self.T = T
        self.dt = dt
        self.num_steps = int(T / dt)

    def generate_path(self, seed: int = None) -> np.ndarray:
        """Generate price path with jumps"""

        if seed is not None:
            np.random.seed(seed)

        S = np.zeros(self.num_steps + 1)
        S[0] = self.S0

        for t in range(1, self.num_steps + 1):
            # Diffusion component (GBM)
            Z = np.random.standard_normal()
            drift = (self.mu - 0.5 * self.sigma**2) * self.dt
            diffusion = self.sigma * np.sqrt(self.dt) * Z

            # Jump component (Poisson process)
            N_t = np.random.poisson(self.lambda_ * self.dt)

            if N_t > 0:
                # Generate jump sizes
                jump_sizes = np.random.normal(
                    self.mu_j,
                    self.sigma_j,
                    N_t
                )
                total_jump = np.sum(jump_sizes)
            else:
                total_jump = 0

            # Combine diffusion and jumps
            S[t] = S[t-1] * np.exp(drift + diffusion + total_jump)

        return S
```

---

## 6. Strategy Framework

### 6.1 Base Strategy Class

```python
# src/trading/strategies/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from decimal import Decimal
import pandas as pd
from ..data.schemas import BarData, Signal, Position
from ..backtesting.portfolio import Portfolio

class Strategy(ABC):
    """Abstract base class for trading strategies"""

    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
        self.indicators: Dict[str, pd.Series] = {}

    @abstractmethod
    def on_start(self):
        """Called once at strategy initialization"""
        pass

    @abstractmethod
    def on_bar(self, bar: BarData, portfolio: Portfolio) -> List[Signal]:
        """Called for each bar. Returns list of trading signals."""
        pass

    @abstractmethod
    def on_stop(self):
        """Called once when strategy stops"""
        pass

    def calculate_indicators(self, data: pd.DataFrame):
        """Calculate technical indicators (to be overridden)"""
        pass

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get strategy parameter"""
        return self.parameters.get(name, default)
```

### 6.2 Example Strategy: SMA Crossover

```python
# src/trading/strategies/examples/sma_crossover.py

from typing import List
import pandas as pd
from ..base import Strategy
from ...data.schemas import BarData, Signal, Position
from ...backtesting.portfolio import Portfolio
from datetime import datetime

class SMACompanyStrategy(Strategy):
    """Simple Moving Average Crossover Strategy"""

    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        super().__init__(
            name="SMA_Crossover",
            parameters={
                'fast_period': fast_period,
                'slow_period': slow_period
            }
        )

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_history: List[float] = []
        self.last_signal = None

    def on_start(self):
        """Initialize strategy"""
        self.price_history = []
        self.last_signal = None
        print(f"Starting {self.name} with fast={self.fast_period}, slow={self.slow_period}")

    def on_bar(self, bar: BarData, portfolio: Portfolio) -> List[Signal]:
        """Generate signals based on SMA crossover"""

        signals = []

        # Update price history
        self.price_history.append(float(bar.close))

        # Need enough data for slow SMA
        if len(self.price_history) < self.slow_period:
            return signals

        # Calculate SMAs
        recent_prices = self.price_history[-self.slow_period:]
        fast_sma = sum(recent_prices[-self.fast_period:]) / self.fast_period
        slow_sma = sum(recent_prices) / self.slow_period

        # Get current position
        position = portfolio.get_position(bar.symbol)

        # Golden cross: fast SMA crosses above slow SMA
        if fast_sma > slow_sma and self.last_signal != 'long':
            # Close short if exists
            if position and position.side == 'short':
                signals.append(Signal(
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    signal_type='exit',
                    direction='short',
                    strength=1.0,
                    reason=f"Exit short on golden cross (Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f})"
                ))

            # Enter long
            if not position or position.side != 'long':
                signals.append(Signal(
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    signal_type='entry',
                    direction='long',
                    strength=1.0,
                    reason=f"Golden cross (Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f})"
                ))
                self.last_signal = 'long'

        # Death cross: fast SMA crosses below slow SMA
        elif fast_sma < slow_sma and self.last_signal != 'short':
            # Close long if exists
            if position and position.side == 'long':
                signals.append(Signal(
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    signal_type='exit',
                    direction='long',
                    strength=1.0,
                    reason=f"Exit long on death cross (Fast SMA: {fast_sma:.2f}, Slow SMA: {slow_sma:.2f})"
                ))

            # No shorting in this example, but you could add it here
            self.last_signal = 'short'

        return signals

    def on_stop(self):
        """Clean up"""
        print(f"Stopping {self.name}. Processed {len(self.price_history)} bars.")
```

---

## 7. Risk Management

### 7.1 Position Sizing

```python
# src/trading/risk/position_sizing.py

from decimal import Decimal
from typing import Optional
import numpy as np

class PositionSizer:
    """Position sizing strategies"""

    @staticmethod
    def fixed_fractional(
        account_equity: Decimal,
        risk_per_trade_pct: Decimal,
        entry_price: Decimal,
        stop_loss_price: Decimal
    ) -> int:
        """Fixed fractional position sizing"""

        # Risk amount
        risk_amount = account_equity * risk_per_trade_pct

        # Risk per share
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            return 0

        # Position size
        position_size = int(risk_amount / risk_per_share)

        return position_size

    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Kelly Criterion for optimal position sizing"""

        if avg_loss == 0:
            return 0.0

        # Kelly formula: f = (bp - q) / b
        # where b = odds (avg_win/avg_loss), p = win_rate, q = 1-p
        b = avg_win / abs(avg_loss)
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        # Use half-Kelly for safety (common practice)
        kelly_fraction = max(0, kelly_fraction) * 0.5

        return kelly_fraction

    @staticmethod
    def equal_weight(
        account_equity: Decimal,
        num_positions: int,
        price: Decimal
    ) -> int:
        """Equal weight position sizing"""

        position_value = account_equity / Decimal(num_positions)
        quantity = int(position_value / price)

        return quantity

    @staticmethod
    def volatility_scaled(
        account_equity: Decimal,
        target_volatility: float,
        asset_volatility: float,
        price: Decimal
    ) -> int:
        """Volatility-scaled position sizing"""

        if asset_volatility == 0:
            return 0

        # Scale position by inverse volatility
        vol_ratio = target_volatility / asset_volatility
        position_value = account_equity * Decimal(vol_ratio)

        # Cap at 100% of equity
        position_value = min(position_value, account_equity)

        quantity = int(position_value / price)

        return quantity
```

### 7.2 Risk Metrics

```python
# src/trading/risk/var.py

import numpy as np
import pandas as pd
from scipy import stats

class RiskMetrics:
    """Risk assessment and measurement"""

    @staticmethod
    def value_at_risk(
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = 'historical'
    ) -> float:
        """Calculate Value at Risk"""

        if method == 'historical':
            # Historical VaR
            var = -np.percentile(returns, (1 - confidence_level) * 100)

        elif method == 'parametric':
            # Parametric VaR (assumes normal distribution)
            mu = returns.mean()
            sigma = returns.std()
            z_score = stats.norm.ppf(1 - confidence_level)
            var = -(mu + z_score * sigma)

        elif method == 'cornish_fisher':
            # Cornish-Fisher VaR (accounts for skewness and kurtosis)
            mu = returns.mean()
            sigma = returns.std()
            skew = returns.skew()
            kurt = returns.kurtosis()

            z = stats.norm.ppf(1 - confidence_level)
            z_cf = z + (z**2 - 1) * skew / 6 + \
                   (z**3 - 3*z) * kurt / 24 - \
                   (2*z**3 - 5*z) * (skew**2) / 36

            var = -(mu + z_cf * sigma)

        else:
            raise ValueError(f"Unknown VaR method: {method}")

        return float(var)

    @staticmethod
    def conditional_var(
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""

        var_threshold = -RiskMetrics.value_at_risk(
            returns,
            confidence_level,
            method='historical'
        )

        # Average of losses beyond VaR
        tail_losses = returns[returns <= var_threshold]

        if len(tail_losses) == 0:
            return 0.0

        cvar = -tail_losses.mean()

        return float(cvar)

    @staticmethod
    def maximum_drawdown(equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown"""

        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        max_dd = drawdown.min()

        return float(max_dd)

    @staticmethod
    def calmar_ratio(
        returns: pd.Series,
        equity_curve: pd.Series
    ) -> float:
        """Calculate Calmar Ratio (return / max drawdown)"""

        annual_return = returns.mean() * 252  # Assuming daily returns
        max_dd = abs(RiskMetrics.maximum_drawdown(equity_curve))

        if max_dd == 0:
            return 0.0

        calmar = annual_return / max_dd

        return float(calmar)
```

---

## 8. API Integration

### 8.1 Alpaca Trading Client

```python
# src/trading/execution/alpaca_executor.py

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from typing import Optional
from decimal import Decimal
from ..data.schemas import Order
import uuid

class AlpacaExecutor:
    """Alpaca trading execution client"""

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.client = TradingClient(api_key, secret_key, paper=paper)
        self.paper = paper

    def submit_market_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Submit market order to Alpaca"""

        if client_order_id is None:
            client_order_id = str(uuid.uuid4())

        # Create order request
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if side == 'buy' else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            client_order_id=client_order_id
        )

        # Submit order
        alpaca_order = self.client.submit_order(order_data)

        # Convert to our Order schema
        order = Order(
            order_id=alpaca_order.id,
            symbol=alpaca_order.symbol,
            side=side,
            quantity=quantity,
            order_type='market',
            status='submitted',
            filled_quantity=0,
            created_at=alpaca_order.created_at,
            updated_at=alpaca_order.updated_at
        )

        return order

    def submit_limit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        limit_price: Decimal,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Submit limit order"""

        if client_order_id is None:
            client_order_id = str(uuid.uuid4())

        order_data = LimitOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if side == 'buy' else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=float(limit_price),
            client_order_id=client_order_id
        )

        alpaca_order = self.client.submit_order(order_data)

        order = Order(
            order_id=alpaca_order.id,
            symbol=alpaca_order.symbol,
            side=side,
            quantity=quantity,
            order_type='limit',
            limit_price=limit_price,
            status='submitted',
            filled_quantity=0,
            created_at=alpaca_order.created_at,
            updated_at=alpaca_order.updated_at
        )

        return order

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        try:
            self.client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            print(f"Error canceling order {order_id}: {e}")
            return False

    def get_order_status(self, order_id: str) -> str:
        """Get current order status"""
        order = self.client.get_order_by_id(order_id)
        return order.status

    def get_account(self):
        """Get account information"""
        return self.client.get_account()

    def get_positions(self):
        """Get all current positions"""
        return self.client.get_all_positions()
```

---

## 9. Performance & Metrics

### 9.1 Performance Metrics Calculator

```python
# src/trading/analytics/metrics.py

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal

class PerformanceMetrics:
    """Calculate comprehensive performance metrics"""

    @staticmethod
    def calculate_metrics(
        equity_curve: pd.DataFrame,
        trades: pd.DataFrame,
        initial_capital: Decimal,
        risk_free_rate: float = 0.02
    ) -> Dict:
        """Calculate all performance metrics"""

        # Convert equity to returns
        equity_series = equity_curve['equity']
        returns = equity_series.pct_change().dropna()

        # Basic metrics
        total_return = (equity_series.iloc[-1] / float(initial_capital)) - 1
        cagr = PerformanceMetrics._calculate_cagr(
            float(initial_capital),
            equity_series.iloc[-1],
            len(equity_series) / 252
        )

        # Risk metrics
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = PerformanceMetrics._calculate_sharpe(
            returns,
            risk_free_rate
        )
        sortino_ratio = PerformanceMetrics._calculate_sortino(
            returns,
            risk_free_rate
        )

        # Drawdown analysis
        max_dd, max_dd_duration = PerformanceMetrics._calculate_drawdown_metrics(
            equity_series
        )

        # Trade analysis
        win_rate = PerformanceMetrics._calculate_win_rate(trades)
        avg_win, avg_loss = PerformanceMetrics._calculate_win_loss_avg(trades)
        profit_factor = PerformanceMetrics._calculate_profit_factor(trades)

        return {
            # Returns
            'total_return': float(total_return),
            'cagr': float(cagr),
            'volatility': float(volatility),

            # Risk-adjusted returns
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(cagr / abs(max_dd)) if max_dd != 0 else 0,

            # Drawdown
            'max_drawdown': float(max_dd),
            'max_drawdown_duration': int(max_dd_duration),

            # Trading stats
            'num_trades': len(trades),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),

            # Equity stats
            'final_equity': float(equity_series.iloc[-1]),
            'peak_equity': float(equity_series.max()),
        }

    @staticmethod
    def _calculate_cagr(
        start_value: float,
        end_value: float,
        years: float
    ) -> float:
        """Calculate Compound Annual Growth Rate"""
        if years == 0 or start_value == 0:
            return 0.0
        return (end_value / start_value) ** (1 / years) - 1

    @staticmethod
    def _calculate_sharpe(
        returns: pd.Series,
        risk_free_rate: float
    ) -> float:
        """Calculate Sharpe Ratio"""
        if returns.std() == 0:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)
        return (excess_returns.mean() / returns.std()) * np.sqrt(252)

    @staticmethod
    def _calculate_sortino(
        returns: pd.Series,
        risk_free_rate: float
    ) -> float:
        """Calculate Sortino Ratio (uses downside deviation)"""
        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        return (excess_returns.mean() / downside_returns.std()) * np.sqrt(252)

    @staticmethod
    def _calculate_drawdown_metrics(equity: pd.Series):
        """Calculate maximum drawdown and duration"""
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max

        max_dd = drawdown.min()

        # Calculate drawdown duration
        is_drawdown = drawdown < 0
        drawdown_periods = is_drawdown.astype(int).groupby(
            (is_drawdown != is_drawdown.shift()).cumsum()
        ).sum()

        max_dd_duration = drawdown_periods.max() if len(drawdown_periods) > 0 else 0

        return max_dd, max_dd_duration

    @staticmethod
    def _calculate_win_rate(trades: pd.DataFrame) -> float:
        """Calculate percentage of winning trades"""
        if len(trades) == 0:
            return 0.0

        # Assuming trades have 'pnl' column
        wins = (trades['pnl'] > 0).sum() if 'pnl' in trades.columns else 0
        return wins / len(trades)

    @staticmethod
    def _calculate_win_loss_avg(trades: pd.DataFrame):
        """Calculate average win and average loss"""
        if 'pnl' not in trades.columns or len(trades) == 0:
            return 0.0, 0.0

        wins = trades[trades['pnl'] > 0]['pnl']
        losses = trades[trades['pnl'] < 0]['pnl']

        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0

        return avg_win, avg_loss

    @staticmethod
    def _calculate_profit_factor(trades: pd.DataFrame) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        if 'pnl' not in trades.columns or len(trades) == 0:
            return 0.0

        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss
```

---

## 10. Deployment & Configuration

### 10.1 Configuration Management

```python
# src/trading/utils/config.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from decimal import Decimal
import yaml
from pathlib import Path

class DataConfig(BaseModel):
    """Data source configuration"""
    provider: str = "alpaca"
    api_key: str
    secret_key: str
    paper: bool = True
    symbols: List[str]
    timeframe: str = "1D"
    storage_path: str = "./data/historical"

class BacktestConfig(BaseModel):
    """Backtesting configuration"""
    initial_capital: Decimal = Decimal("100000")
    commission_pct: Decimal = Decimal("0.001")
    slippage_pct: Decimal = Decimal("0.0005")
    max_position_size: Decimal = Decimal("0.25")
    stop_loss_pct: Optional[Decimal] = None
    take_profit_pct: Optional[Decimal] = None

class MonteCarloConfig(BaseModel):
    """Monte Carlo configuration"""
    num_simulations: int = 1000
    num_periods: int = 252
    confidence_levels: List[float] = [0.90, 0.95, 0.99]
    random_seed: Optional[int] = None

class StrategyConfig(BaseModel):
    """Strategy configuration"""
    name: str
    parameters: Dict = {}

class TradingConfig(BaseModel):
    """Main configuration"""
    data: DataConfig
    backtest: BacktestConfig
    monte_carlo: MonteCarloConfig
    strategy: StrategyConfig

def load_config(config_path: str) -> TradingConfig:
    """Load configuration from YAML file"""
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r') as f:
        config_dict = yaml.safe_load(f)

    return TradingConfig(**config_dict)
```

### 10.2 Sample Configuration File

```yaml
# config/default.yaml

data:
  provider: "alpaca"
  api_key: "${ALPACA_API_KEY}"
  secret_key: "${ALPACA_SECRET_KEY}"
  paper: true
  symbols:
    - "SPY"
    - "QQQ"
    - "AAPL"
  timeframe: "1D"
  storage_path: "./data/historical"

backtest:
  initial_capital: 100000
  commission_pct: 0.001
  slippage_pct: 0.0005
  max_position_size: 0.25
  stop_loss_pct: null
  take_profit_pct: null

monte_carlo:
  num_simulations: 1000
  num_periods: 252
  confidence_levels: [0.90, 0.95, 0.99]
  random_seed: 42

strategy:
  name: "SMA_Crossover"
  parameters:
    fast_period: 50
    slow_period: 200
```

### 10.3 Project Setup with uv

```toml
# pyproject.toml

[project]
name = "algo-trading"
version = "0.1.0"
description = "Algorithmic Trading Platform with Backtesting and Monte Carlo"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "alpaca-py>=0.21.0",
    "plotly>=5.18.0",
    "scipy>=1.12.0",
    "pydantic>=2.6.0",
    "pyyaml>=6.0.1",
    "loguru>=0.7.2",
    "pyarrow>=15.0.0",
    "python-dotenv>=1.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.1.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]
backtest = [
    "backtrader>=1.9.78.123",
    "vectorbt>=0.26.0",
]
ml = [
    "scikit-learn>=1.4.0",
    "xgboost>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
```

### 10.4 Installation Commands

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project
uv init algo-trading
cd algo-trading

# Install dependencies
uv sync

# Install with optional dependencies
uv sync --extra dev --extra backtest --extra ml

# Run tests
uv run pytest

# Format code
uv run black src/

# Type checking
uv run mypy src/
```

---

## Summary: Key Design Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Package Manager** | uv | 10-100x faster than pip, deterministic builds |
| **Backtesting** | Event-driven engine | Realistic simulation, no lookahead bias |
| **Monte Carlo** | Multiple models (GBM, Bootstrap, Jump Diffusion) | Capture different market regimes |
| **Data Storage** | Parquet with partitioning | Efficient columnar storage, fast queries |
| **Config** | Pydantic + YAML | Type safety, validation, human-readable |
| **Numerical** | Decimal for money, float for calculations | Avoid floating-point precision errors |
| **Testing** | Pytest with fixtures | Comprehensive unit and integration tests |
| **API Client** | Official alpaca-py | Maintained, type-safe, async support |

---

## Next Steps: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- Set up project structure with uv
- Implement data layer (providers, storage, normalization)
- Create Pydantic schemas
- Basic unit tests

### Phase 2: Backtesting (Week 3-4)
- Implement backtesting engine
- Portfolio tracker
- Fill simulator with slippage
- Example strategies (SMA, Mean Reversion)

### Phase 3: Monte Carlo (Week 5-6)
- Monte Carlo simulator
- Path generation models (GBM, Jump Diffusion)
- Risk metrics (VaR, CVaR)
- Confidence interval analysis

### Phase 4: Integration (Week 7-8)
- Alpaca API integration
- Live trading executor
- Order management
- Performance analytics

### Phase 5: Visualization & Reporting (Week 9-10)
- Plotly charts (equity curve, drawdown, returns)
- Interactive dashboard
- PDF/HTML report generation
- Strategy comparison tools

### Phase 6: Testing & Documentation (Week 11-12)
- Comprehensive test suite
- Integration tests with mock API
- User documentation
- Example notebooks

---

**Document Status:** ✅ Complete - Ready for Implementation
**Last Updated:** 2025-10-14
**Next Review:** After Phase 1 completion

**Coordination Hooks:**
```bash
npx claude-flow@alpha hooks post-edit --file "docs/architecture/python-trading-architecture.md" --memory-key "hive/architect/python-platform"
npx claude-flow@alpha hooks post-task --task-id "task-1760486032169-cqbd429wh"
npx claude-flow@alpha hooks session-end --export-metrics true
```
