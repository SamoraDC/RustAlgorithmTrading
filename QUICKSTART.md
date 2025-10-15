# 🚀 Quick Start Guide - Python-Rust Algorithmic Trading System

**Get started with backtesting in Python or live trading in Rust!**

---

## Choose Your Path

This system offers three workflows:

1. **🐍 Python Backtesting** (Start Here) - Test strategies on historical data
2. **🦀 Rust Live Trading** (Advanced) - High-performance paper/live trading
3. **⚡ Full System** (Production) - Python backtesting + Rust execution

**New to algorithmic trading?** → Start with Option 1 (Python Backtesting)
**Experienced trader?** → Jump to Option 3 (Full System)

---

## Prerequisites

### For Python Backtesting (Option 1)
✅ **Python 3.11+**:
```bash
python --version  # Should show 3.11 or higher
```

✅ **uv (recommended) or pip**:
```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# OR use pip (slower)
pip install --upgrade pip
```

### For Rust Live Trading (Options 2 & 3)
✅ **Rust 1.70+**: Install from https://rustup.rs/
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

✅ **Alpaca Account**: Free paper trading at https://alpaca.markets
- Sign up for paper trading account
- Get API Key ID and Secret Key

### Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/RustAlgorithmTrading.git
cd RustAlgorithmTrading
```

---

## Option 1: 🐍 Python Backtesting (Start Here)

**Perfect for**: Strategy development, testing, and optimization

### Step 1: Install Python Dependencies
```bash
# Using uv (recommended - fast!)
uv pip install -e .

# OR using pip (slower)
pip install -e .
```

This installs:
- `vectorbt` - Backtesting framework
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `ta-lib` - Technical indicators
- Development tools (pytest, black, mypy)

### Step 2: Run Your First Backtest
```bash
# Simple moving average crossover strategy
python examples/simple_backtest.py
```

**Example Code** (`examples/simple_backtest.py`):
```python
import vectorbt as vbt
import pandas as pd

# Download historical data (S&P 500)
data = vbt.YFData.download("SPY", start="2023-01-01", end="2024-01-01")

# Simple moving average crossover
fast_ma = data.close.rolling(window=20).mean()
slow_ma = data.close.rolling(window=50).mean()

# Generate signals: buy when fast > slow, sell when fast < slow
entries = fast_ma > slow_ma
exits = fast_ma < slow_ma

# Run backtest
portfolio = vbt.Portfolio.from_signals(
    data.close,
    entries,
    exits,
    init_cash=10000,
    fees=0.001  # 0.1% per trade
)

# Display results
print(portfolio.stats())
print(f"Total Return: {portfolio.total_return():.2%}")
print(f"Sharpe Ratio: {portfolio.sharpe_ratio():.2f}")
print(f"Max Drawdown: {portfolio.max_drawdown():.2%}")
```

### Step 3: Analyze Results
```bash
# View detailed performance metrics
python -m python_trading.backtesting.analyze --results results/backtest_001.json

# Generate visual report
python -m python_trading.backtesting.visualize --results results/backtest_001.json
```

You'll see:
```
📊 Backtest Results Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Return:        32.45%
Annual Return:       28.12%
Sharpe Ratio:        1.82
Max Drawdown:       -12.34%
Win Rate:            58.3%
Total Trades:        47
Avg Trade Duration:  3.2 days
```

### Step 4: Optimize Strategy Parameters
```bash
# Grid search over parameter space
python examples/optimize_strategy.py
```

**Example Code** (`examples/optimize_strategy.py`):
```python
import vectorbt as vbt
import numpy as np

data = vbt.YFData.download("SPY", start="2023-01-01", end="2024-01-01")

# Test multiple moving average combinations
windows = vbt.combinations(
    fast=np.arange(5, 50, 5),   # Fast MA: 5, 10, 15, ..., 45
    slow=np.arange(20, 200, 10)  # Slow MA: 20, 30, 40, ..., 190
)

# Run all combinations in parallel
portfolio = vbt.Portfolio.from_signals(
    data.close,
    data.close.rolling(windows.fast).mean() > data.close.rolling(windows.slow).mean(),
    data.close.rolling(windows.fast).mean() < data.close.rolling(windows.slow).mean(),
    init_cash=10000
)

# Find best parameters
best_params = portfolio.sharpe_ratio().idxmax()
print(f"Best Fast MA: {best_params[0]}")
print(f"Best Slow MA: {best_params[1]}")
print(f"Best Sharpe: {portfolio.sharpe_ratio().max():.2f}")
```

### Next Steps (Python)
- Explore `examples/advanced_strategies/` for more complex strategies
- Read `docs/python/backtesting_guide.md` for detailed backtesting guide
- Try `examples/ml_features.py` to compute ML features
- Move to Option 3 to deploy your strategy in Rust

---

## Option 2: 🦀 Rust Live Trading (Advanced)

**Perfect for**: High-performance paper/live trading with low latency

### Step 1: Configure API Keys
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Alpaca keys
nano .env  # or use your favorite editor
```

Add your keys:
```bash
ALPACA_API_KEY=YOUR_KEY_ID_HERE
ALPACA_SECRET_KEY=YOUR_SECRET_KEY_HERE
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Step 2: Build the Project
```bash
cd rust/
cargo build --release
```

This will:
- Download and compile 292 dependencies
- Build all 5 crates (takes 5-10 minutes first time)
- Create optimized binaries in `target/release/`

### Step 3: Run Market Data Feed
```bash
# Start market data ingestion
./target/release/market-data --config ../config/dev/market-data.toml
```

**Example Config** (`config/dev/market-data.toml`):
```toml
[websocket]
url = "wss://stream.data.alpaca.markets/v2/iex"
symbols = ["SPY", "AAPL", "QQQ", "TSLA"]
reconnect_interval_ms = 1000

[orderbook]
depth = 10  # Track top 10 levels
max_symbols = 100

[metrics]
enabled = true
port = 9090
```

You should see:
```
✅ Connected to Alpaca WebSocket
✅ Subscribed to: SPY, AAPL, QQQ, TSLA
📊 Receiving market data...
[2024-01-15T10:30:00Z] SPY: $456.78 (Bid: $456.75, Ask: $456.80)
[2024-01-15T10:30:01Z] AAPL: $178.23 (Bid: $178.20, Ask: $178.25)
```

### Step 4: Verify It Works
Open another terminal:
```bash
# Check metrics endpoint
curl http://localhost:9090/metrics | grep market_data
```

You should see:
```
market_data_messages_received_total{symbol="SPY"} 1234
market_data_latency_seconds{symbol="SPY",quantile="0.99"} 0.000045
market_data_orderbook_depth{symbol="SPY"} 10
```

### Step 5: Test Paper Trading
```bash
# Terminal 1: Market Data
./target/release/market-data

# Terminal 2: Risk Manager
./target/release/risk-manager --config ../config/dev/risk-manager.toml

# Terminal 3: Execution Engine
./target/release/execution-engine --config ../config/dev/execution-engine.toml
```

**Example Trade**:
```bash
# Send test order via HTTP API
curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SPY",
    "side": "buy",
    "quantity": 10,
    "order_type": "limit",
    "limit_price": 456.50
  }'
```

Response:
```json
{
  "order_id": "abc123",
  "status": "accepted",
  "symbol": "SPY",
  "side": "buy",
  "quantity": 10,
  "filled_quantity": 0,
  "avg_fill_price": null,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Next Steps (Rust)
- Monitor performance with Grafana dashboards
- Tune risk parameters in `config/dev/risk-manager.toml`
- Deploy with Docker Compose for production
- Integrate Python strategies via PyO3 (Option 3)

---

## Option 3: ⚡ Full System (Production)

**Perfect for**: End-to-end workflow from backtesting to live trading

### Step 1: Python Strategy Development
```bash
# Develop and backtest strategy in Python
python examples/advanced_strategies/mean_reversion.py

# Optimize parameters
python examples/optimize_strategy.py --strategy mean_reversion
```

### Step 2: Compute Features for Rust
```bash
# Use Python to compute ML features
python -m python_trading.features.compute --output rust/data/features.parquet
```

**Example Code** (`python_trading/features/compute.py`):
```python
import pandas as pd
import talib

def compute_features(data: pd.DataFrame) -> pd.DataFrame:
    """Compute technical indicators for Rust execution engine."""
    features = pd.DataFrame(index=data.index)

    # Moving averages
    features['sma_20'] = talib.SMA(data['close'], timeperiod=20)
    features['sma_50'] = talib.SMA(data['close'], timeperiod=50)
    features['ema_12'] = talib.EMA(data['close'], timeperiod=12)

    # Momentum indicators
    features['rsi'] = talib.RSI(data['close'], timeperiod=14)
    features['macd'], features['macd_signal'], _ = talib.MACD(data['close'])

    # Volatility
    features['bbands_upper'], features['bbands_middle'], features['bbands_lower'] = \
        talib.BBANDS(data['close'], timeperiod=20)
    features['atr'] = talib.ATR(data['high'], data['low'], data['close'], timeperiod=14)

    # Volume indicators
    features['obv'] = talib.OBV(data['close'], data['volume'])
    features['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)

    return features.dropna()

# Save for Rust
features = compute_features(market_data)
features.to_parquet('rust/data/features.parquet')
```

### Step 3: PyO3 Integration
```bash
# Build Rust with Python bindings
cd rust/signal-bridge
cargo build --release --features pyo3
```

**Example Code** (`rust/signal-bridge/src/lib.rs`):
```rust
use pyo3::prelude::*;

#[pyfunction]
fn compute_signal(features: Vec<f64>) -> PyResult<f64> {
    // Call Python-computed features from Rust
    let signal = if features[0] > features[1] { // SMA crossover
        1.0  // Buy signal
    } else if features[0] < features[1] {
        -1.0  // Sell signal
    } else {
        0.0  // No signal
    };
    Ok(signal)
}

#[pymodule]
fn signal_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_signal, m)?)?;
    Ok(())
}
```

### Step 4: Run Full System
```bash
# Option A: Docker Compose (Recommended)
docker-compose up -d

# Option B: Manual
# Terminal 1: Market Data
./rust/target/release/market-data

# Terminal 2: Python Feature Server
python -m python_trading.features.server --port 8081

# Terminal 3: Risk Manager
./rust/target/release/risk-manager

# Terminal 4: Execution Engine (with PyO3)
./rust/target/release/execution-engine --features-url http://localhost:8081
```

### Step 5: Monitor End-to-End Performance
```bash
# Grafana dashboards
open http://localhost:3000

# View real-time metrics
curl http://localhost:9090/metrics | grep -E "(python|rust)_latency"
```

**Example Output**:
```
python_feature_computation_seconds{quantile="0.99"} 0.002  # 2ms
rust_order_execution_seconds{quantile="0.99"} 0.000045     # 45μs
end_to_end_latency_seconds{quantile="0.99"} 0.004          # 4ms
```

### Next Steps (Full System)
- Monitor P&L in Grafana
- Scale feature computation with `python_trading.features.distributed`
- Optimize Rust execution with `cargo bench`
- Deploy to production with Kubernetes

---

## Docker Deployment

### Quick Start with Docker Compose
```bash
# Start all services (market data, risk, execution, monitoring)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

This starts:
- Market data feed (WebSocket + order book)
- Risk manager (position limits, loss limits)
- Execution engine (order routing)
- Prometheus (metrics collection)
- Grafana (dashboards and visualization)

### Access Services
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Execution API**: http://localhost:8080
- **Metrics**: http://localhost:9090/metrics

---

## Common Issues & Troubleshooting

### Python Issues

**Import Errors**:
```bash
# Reinstall dependencies
uv pip install -e . --force-reinstall

# OR with pip
pip install -e . --force-reinstall
```

**TA-Lib Installation Failed**:
```bash
# Ubuntu/Debian
sudo apt install build-essential ta-lib
pip install TA-Lib

# macOS
brew install ta-lib
pip install TA-Lib

# Windows (use pre-built wheel)
pip install TA-Lib --find-links https://github.com/cgohlke/talib-build/releases
```

### Rust Issues

**Build Errors**:
```bash
# Update Rust toolchain
rustup update

# Clean and rebuild
cd rust/
cargo clean
cargo build --release
```

**Missing System Dependencies**:
```bash
# Ubuntu/Debian
sudo apt install build-essential pkg-config libssl-dev

# macOS
brew install openssl pkg-config

# Windows
# Install Visual Studio Build Tools from:
# https://visualstudio.microsoft.com/downloads/
```

**API Connection Errors**:
```bash
# Test Alpaca API keys
curl -u "$ALPACA_API_KEY:$ALPACA_SECRET_KEY" \
  https://paper-api.alpaca.markets/v2/account

# Should return account info (not 401 Unauthorized)
```

---

## Development Workflow

### Python Development

**Running Tests**:
```bash
# All tests
pytest

# Specific test file
pytest tests/test_backtesting.py

# With coverage
pytest --cov=python_trading --cov-report=html
```

**Code Formatting**:
```bash
# Format code with black
black python_trading/ tests/

# Sort imports with isort
isort python_trading/ tests/

# Type checking with mypy
mypy python_trading/
```

**Linting**:
```bash
# Run flake8
flake8 python_trading/ tests/

# Run pylint
pylint python_trading/
```

### Rust Development

**Running Tests**:
```bash
# All tests
cd rust/
cargo test --workspace

# Specific crate
cargo test -p market-data

# With output
cargo test -- --nocapture
```

**Code Formatting**:
```bash
# Format all code
cargo fmt --all

# Check without formatting
cargo fmt --all -- --check
```

**Linting**:
```bash
# Run clippy (strict mode)
cargo clippy --all -- -D warnings
```

**Benchmarks**:
```bash
# Run benchmarks
cargo bench --workspace

# Specific benchmark
cargo bench -p execution-engine
```

---

## Project Structure (Quick Reference)

```
RustAlgorithmTrading/
├── README.md              # Project overview
├── QUICKSTART.md          # This file - getting started guide
├── ARCHITECTURE.md        # System design and architecture
├── CONTRIBUTING.md        # Contribution guidelines
│
├── python_trading/        # 🐍 Python backtesting & ML
│   ├── backtesting/       # Backtesting engine (vectorbt)
│   ├── features/          # Feature engineering (TA-Lib)
│   ├── strategies/        # Trading strategies
│   ├── optimization/      # Parameter optimization
│   └── analysis/          # Performance analysis
│
├── rust/                  # 🦀 Rust live trading
│   ├── market-data/       # WebSocket + order book
│   ├── risk-manager/      # Risk controls & limits
│   ├── execution-engine/  # Order routing & execution
│   ├── signal-bridge/     # PyO3 Python-Rust bridge
│   └── common/            # Shared types & utilities
│
├── examples/              # Example scripts
│   ├── simple_backtest.py         # Basic backtesting
│   ├── optimize_strategy.py       # Parameter optimization
│   ├── ml_features.py             # ML feature computation
│   └── advanced_strategies/       # Complex strategies
│
├── tests/                 # Test suites
│   ├── python/            # Python unit & integration tests
│   └── rust/              # Rust unit & integration tests
│
├── config/                # Configuration files
│   ├── dev/               # Development configs
│   ├── prod/              # Production configs
│   └── backtest/          # Backtesting configs
│
├── docs/                  # Comprehensive documentation
│   ├── python/            # Python guides
│   ├── rust/              # Rust guides
│   ├── setup/             # Setup & deployment
│   ├── api/               # API documentation
│   └── architecture/      # Design documents
│
└── docker/                # Docker deployment
    └── docker-compose.yml # Multi-container orchestration
```

---

## Key Commands Cheat Sheet

### Python Backtesting
```bash
# Install dependencies
uv pip install -e .                                    # Fast install with uv
pip install -e .                                       # Standard install

# Run backtest
python examples/simple_backtest.py                     # Basic example
python examples/optimize_strategy.py                   # Parameter optimization
python -m python_trading.backtesting.run --config cfg  # Advanced backtest

# Analysis & visualization
python -m python_trading.backtesting.analyze           # Performance metrics
python -m python_trading.backtesting.visualize         # Charts and plots

# Testing
pytest                                                 # Run all Python tests
pytest tests/test_backtesting.py                       # Specific test file
pytest --cov=python_trading                            # With coverage
```

### Rust Live Trading
```bash
# Build
cd rust/
cargo build --release                                  # Production build
cargo build                                            # Debug build

# Run services
./target/release/market-data                           # Market data feed
./target/release/risk-manager                          # Risk management
./target/release/execution-engine                      # Order execution

# Testing
cargo test --workspace                                 # All tests
cargo test -p market-data                              # Specific crate
cargo bench --workspace                                # Benchmarks

# Code quality
cargo fmt --all                                        # Format code
cargo clippy --all -- -D warnings                      # Linting
```

### Docker Deployment
```bash
# Start all services
docker-compose up -d                                   # Detached mode
docker-compose up                                      # Foreground (see logs)

# Manage services
docker-compose down                                    # Stop all services
docker-compose logs -f market-data                     # View service logs
docker-compose restart execution-engine                # Restart service

# Build images
docker-compose build                                   # Build all images
docker-compose build --no-cache                        # Clean rebuild
```

### Data Management
```bash
# Python: Download historical data
python -m python_trading.data.download \
  --symbol SPY --start 2023-01-01 --end 2024-01-01

# Python: Compute ML features
python -m python_trading.features.compute \
  --input data/raw/SPY.csv --output data/features/SPY.parquet

# Rust: Verify market data
curl http://localhost:9090/metrics | grep market_data
```

---

## Performance Targets & Benchmarks

### Python Backtesting Performance
| Metric | Target | Notes |
|--------|--------|-------|
| Backtest Speed | >10k bars/s | vectorbt vectorized operations |
| Parameter Grid Search | <5 min for 100 combinations | Parallel optimization |
| Feature Computation | >1M bars/min | TA-Lib native C implementation |

### Rust Live Trading Performance
| Metric | Target | Current |
|--------|--------|---------|
| End-to-End Latency | <5ms | TBD - to be measured |
| Order Book Update | <10μs | TBD - to be measured |
| Risk Check | <50μs | TBD - to be measured |
| Market Data Throughput | 10k msg/s | TBD - to be measured |
| Memory Usage (per service) | <500MB | TBD - to be measured |

### Python-Rust Integration
| Metric | Target | Notes |
|--------|--------|-------|
| PyO3 Feature Call | <100μs | Python feature → Rust signal |
| Feature Server Latency | <2ms | HTTP API overhead |
| Full Pipeline (P99) | <4ms | Feature compute + execution |

---

## Monitoring & Observability

### Metrics (Prometheus)
```bash
# View all metrics
curl http://localhost:9090/metrics

# Query specific metric (Python)
curl 'http://localhost:9090/api/v1/query?query=python_backtest_duration_seconds'

# Query specific metric (Rust)
curl 'http://localhost:9090/api/v1/query?query=market_data_latency_seconds'
```

### Dashboards (Grafana)
1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Navigate to "Trading System" dashboard
4. View real-time metrics:
   - **Python**: Backtest performance, optimization progress
   - **Rust**: Market data latency, order book depth, order execution
   - **System**: P&L, risk metrics, position tracking

### Logs
```bash
# Python application logs
tail -f logs/python_trading.log

# Rust services (Docker)
docker-compose logs -f market-data
docker-compose logs -f risk-manager
docker-compose logs -f execution-engine

# Rust services (systemd)
journalctl -u market-data -f
```

---

## Help & Resources

### Documentation
📚 **Comprehensive Guides**: See `docs/` directory

**Getting Started**:
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/README.md` - Project overview
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/QUICKSTART.md` - This file (quick start)
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/ARCHITECTURE.md` - System architecture
- `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/CONTRIBUTING.md` - Contribution guide

**Python Backtesting**:
- `docs/python/backtesting_guide.md` - Comprehensive backtesting guide
- `docs/python/strategy_development.md` - Strategy development workflow
- `docs/python/feature_engineering.md` - ML feature engineering
- `docs/python/optimization.md` - Parameter optimization techniques

**Rust Live Trading**:
- `docs/rust/market_data.md` - Market data ingestion
- `docs/rust/risk_management.md` - Risk controls and limits
- `docs/rust/order_execution.md` - Order routing and execution
- `docs/rust/performance.md` - Performance optimization

**Integration**:
- `docs/integration/pyo3_guide.md` - Python-Rust integration with PyO3
- `docs/integration/deployment.md` - Full system deployment

**API Reference**:
- `docs/api/alpaca_integration.md` - Alpaca API integration
- `docs/api/rest_api.md` - Internal REST API reference
- `docs/api/websocket.md` - WebSocket API reference

### Community
🐛 **Issues**: Open issue on GitHub
💬 **Discussions**: GitHub Discussions
📧 **Email**: support@example.com

---

## What's Next?

### For Beginners (Python Path)
1. ✅ **You're here!** Read this quick start guide
2. 🐍 **Install Python**: `uv pip install -e .`
3. 📊 **Run your first backtest**: `python examples/simple_backtest.py`
4. 🎯 **Optimize strategy**: `python examples/optimize_strategy.py`
5. 📚 **Learn more**: Read `docs/python/backtesting_guide.md`

### For Advanced Users (Rust Path)
1. ✅ **Setup complete!** Configure Alpaca API keys
2. 🦀 **Build Rust**: `cd rust/ && cargo build --release`
3. 📡 **Start market data**: `./target/release/market-data`
4. 💹 **Test paper trading**: Send test orders via API
5. 📚 **Deep dive**: Read `ARCHITECTURE.md`

### For Production Deployment (Full System)
1. ✅ **Both systems ready!** Python + Rust installed
2. ⚡ **Integrate systems**: Build PyO3 bridge
3. 🐳 **Deploy with Docker**: `docker-compose up -d`
4. 📈 **Monitor performance**: Check Grafana dashboards
5. 🚀 **Go live**: Switch from paper to live trading (carefully!)

---

## Learning Path Recommendations

**Week 1: Python Backtesting**
- Day 1-2: Run example backtests and understand vectorbt
- Day 3-4: Develop your first custom strategy
- Day 5-6: Optimize strategy parameters
- Day 7: Analyze results and iterate

**Week 2: Rust Live Trading**
- Day 1-2: Set up Rust environment and understand architecture
- Day 3-4: Run market data feed and explore order book
- Day 5-6: Test paper trading with simple orders
- Day 7: Monitor performance metrics

**Week 3: Integration**
- Day 1-3: Build PyO3 bridge and test feature computation
- Day 4-5: Deploy full system with Docker
- Day 6-7: End-to-end testing and optimization

**Week 4: Production**
- Day 1-3: Final testing in paper trading environment
- Day 4-5: Deploy to production infrastructure
- Day 6-7: Monitor live system and adjust risk parameters

---

**Happy Trading! 🚀📈**

**⚠️ RISK DISCLAIMER**: This is a trading system for **educational and research purposes**. Always start with paper trading. Real money trading involves significant risk. Test thoroughly before deploying with real capital.

*Start with paper trading. Test extensively. Deploy carefully.*
