# Quick Start Guide - Algorithmic Trading System

## Prerequisites

1. **Environment Variables**: Set up your `.env` file (already configured):
   ```bash
   ALPACA_API_KEY=PKWT8EA81UL0QP85EYAR
   ALPACA_SECRET_KEY=1xASbdPSlONXPGtGClyUcxULzMeOtDPV7vXCtOTM
   ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2
   ```

2. **Rust Toolchain**: Ensure Rust is installed
   ```bash
   rustc --version  # Should be 1.70+
   ```

3. **Dependencies**: Install required packages
   ```bash
   # On Ubuntu/WSL
   sudo apt-get install jq
   ```

## Getting Started

### 1. Validate Configuration

```bash
./scripts/validate_config.sh
```

This will:
- Check JSON syntax in all config files
- Verify environment variables are set
- Display configuration summaries

### 2. Build Services

```bash
cd rust
cargo build --release
```

Expected output: All services compile successfully

### 3. Start the System

**Development Mode** (default):
```bash
./scripts/start_services.sh
```

**Staging Mode**:
```bash
TRADING_ENV=staging ./scripts/start_services.sh
```

**Production Mode** (⚠️ Live trading!):
```bash
TRADING_ENV=production ./scripts/start_services.sh
```

### 4. Check System Health

```bash
./scripts/health_check.sh
```

Expected output:
```
=== Trading System Health Check ===

Service Status:
✓ market-data is running (PID: 12345)
✓ risk-manager is running (PID: 12346)
✓ execution-engine is running (PID: 12347)
✓ signal-bridge is running (PID: 12348)

Configuration:
  Environment: development
  Paper Trading: true
```

### 5. Monitor Logs

```bash
# Real-time monitoring
tail -f logs/market-data.log
tail -f logs/execution-engine.log
tail -f logs/risk-manager.log
tail -f logs/signal-bridge.log

# Or use tmux/screen for multiple terminals
```

### 6. Stop the System

```bash
./scripts/stop_services.sh
```

## Service Overview

### Market Data Service
- **Purpose**: Connects to Alpaca WebSocket, streams real-time market data
- **Output**: Publishes market data to ZeroMQ (tcp://127.0.0.1:5555)
- **Monitored Symbols**: AAPL, MSFT, GOOGL, AMZN, TSLA (dev mode)

### Risk Manager
- **Purpose**: Enforces risk limits and circuit breakers
- **Risk Limits** (dev mode):
  - Max Position Size: 1000 shares
  - Max Notional Exposure: $50,000
  - Max Daily Loss: $5,000
  - Stop Loss: 2%
  - Trailing Stop: 1.5%

### Execution Engine
- **Purpose**: Executes trades via Alpaca API
- **Features**:
  - Retry logic (3 attempts, 1s delay)
  - Rate limiting (200 req/sec)
  - Slippage monitoring
  - Paper trading mode

### Signal Bridge
- **Purpose**: Bridge between Python ML models and Rust execution
- **Features**:
  - Feature extraction from market data
  - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
  - ZeroMQ integration
  - Real-time signal generation

## Configuration Environments

| Environment | Paper Trading | Max Position | Max Exposure | Daily Loss Limit | Update Interval |
|-------------|---------------|--------------|--------------|------------------|-----------------|
| Development | ✅ Yes        | 1000 shares  | $50,000      | $5,000          | 1000ms          |
| Staging     | ✅ Yes        | 500 shares   | $25,000      | $2,500          | 500ms           |
| Production  | ❌ **LIVE**   | 250 shares   | $10,000      | $1,000          | 250ms           |

## Common Tasks

### Change Environment

```bash
# Use symbolic link
cd config
ln -sf system.staging.json system.json

# Or set environment variable
export TRADING_ENV=staging
./scripts/start_services.sh
```

### View Service Logs

```bash
# Last 50 lines
tail -50 logs/market-data.log

# Follow in real-time
tail -f logs/execution-engine.log

# Search for errors
grep ERROR logs/*.log
```

### Test Configuration

```bash
# Validate JSON
jq empty config/system.json

# View specific config section
jq '.risk' config/system.json

# Compare environments
diff <(jq -S . config/system.json) <(jq -S . config/system.staging.json)
```

### Manual Service Start

```bash
cd rust

# Market Data
RUST_LOG=info ./target/release/market-data

# Risk Manager
RUST_LOG=info ./target/release/risk-manager

# Execution Engine
RUST_LOG=info ./target/release/execution-engine

# Signal Bridge
RUST_LOG=info ./target/release/signal-bridge
```

## Troubleshooting

### Services won't start

1. Check environment variables:
   ```bash
   echo $ALPACA_API_KEY
   echo $ALPACA_SECRET_KEY
   ```

2. Verify configuration:
   ```bash
   ./scripts/validate_config.sh
   ```

3. Check build errors:
   ```bash
   cd rust
   cargo build 2>&1 | tee build.log
   ```

### Configuration errors

```bash
# Validate JSON syntax
jq empty config/system.json

# Check for missing fields
jq '.market_data' config/system.json
jq '.risk' config/system.json
jq '.execution' config/system.json
jq '.signal' config/system.json
```

### Service crashes

```bash
# Check logs for errors
grep -i error logs/*.log
grep -i panic logs/*.log

# Run with debug logging
RUST_LOG=debug ./target/release/market-data
```

### ZeroMQ connection issues

```bash
# Check if ports are in use
netstat -tlnp | grep 5555
netstat -tlnp | grep 5556

# Test ZeroMQ connectivity
# (requires zeromq tools)
zmq_sub tcp://127.0.0.1:5555
```

## Safety Checklist

Before running in **production mode**:

- [ ] Verify API credentials are for the correct account
- [ ] Review risk limits in `config/system.production.json`
- [ ] Test thoroughly in paper trading mode
- [ ] Enable circuit breakers (`enable_circuit_breaker: true`)
- [ ] Set appropriate stop loss percentages
- [ ] Configure monitoring and alerts
- [ ] Review and understand all risk parameters
- [ ] Have a plan for manual intervention
- [ ] Monitor initial trades closely
- [ ] Start with minimal position sizes

## Support & Resources

- **Configuration**: See `/config/README.md`
- **Implementation**: See `/docs/CODER_IMPLEMENTATION_SUMMARY.md`
- **API Docs**: https://alpaca.markets/docs/api-documentation/
- **ZeroMQ**: https://zeromq.org/
- **Rust Tracing**: https://docs.rs/tracing/

## Next Steps

1. Run system in development mode
2. Monitor logs and verify connectivity
3. Test with paper trading
4. Gradually increase complexity
5. Add Python ML integration
6. Implement custom strategies
7. Backtest thoroughly
8. Consider production deployment

---

**Remember**: Start small, test extensively, and never trade with money you can't afford to lose!
