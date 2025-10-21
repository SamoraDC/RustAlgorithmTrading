# Configuration Files

This directory contains configuration files for the algorithmic trading system.

## Files

### `system.json` (Development)
Default configuration for development environment with relaxed risk limits.

**Features:**
- Paper trading enabled
- Higher position limits for testing
- 5 symbols monitored
- 1-second signal update interval

### `system.staging.json` (Staging)
Configuration for staging environment with moderate risk controls.

**Features:**
- Paper trading enabled
- Tighter risk controls than development
- 8 symbols monitored
- 500ms signal update interval
- More technical indicators

### `system.production.json` (Production)
Configuration for live trading with strict risk controls.

**Features:**
- Live trading (paper_trading = false)
- Strictest risk limits
- 4 highly liquid symbols only
- 250ms signal update interval
- Comprehensive technical indicators
- Lower max loss thresholds

### `risk_limits.toml`
Comprehensive risk management parameters shared across all environments.

**Categories:**
- Position limits (max shares, notional exposure, concentration)
- Loss limits (per-trade, daily, weekly, monthly, drawdown)
- Stop loss configuration (default, trailing, min/max)
- Take profit settings (targets, risk/reward ratios, partial profits)
- Circuit breaker rules (triggers, cooldowns, auto-resume)
- Order validation (size limits, price bounds, slippage)
- Leverage controls
- Volatility-based adjustments
- Time restrictions (market hours, blackout periods)
- Correlation limits
- Monitoring and alerting

## Usage

### Loading Configuration in Rust

```rust
use common::config::SystemConfig;

// Load environment-specific config
let config = SystemConfig::from_file("config/system.json")?;

// Access components
let market_config = config.market_data;
let risk_config = config.risk;
let execution_config = config.execution;
let signal_config = config.signal;
```

### Environment Variables

API credentials should be loaded from environment variables, not hardcoded:

```bash
export ALPACA_API_KEY="your_key_here"
export ALPACA_SECRET_KEY="your_secret_here"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets/v2"
```

In the code, load them at runtime:

```rust
let api_key = std::env::var("ALPACA_API_KEY")
    .expect("ALPACA_API_KEY must be set");
let api_secret = std::env::var("ALPACA_SECRET_KEY")
    .expect("ALPACA_SECRET_KEY must be set");
```

## Configuration Validation

All configuration values are validated at load time:

- **Market Data**: WebSocket URL format, symbol list not empty
- **Risk**: Positive values, sensible thresholds
- **Execution**: Valid API URL, rate limits > 0, retry attempts > 0
- **Signal**: Model path exists, features list not empty, valid ZMQ addresses

## Environment Selection

Use symbolic links or environment variables to select configuration:

```bash
# Development (default)
ln -sf system.json config/active.json

# Staging
ln -sf system.staging.json config/active.json

# Production (use with caution!)
ln -sf system.production.json config/active.json
```

Or use environment variable:

```bash
export TRADING_ENV=staging
```

Then in code:

```rust
let env = std::env::var("TRADING_ENV").unwrap_or("development".to_string());
let config_path = format!("config/system.{}.json", env);
let config = SystemConfig::from_file(&config_path)?;
```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Restrict file permissions** on configuration files:
   ```bash
   chmod 600 config/system*.json
   chmod 600 config/risk_limits.toml
   ```
4. **Rotate API keys** regularly
5. **Use paper trading** until thoroughly tested
6. **Monitor risk limits** continuously
7. **Enable circuit breakers** in all environments

## Risk Parameters Tuning

When adjusting risk parameters:

1. **Start conservative** - Use lower position sizes and tighter stops
2. **Backtest thoroughly** - Validate changes against historical data
3. **Paper trade first** - Test in paper trading before going live
4. **Monitor closely** - Watch for unexpected behavior
5. **Document changes** - Keep track of why parameters were changed
6. **Review regularly** - Risk parameters should evolve with market conditions

## Circuit Breaker Triggers

The circuit breaker will halt trading when:

- Daily loss exceeds `max_daily_loss`
- Consecutive losing trades ≥ `max_consecutive_losses`
- Trades per day exceeds `max_trades_per_day`

After a circuit breaker trip:

- Trading is paused for `cooldown_minutes`
- All open positions are evaluated
- Manual intervention required (unless `auto_resume = true`)
- Incident is logged for review

## Monitoring Alerts

Configure alerts for:

- Position limit approaching (80% threshold)
- Daily loss limit approaching (80% threshold)
- Circuit breaker activation
- Failed orders or rejected trades
- Unusual market conditions
- System health checks failing

## Version History

- **1.0.0** (2025-10-21): Initial production-ready configuration
  - Three environment profiles (dev, staging, prod)
  - Comprehensive risk limits
  - Circuit breaker implementation
  - Correlation-based position management
