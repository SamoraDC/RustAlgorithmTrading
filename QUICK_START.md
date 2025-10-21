# 🚀 Quick Start - Autonomous Trading System

## ONE COMMAND TO START EVERYTHING

```bash
./scripts/start_trading.sh
```

That's it! The system handles the rest automatically:
- ✅ Backtesting
- ✅ Validation
- ✅ Paper Trading

---

## Prerequisites (5 Minutes)

### 1. Get Alpaca API Keys (FREE)

1. Go to [https://alpaca.markets/](https://alpaca.markets/)
2. Sign up (free account)
3. Generate **Paper Trading** API keys
4. Copy your API Key and Secret Key

### 2. Create `.env` File

Create a file called `.env` in this directory:

```bash
ALPACA_API_KEY=PK1234567890ABCDEF
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true
```

**Replace with your actual keys from Alpaca!**

---

## Start Trading

### Method 1: Simple Start (Recommended)

```bash
./scripts/start_trading.sh
```

This runs:
1. **Backtesting** - Tests strategy on 1 year of historical data
2. **Validation** - Monte Carlo simulation (1000 iterations)
3. **Paper Trading** - Live paper trading (if validation passes)

### Method 2: Advanced Options

**Backtest Only** (test strategies):
```bash
./scripts/autonomous_trading_system.sh --mode=backtest-only
```

**Paper Trading Only** (skip validation):
```bash
./scripts/autonomous_trading_system.sh --mode=paper-only
```

**Continuous 24/7** (auto-restart):
```bash
./scripts/autonomous_trading_system.sh --mode=continuous
```

---

## Monitor Your System

### View Real-time Logs

```bash
tail -f logs/autonomous/autonomous.log
```

### Check Backtest Results

```bash
cat data/backtest_results/backtest_*.json | jq .
```

### Check Account Status

The system logs your account status every 30 seconds:
- Cash available
- Portfolio value
- Current positions
- P&L per position

---

## Stop Trading

Press `Ctrl+C` to stop gracefully. The system will:
1. Close all open positions
2. Cancel pending orders
3. Stop all services
4. Save current state

---

## What Happens Automatically?

### Phase 1: Backtesting (30-60 seconds)

```
[INFO] Running backtesting engine with historical data...
[BACKTEST] Running backtest for ['AAPL', 'MSFT', 'GOOGL']
[BACKTEST] Period: 2024-01-01 to 2025-01-20
[BACKTEST] Initial capital: $100,000.00

[BACKTEST] Results:
  Final Value: $125,430.00
  Total Return: 25.43%
  Sharpe Ratio: 1.85
  Max Drawdown: -12.50%
  Win Rate: 62.50%
  Profit Factor: 2.10

[SUCCESS] Backtesting phase PASSED
```

### Phase 2: Simulation (10-30 seconds)

```
[INFO] Running Monte Carlo simulation...
[SIMULATION] Monte Carlo Results (1000 iterations):
  Mean Return: 24.50%
  Median Return: 23.80%
  5th Percentile: 5.20%
  95th Percentile: 48.30%
  Probability of Profit: 78.50%

[SUCCESS] Simulation phase PASSED
```

### Phase 3: Paper Trading (Continuous)

```
[INFO] Starting Rust microservices...
[SUCCESS] market-data started (PID: 12345)
[SUCCESS] risk-manager started (PID: 12346)
[SUCCESS] execution-engine started (PID: 12347)

[TRADING] Account Status:
  Cash: $100,000.00
  Portfolio Value: $100,000.00
  Buying Power: $200,000.00

[TRADING] Starting autonomous trading loop...
[TRADING] Market is open - trading active

[TRADING] Iteration 1 - 2025-01-21 09:35:00
[TRADING] Current positions: 2
  AAPL: 10 shares, P&L: $125.50 (1.25%)
  MSFT: 5 shares, P&L: -$45.20 (-0.45%)
```

---

## Safety Features (All Automatic)

### ✅ Forced Paper Trading
- Live trading is **DISABLED**
- All trades go to paper account
- Zero real money risk

### ✅ Circuit Breaker
Auto-stops trading when:
- Daily loss > $5,000
- 5 consecutive losses
- Max drawdown > 20%

### ✅ Position Limits
- Max per position: $10,000
- Max total exposure: $50,000
- Max concurrent positions: 10

### ✅ Risk Validation
Every order checked for:
- Sufficient buying power
- Position size limits
- Stop-loss requirements
- Slippage protection

### ✅ Graceful Shutdown
On stop signal:
1. Closes all positions
2. Cancels pending orders
3. Saves state
4. Clean exit

---

## Validation Thresholds

The system validates before paper trading:

| Metric | Minimum Required |
|--------|-----------------|
| **Sharpe Ratio** | ≥ 1.0 |
| **Win Rate** | ≥ 50% |
| **Max Drawdown** | ≤ 20% |
| **5th Percentile Return** | ≥ -10% |
| **Probability of Profit** | ≥ 60% |

**If any threshold fails → paper trading is blocked!**

---

## Troubleshooting

### Problem: "ALPACA_API_KEY not set"

**Solution**: Create `.env` file with your credentials:

```bash
echo "ALPACA_API_KEY=PK..." > .env
echo "ALPACA_SECRET_KEY=..." >> .env
echo "ALPACA_PAPER=true" >> .env
```

### Problem: "Backtesting phase FAILED"

**Cause**: Strategy doesn't meet minimum thresholds

**Solution**: Check results:
```bash
cat data/backtest_results/backtest_*.json | jq .
```

Strategy may need adjustment or different symbols.

### Problem: "Market is closed"

**Cause**: Trading outside market hours

**Solution**: Wait for market to open (Mon-Fri, 9:30 AM - 4:00 PM ET) or the system will automatically wait and notify you when market opens.

### Problem: Services won't start

**Solution**: Kill stuck processes:
```bash
pkill -f market-data
pkill -f risk-manager
pkill -f execution-engine
```

Then restart.

---

## Run as 24/7 Service (Optional)

For continuous operation:

```bash
# Install as system service
sudo cp autonomous-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable autonomous-trading
sudo systemctl start autonomous-trading

# Monitor
sudo journalctl -u autonomous-trading -f
```

---

## File Structure

```
RustAlgorithmTrading/
├── .env                          # Your Alpaca credentials (CREATE THIS)
├── scripts/
│   ├── start_trading.sh          # ← START HERE (simple)
│   └── autonomous_trading_system.sh  # Advanced launcher
├── logs/autonomous/              # System logs
├── data/
│   ├── backtest_results/         # Backtest outputs
│   ├── simulation_results/       # Simulation outputs
│   └── live_trading/             # Paper trading data
└── docs/
    └── AUTONOMOUS_SYSTEM_GUIDE.md  # Full documentation
```

---

## Next Steps

### 1. First Run (Testing)

Start in backtest-only mode to test strategy:

```bash
./scripts/autonomous_trading_system.sh --mode=backtest-only
```

Review results before paper trading.

### 2. Full Pipeline (Recommended)

Run complete validation + paper trading:

```bash
./scripts/start_trading.sh
```

Monitor for 1-2 weeks.

### 3. Continuous Operation (Production)

Once confident, run 24/7:

```bash
./scripts/autonomous_trading_system.sh --mode=continuous
```

Or install as systemd service.

---

## Summary

**To start everything autonomously:**

```bash
# 1. Create .env with Alpaca credentials
echo "ALPACA_API_KEY=your_key" > .env
echo "ALPACA_SECRET_KEY=your_secret" >> .env
echo "ALPACA_PAPER=true" >> .env

# 2. Start trading system
./scripts/start_trading.sh

# 3. Monitor (in another terminal)
tail -f logs/autonomous/autonomous.log
```

**That's it! The system does everything else automatically.** 🚀

---

## Documentation

- **Quick Start**: This file
- **Full Guide**: `docs/AUTONOMOUS_SYSTEM_GUIDE.md`
- **Deployment**: `docs/deployment/PRODUCTION_DEPLOYMENT.md`
- **Operations**: `docs/operations/OPERATIONS_RUNBOOK.md`

---

**Happy Autonomous Trading!** 🤖💰
