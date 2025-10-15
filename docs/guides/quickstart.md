# Quick Start Guide

Get the py_rt trading system running in 10 minutes.

## Prerequisites

Before you begin, ensure you have:

- **Rust 1.70+** - Install from [rustup.rs](https://rustup.rs/)
- **Python 3.11+** - Install from [python.org](https://python.org)
- **uv** - Fast Python package manager: `pip install uv`
- **Alpaca Markets Account** - Free paper trading at [alpaca.markets](https://alpaca.markets)

## Step 1: Clone Repository

```bash
git clone https://github.com/SamoraDC/RustAlgorithmTrading.git
cd RustAlgorithmTrading
```

## Step 2: Install Dependencies

### Python Dependencies
```bash
# Install Python dependencies with uv
uv sync

# Verify installation
uv run python --version
```

### Rust Dependencies
```bash
# Navigate to Rust workspace
cd rust

# Build all components (this will take a few minutes on first build)
cargo build --release

# Run tests to verify installation
cargo test --workspace
```

## Step 3: Configure API Keys

Create a `.env` file in the project root:

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env
```

Add your Alpaca API keys:

```env
# Alpaca API Keys (Paper Trading)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_URL=https://data.alpaca.markets

# System Configuration
RUST_LOG=info
LOG_LEVEL=INFO
```

Get your API keys from [Alpaca Dashboard](https://app.alpaca.markets/paper/dashboard/overview).

## Step 4: Test Alpaca Connection

Verify your API credentials work:

```bash
# Run connection test
uv run python python-trading/test_alpaca_connection.py
```

Expected output:
```
Account Status: ACTIVE
Buying Power: $100000.00
Portfolio Value: $100000.00
Equity: $100000.00
```

## Step 5: Create System Configuration

Create `config/system.json`:

```json
{
  "market_data": {
    "alpaca_api_key": "${ALPACA_API_KEY}",
    "alpaca_secret_key": "${ALPACA_SECRET_KEY}",
    "zmq_pub_address": "tcp://*:5555",
    "symbols": ["AAPL", "MSFT", "GOOGL"],
    "reconnect_delay_secs": 5
  },
  "signal_bridge": {
    "zmq_sub_address": "tcp://localhost:5555",
    "zmq_pub_address": "tcp://*:5556",
    "python_module": "src.strategies.momentum"
  },
  "risk_manager": {
    "zmq_sub_address": "tcp://localhost:5555,tcp://localhost:5556",
    "zmq_pub_address": "tcp://*:5557",
    "max_position_size": 10000.0,
    "max_order_size": 1000.0,
    "max_daily_loss": 5000.0,
    "position_limit_pct": 0.1
  },
  "execution_engine": {
    "alpaca_api_key": "${ALPACA_API_KEY}",
    "alpaca_secret_key": "${ALPACA_SECRET_KEY}",
    "zmq_sub_address": "tcp://localhost:5557",
    "zmq_pub_address": "tcp://*:5558",
    "max_retries": 3,
    "max_slippage_bps": 50,
    "rate_limit_per_minute": 200
  }
}
```

## Step 6: Start the System

Open 4 terminal windows and start each component:

### Terminal 1: Market Data Service
```bash
cd rust/market-data
RUST_LOG=info cargo run --release
```

Wait for: `Market Data Service started on tcp://*:5555`

### Terminal 2: Signal Bridge
```bash
cd rust/signal-bridge
RUST_LOG=info cargo run --release
```

Wait for: `Signal Bridge connected to tcp://localhost:5555`

### Terminal 3: Risk Manager
```bash
cd rust/risk-manager
RUST_LOG=info cargo run --release
```

Wait for: `Risk Manager started, enforcing limits`

### Terminal 4: Execution Engine
```bash
cd rust/execution-engine
RUST_LOG=info cargo run --release
```

Wait for: `Execution Engine connected to Alpaca Markets`

## Step 7: Run a Simple Backtest

Test a strategy with historical data:

```bash
# Run basic momentum strategy backtest
uv run python examples/basic_backtest.py
```

Expected output:
```
Backtesting Momentum Strategy...
Total Return: 12.34%
Sharpe Ratio: 1.45
Max Drawdown: -8.21%
Win Rate: 54.3%
```

## Step 8: Monitor System Health

Check that all components are running:

```bash
# Check market data service
curl http://localhost:9090/metrics | grep market_data

# Check risk manager
curl http://localhost:9091/metrics | grep risk_manager

# Check execution engine
curl http://localhost:9092/metrics | grep execution_engine
```

## What's Next?

Now that your system is running:

1. **[Develop a Strategy](strategy-development.md)** - Create your first trading strategy
2. **[Configure Risk Limits](risk-management.md)** - Set up risk controls
3. **[Run Backtests](backtesting.md)** - Test strategies on historical data
4. **[Monitor Performance](monitoring.md)** - Set up dashboards and alerts

## Common Issues

### Port Already in Use
```bash
# Find process using port 5555
lsof -i :5555

# Kill process
kill -9 <PID>
```

### ZMQ Connection Failed
- Ensure services start in order: Market Data → Signal Bridge → Risk Manager → Execution Engine
- Check firewall settings allow localhost connections

### Alpaca API Errors
- Verify API keys are correct in `.env`
- Check account status at [Alpaca Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
- Ensure using paper trading URL for testing

### Python Import Errors
```bash
# Reinstall dependencies
uv sync --reinstall
```

### Rust Build Errors
```bash
# Clean and rebuild
cd rust
cargo clean
cargo build --release
```

## Need Help?

- Check [Troubleshooting Guide](../developer/troubleshooting.md)
- Search [GitHub Issues](https://github.com/SamoraDC/RustAlgorithmTrading/issues)
- Ask in [GitHub Discussions](https://github.com/SamoraDC/RustAlgorithmTrading/discussions)

---

**Next**: [Strategy Development Guide](strategy-development.md)
