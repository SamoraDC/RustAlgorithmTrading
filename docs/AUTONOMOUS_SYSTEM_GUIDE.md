# 🤖 Autonomous Trading System Guide

## Overview

The autonomous trading system runs the complete pipeline automatically:

1. **Backtesting** - Tests strategies on historical data
2. **Simulation** - Monte Carlo validation
3. **Paper Trading** - Live paper trading with Alpaca

**Zero human intervention required!** ✅

---

## Quick Start (5 Minutes)

### Step 1: Set Up Credentials

Create a `.env` file in the project root:

```bash
# Alpaca API Credentials (Paper Trading)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true
```

**Get your credentials**:
1. Go to [Alpaca Markets](https://alpaca.markets/)
2. Sign up for free
3. Generate paper trading API keys
4. Paste them in `.env`

### Step 2: Start Everything

**One command to start everything:**

```bash
./scripts/start_trading.sh
```

That's it! The system will:
- ✅ Validate environment
- ✅ Build Rust services
- ✅ Run backtesting
- ✅ Run Monte Carlo simulation
- ✅ Start paper trading (if validation passes)

---

## Usage Modes

### Mode 1: Full Pipeline (Recommended)

Runs everything: backtest → simulation → paper trading

```bash
./scripts/autonomous_trading_system.sh --mode=full
```

**Flow**:
1. Backtests strategy on 1 year of data
2. Validates metrics (Sharpe > 1.0, Win Rate > 50%)
3. Runs Monte Carlo simulation (1000 iterations)
4. If validation passes → starts paper trading
5. If validation fails → stops and logs error

### Mode 2: Backtest Only

Run backtesting to test strategies:

```bash
./scripts/autonomous_trading_system.sh --mode=backtest-only
```

Results saved to: `data/backtest_results/`

### Mode 3: Paper Trading Only

Skip validation, go straight to paper trading:

```bash
./scripts/autonomous_trading_system.sh --mode=paper-only
```

⚠️ **Warning**: Skips risk validation!

### Mode 4: Continuous Operation (24/7)

Run forever with auto-restart on failures:

```bash
./scripts/autonomous_trading_system.sh --mode=continuous
```

**Features**:
- Auto-restarts on failure (max 5 attempts)
- Runs initial validation once
- Continuous paper trading
- Perfect for production deployment

---

## Validation Thresholds

The system validates strategies before paper trading:

### Backtesting Thresholds

| Metric | Minimum | Excellent |
|--------|---------|-----------|
| **Sharpe Ratio** | 1.0 | 2.0+ |
| **Win Rate** | 50% | 60%+ |
| **Max Drawdown** | -20% | -10% |
| **Profit Factor** | 1.5 | 2.0+ |

### Simulation Thresholds

| Metric | Minimum | Excellent |
|--------|---------|-----------|
| **5th Percentile Return** | -10% | 0%+ |
| **Probability of Profit** | 60% | 80%+ |

**If any threshold fails → paper trading is blocked!** ✋

---

## Monitoring

### Real-time Logs

View live trading activity:

```bash
tail -f logs/autonomous/autonomous.log
```

### Service Logs

View individual service logs:

```bash
# Market data service
tail -f logs/autonomous/market-data.log

# Risk manager
tail -f logs/autonomous/risk-manager.log

# Execution engine
tail -f logs/autonomous/execution-engine.log
```

### Results

Check backtesting results:

```bash
ls -lh data/backtest_results/
cat data/backtest_results/backtest_*.json | jq .
```

Check simulation results:

```bash
ls -lh data/simulation_results/
cat data/simulation_results/simulation_*.json | jq .
```

---

## System as a Service (Optional)

### Run 24/7 with systemd

For production deployment, install as a system service:

```bash
# Copy service file
sudo cp autonomous-trading.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable (start on boot)
sudo systemctl enable autonomous-trading

# Start now
sudo systemctl start autonomous-trading

# Check status
sudo systemctl status autonomous-trading

# View logs
sudo journalctl -u autonomous-trading -f
```

### Service Management

```bash
# Stop the service
sudo systemctl stop autonomous-trading

# Restart the service
sudo systemctl restart autonomous-trading

# Disable (don't start on boot)
sudo systemctl disable autonomous-trading
```

---

## Safety Features

### 1. Forced Paper Trading ✅

Live trading is **DISABLED** by default. The system forces paper trading mode:

```python
export ALPACA_PAPER=true
```

### 2. Circuit Breaker ✅

Automatic halt when:
- Daily loss > $5,000
- 5 consecutive losing trades
- Max drawdown > 20%

### 3. Position Limits ✅

Conservative limits enforced:
- Max position: $10,000 per symbol
- Max total exposure: $50,000
- Max positions: 10 concurrent

### 4. Risk Checks ✅

Every order validated for:
- Sufficient buying power
- Position size limits
- Stop-loss requirements
- Slippage protection

### 5. Graceful Shutdown ✅

On Ctrl+C or system signal:
1. Closes all open positions
2. Cancels pending orders
3. Saves current state
4. Shuts down cleanly

---

## Troubleshooting

### Issue: "ALPACA_API_KEY not set"

**Solution**: Create `.env` file with your credentials

```bash
echo "ALPACA_API_KEY=your_key" > .env
echo "ALPACA_SECRET_KEY=your_secret" >> .env
echo "ALPACA_PAPER=true" >> .env
```

### Issue: "Backtesting phase FAILED"

**Cause**: Strategy metrics below threshold

**Solution**: Check backtest results:

```bash
cat data/backtest_results/backtest_*.json | jq '.sharpe_ratio, .win_rate, .max_drawdown'
```

If metrics are poor:
1. Adjust strategy parameters
2. Use different symbols
3. Change time period

### Issue: "Failed to build Rust services"

**Solution**: Ensure Rust is installed:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### Issue: "Market is closed"

**Cause**: Trading attempted outside market hours

**Solution**: Wait for market to open or test with different symbols. Market hours:
- Monday-Friday: 9:30 AM - 4:00 PM ET
- Closed: Weekends and holidays

### Issue: Services won't start

**Check PIDs**:

```bash
ls -lh logs/autonomous/*.pid
```

**Kill stuck processes**:

```bash
pkill -f "market-data"
pkill -f "risk-manager"
pkill -f "execution-engine"
```

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 AUTONOMOUS TRADING SYSTEM                   │
└─────────────────────────────────────────────────────────────┘

                         START
                           ↓
                  ┌────────────────┐
                  │  Environment   │
                  │  Validation    │
                  └────────┬───────┘
                           ↓
                  ┌────────────────┐
                  │ Build Rust     │
                  │ Services       │
                  └────────┬───────┘
                           ↓
         ╔═════════════════════════════════╗
         ║  PHASE 1: BACKTESTING           ║
         ╚═════════════════════════════════╝
                           ↓
              ┌────────────────────┐
              │ Load Historical    │
              │ Data (1 year)      │
              └─────────┬──────────┘
                        ↓
              ┌────────────────────┐
              │ Execute Strategy   │
              │ (AAPL, MSFT, GOOGL)│
              └─────────┬──────────┘
                        ↓
              ┌────────────────────┐
              │ Calculate Metrics  │
              │ (Sharpe, Win Rate) │
              └─────────┬──────────┘
                        ↓
              ╔══════════════════╗
              ║ Metrics >= Min?  ║
              ╚════════┬═════════╝
                  NO  │  YES
              ┌───────┴────────┐
              ↓                ↓
         [FAIL/STOP]    ╔═════════════════════════════════╗
                        ║  PHASE 2: SIMULATION            ║
                        ╚═════════════════════════════════╝
                                  ↓
                        ┌────────────────────┐
                        │ Monte Carlo Sim    │
                        │ (1000 iterations)  │
                        └─────────┬──────────┘
                                  ↓
                        ┌────────────────────┐
                        │ Calculate Stats    │
                        │ (5%ile, P(profit)) │
                        └─────────┬──────────┘
                                  ↓
                        ╔══════════════════╗
                        ║ Risk Acceptable? ║
                        ╚════════┬═════════╝
                            NO  │  YES
                        ┌───────┴────────┐
                        ↓                ↓
                   [FAIL/STOP]    ╔═════════════════════════════════╗
                                  ║  PHASE 3: PAPER TRADING         ║
                                  ╚═════════════════════════════════╝
                                            ↓
                                  ┌────────────────────┐
                                  │ Start Rust         │
                                  │ Microservices      │
                                  │ (market-data,      │
                                  │  risk-manager,     │
                                  │  execution)        │
                                  └─────────┬──────────┘
                                            ↓
                                  ┌────────────────────┐
                                  │ Connect to Alpaca  │
                                  │ WebSocket + REST   │
                                  └─────────┬──────────┘
                                            ↓
                        ╔════════════════════════════════╗
                        ║     AUTONOMOUS TRADING LOOP    ║
                        ║                                ║
                        ║  • Monitor market data         ║
                        ║  • Generate signals            ║
                        ║  • Execute trades              ║
                        ║  • Manage risk                 ║
                        ║  • Track positions             ║
                        ║                                ║
                        ║  Runs until: Ctrl+C or error   ║
                        ╚════════════════════════════════╝
                                            ↓
                                  ┌────────────────────┐
                                  │ Graceful Shutdown  │
                                  │ • Close positions  │
                                  │ • Save state       │
                                  │ • Stop services    │
                                  └────────────────────┘
                                            ↓
                                          END
```

---

## Performance Expectations

### Backtesting

- **Duration**: 30-60 seconds (1 year of data)
- **Symbols**: 3 (configurable)
- **Output**: JSON results + metrics

### Simulation

- **Duration**: 10-30 seconds
- **Iterations**: 1,000 Monte Carlo runs
- **Output**: Risk statistics

### Paper Trading

- **Latency**: <100ms per trade (target)
- **Throughput**: 100+ trades/day
- **Update Frequency**: Every 30 seconds

---

## Customization

### Change Symbols

Edit in `autonomous_trading_system.sh`:

```python
symbols = ['AAPL', 'MSFT', 'GOOGL']  # Change these
```

### Change Thresholds

Edit in `autonomous_trading_system.sh`:

```bash
MIN_SHARPE_RATIO=1.0      # Change to 1.5 for stricter
MIN_WIN_RATE=0.50         # Change to 0.60 for stricter
MAX_DRAWDOWN=0.20         # Change to 0.15 for stricter
```

### Change Trading Frequency

Edit in `autonomous_trading_system.sh`:

```python
time.sleep(30)  # Change from 30 seconds to your preference
```

### Add Your Own Strategy

Replace `SimpleMomentumStrategy` with your custom strategy:

```python
from strategies.my_custom_strategy import MyCustomStrategy

strategy = MyCustomStrategy(symbols)
```

---

## Next Steps

### 1. Start Simple

Run backtest-only mode first:

```bash
./scripts/autonomous_trading_system.sh --mode=backtest-only
```

Review results before paper trading.

### 2. Test Simulation

Run simulation to understand risk:

```bash
./scripts/autonomous_trading_system.sh --mode=full
```

Check if validation passes.

### 3. Monitor Paper Trading

Watch for 1-2 weeks in paper trading mode. Track:
- P&L consistency
- Win rate vs backtest
- Drawdown patterns
- Execution quality

### 4. Optimize

Based on paper trading results:
- Adjust strategy parameters
- Fine-tune risk limits
- Optimize entry/exit timing

### 5. Scale Up (Optional)

Once confident:
- Add more symbols
- Increase position sizes
- Deploy as systemd service

---

## Support

**Logs**: `logs/autonomous/`
**Results**: `data/backtest_results/`, `data/simulation_results/`
**Documentation**: `/docs/`

---

**Ready to go autonomous?** 🚀

```bash
./scripts/start_trading.sh
```

The system handles everything else!
