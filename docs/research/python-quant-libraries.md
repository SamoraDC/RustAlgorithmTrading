# Python Quantitative Finance Libraries (2025)

## Core Scientific Computing Stack

### NumPy
**Purpose**: Foundation for numerical computing

**Key Features**:
- N-dimensional arrays and matrices
- Fast vectorized operations
- Linear algebra functions
- Random number generation
- Broadcasting capabilities

**Installation**:
```bash
uv pip install numpy
```

**Use Cases**:
- Portfolio calculations (returns, covariance)
- Monte Carlo simulations
- Technical indicator computation
- Matrix operations for optimization

### Pandas
**Purpose**: Data manipulation and analysis

**Key Features**:
- DataFrame structure optimized for time series
- Built-in financial functions
- Easy data alignment and merging
- Powerful grouping and aggregation
- Time series resampling

**Installation**:
```bash
uv pip install pandas
```

**Use Cases**:
- Price data management
- OHLCV data processing
- Portfolio rebalancing calculations
- Performance metric computation
- Data cleaning and transformation

### SciPy
**Purpose**: Scientific computing and optimization

**Key Features**:
- Optimization algorithms (minimize, least squares)
- Statistical functions
- Interpolation and integration
- Linear algebra (advanced)
- Signal processing

**Installation**:
```bash
uv pip install scipy
```

**Use Cases**:
- Portfolio optimization (efficient frontier)
- Curve fitting for indicators
- Statistical analysis
- Numerical optimization

## Backtesting Frameworks

### 1. Backtesting.py
**Description**: Lightweight, fast backtesting framework built on Pandas and NumPy

**Strengths**:
- Simple, intuitive API
- Fast execution (vectorized)
- Beautiful Bokeh visualizations
- Minimal code required
- Interactive charts

**Limitations**:
- Less suitable for complex multi-asset strategies
- Limited live trading integration
- Event-driven features less developed

**Installation**:
```bash
uv pip install backtesting
```

**Best For**:
- Quick strategy prototyping
- Single-asset strategies
- Educational purposes
- Rapid iteration

### 2. Backtrader
**Description**: Feature-rich, event-driven backtesting framework

**Strengths**:
- Comprehensive feature set
- Live trading support (IB, Alpaca, etc.)
- Complex order types
- Multiple data feeds
- Extensive documentation
- Large community

**Limitations**:
- Steeper learning curve
- More verbose code
- Slower than vectorized alternatives

**Installation**:
```bash
uv pip install backtrader
```

**Best For**:
- Complex multi-strategy systems
- Live trading integration
- Professional-grade development
- Multi-asset portfolios

### 3. Zipline
**Description**: Institutional-grade backtesting library (used by Quantopian)

**Strengths**:
- Realistic market simulation
- Built-in pipeline for factor analysis
- Handles corporate actions
- Professional-grade architecture
- Integration with research ecosystem

**Limitations**:
- More complex setup
- Requires specific data format
- Less actively maintained
- Heavier dependencies

**Installation**:
```bash
uv pip install zipline-reloaded  # Maintained fork
```

**Best For**:
- Factor-based strategies
- Academic research
- Institutional-quality testing
- Long-term projects

### 4. vectorbt
**Description**: High-performance vectorized backtesting

**Strengths**:
- Extremely fast (NumPy vectorization)
- Portfolio optimization built-in
- Advanced analytics
- Parallel processing
- Memory efficient

**Limitations**:
- Newer library (smaller community)
- Complex API for beginners
- Less documentation

**Installation**:
```bash
uv pip install vectorbt
```

**Best For**:
- Large-scale parameter optimization
- High-frequency strategies
- Portfolio analysis
- Performance-critical applications

## Market Data Libraries

### 1. Alpaca-py
**Description**: Official Python SDK for Alpaca Markets

**Features**:
- Trading API integration
- Historical data (7+ years)
- Real-time WebSocket streaming
- Paper and live trading
- Options trading support

**Installation**:
```bash
uv pip install alpaca-py
```

**Use Cases**:
- Alpaca API integration
- Live trading execution
- Real-time data streaming
- Historical data for backtesting

### 2. yfinance
**Description**: Yahoo Finance data downloader

**Strengths**:
- Free, no API key required
- Easy to use
- Multiple assets and markets
- Historical and real-time data

**Limitations**:
- **HAS SURVIVORSHIP BIAS** - not suitable for serious backtesting
- Rate limiting
- Less reliable for production
- No official support

**Installation**:
```bash
uv pip install yfinance
```

**Best For**:
- Prototyping and learning
- Quick data exploration
- Personal projects
- **NOT recommended for production backtesting**

### 3. Databento
**Description**: Professional market data API

**Features**:
- High-quality, clean data
- Survivorship-bias-free datasets
- Tick-level granularity
- Multiple exchanges
- Historical and real-time

**Installation**:
```bash
uv pip install databento
```

**Best For**:
- Professional backtesting
- Accurate historical data
- High-frequency strategies

### 4. pandas-datareader
**Description**: Data access layer for pandas

**Features**:
- Multiple data sources
- Unified interface
- Economic data (FRED, World Bank)
- Stock data from various providers

**Installation**:
```bash
uv pip install pandas-datareader
```

## Portfolio Optimization

### PyPortfolioOpt (pypfopt)
**Description**: Portfolio optimization and allocation

**Features**:
- Mean-variance optimization
- Black-Litterman model
- Hierarchical Risk Parity (HRP)
- Critical Line Algorithm (CLA)
- Multiple objective functions
- Practical constraints (long-only, sector limits)

**Installation**:
```bash
uv pip install PyPortfolioOpt
# Alternative package name
uv pip install pypfopt
```

**Example Use**:
```python
from pypfopt import EfficientFrontier, risk_models, expected_returns

# Calculate expected returns and covariance
mu = expected_returns.mean_historical_return(prices)
S = risk_models.sample_cov(prices)

# Optimize for maximum Sharpe ratio
ef = EfficientFrontier(mu, S)
weights = ef.max_sharpe()
cleaned_weights = ef.clean_weights()
```

## Performance Analytics

### 1. QuantStats
**Description**: Portfolio performance metrics and reporting

**Features**:
- Comprehensive performance metrics
- Risk-adjusted returns
- Drawdown analysis
- HTML reports with charts
- Sharpe, Sortino, Calmar ratios
- Benchmark comparison

**Installation**:
```bash
uv pip install quantstats
```

**Example Use**:
```python
import quantstats as qs

# Analyze returns
qs.reports.html(returns, 'SPY', output='report.html')
print(qs.stats.sharpe(returns))
print(qs.stats.max_drawdown(returns))
```

### 2. Empyrical
**Description**: Financial risk metrics (from Quantopian)

**Features**:
- Risk metrics calculation
- Return analysis
- Drawdown statistics
- Common financial ratios
- Simple, focused API

**Installation**:
```bash
uv pip install empyrical
```

**Example Use**:
```python
import empyrical as ep

sharpe = ep.sharpe_ratio(returns)
max_dd = ep.max_drawdown(returns)
sortino = ep.sortino_ratio(returns)
```

## Technical Analysis

### 1. TA-Lib
**Description**: Technical analysis library (C library with Python wrapper)

**Features**:
- 150+ technical indicators
- Pattern recognition
- Fast C implementation
- Industry standard

**Installation**:
```bash
# Requires compilation, platform-dependent
# On Ubuntu/Debian:
# sudo apt-get install ta-lib
uv pip install TA-Lib

# Alternative: ta-lib without C dependency
uv pip install ta
```

### 2. pandas-ta
**Description**: Technical analysis indicators for pandas

**Features**:
- 130+ indicators
- Pure Python (no compilation)
- Pandas integration
- Easy to extend

**Installation**:
```bash
uv pip install pandas-ta
```

## Visualization

### 1. Matplotlib
**Description**: Foundational plotting library

**Installation**:
```bash
uv pip install matplotlib
```

**Use Cases**:
- Price charts
- Performance graphs
- Custom visualizations

### 2. Plotly
**Description**: Interactive plotting library

**Installation**:
```bash
uv pip install plotly
```

**Use Cases**:
- Interactive dashboards
- Candlestick charts
- 3D visualizations

### 3. Bokeh
**Description**: Interactive visualization (used by backtesting.py)

**Installation**:
```bash
uv pip install bokeh
```

**Use Cases**:
- Backtesting charts
- Real-time dashboards
- Interactive exploration

## Machine Learning for Finance

### 1. scikit-learn
**Description**: Machine learning library

**Installation**:
```bash
uv pip install scikit-learn
```

**Use Cases**:
- Feature engineering
- Classification/regression
- Clustering
- Dimensionality reduction

### 2. XGBoost
**Description**: Gradient boosting framework

**Installation**:
```bash
uv pip install xgboost
```

**Use Cases**:
- Price prediction
- Feature importance
- Classification tasks

## Utilities and Infrastructure

### 1. python-dotenv
**Description**: Environment variable management

**Installation**:
```bash
uv pip install python-dotenv
```

**Use Cases**:
- Secure API key storage
- Configuration management
- Environment separation

### 2. Schedule
**Description**: Job scheduling

**Installation**:
```bash
uv pip install schedule
```

**Use Cases**:
- Daily rebalancing
- Scheduled data fetching
- Automated trading jobs

### 3. Loguru
**Description**: Modern logging

**Installation**:
```bash
uv pip install loguru
```

**Use Cases**:
- Trade logging
- Error tracking
- Performance monitoring

## Complete Installation Script

```bash
#!/bin/bash
# Install complete quantitative trading environment

# Core scientific computing
uv pip install numpy pandas scipy matplotlib

# Backtesting frameworks
uv pip install backtesting backtrader vectorbt
uv pip install zipline-reloaded  # Maintained Zipline fork

# Market data
uv pip install alpaca-py yfinance pandas-datareader databento

# Portfolio optimization
uv pip install PyPortfolioOpt

# Performance analytics
uv pip install quantstats empyrical

# Technical analysis
uv pip install pandas-ta  # Pure Python, easier install
# uv pip install TA-Lib  # Optional: faster but requires compilation

# Visualization
uv pip install plotly bokeh

# Machine learning
uv pip install scikit-learn xgboost

# Utilities
uv pip install python-dotenv loguru schedule

# Jupyter for analysis
uv pip install jupyter ipykernel
```

## Recommended Minimal Stack

For starting a new project, minimum recommended installation:

```bash
# Essential stack
uv pip install numpy pandas scipy
uv pip install backtesting  # or backtrader
uv pip install alpaca-py
uv pip install PyPortfolioOpt
uv pip install quantstats
uv pip install pandas-ta
uv pip install matplotlib
uv pip install python-dotenv
```

## Library Comparison Matrix

| Library | Speed | Ease of Use | Features | Community | Best For |
|---------|-------|-------------|----------|-----------|----------|
| backtesting.py | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Quick prototyping |
| Backtrader | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Complex strategies |
| Zipline | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Institutional use |
| vectorbt | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | Optimization |
| PyPortfolioOpt | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Portfolio optimization |

## Best Practices

1. **Use virtual environments**: Isolate project dependencies
2. **Pin versions**: Lock dependency versions in production
3. **Update regularly**: Keep libraries current for bug fixes
4. **Read documentation**: Each library has specific patterns
5. **Start simple**: Begin with minimal stack, add as needed
6. **Benchmark**: Test performance with your data size
7. **Use uv for speed**: Faster installation than pip

## Common Pitfalls

1. **Using yfinance for production**: Has survivorship bias
2. **Not pinning versions**: Breaking changes in updates
3. **Mixing incompatible versions**: Pandas/NumPy version conflicts
4. **Over-installing**: Too many unused dependencies
5. **Ignoring data quality**: Library quality ≠ data quality
6. **Not testing locally**: Test before deploying to production

## Resources

- PyPI: https://pypi.org/ (official package index)
- Awesome Quant: https://github.com/wilsonfreitas/awesome-quant
- QuantStart: https://www.quantstart.com/
- QuantConnect: https://www.quantconnect.com/
