# Risk Management Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-21

---

## Table of Contents

1. [Overview](#overview)
2. [Stop-Loss Configuration](#stop-loss-configuration)
3. [Position Sizing](#position-sizing)
4. [Circuit Breakers](#circuit-breakers)
5. [Risk Limits](#risk-limits)
6. [Examples](#examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The risk management system provides comprehensive controls to protect capital and enforce trading discipline. It operates at multiple levels:

1. **Order Level:** Validate individual orders
2. **Position Level:** Monitor position sizes and stop-losses
3. **Portfolio Level:** Enforce overall exposure limits
4. **System Level:** Circuit breakers and emergency controls

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Risk Manager                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Order        │  │ Position     │  │ Circuit      │      │
│  │ Validation   │  │ Management   │  │ Breaker      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            ▼                                 │
│                    ┌──────────────┐                          │
│                    │ Stop-Loss    │                          │
│                    │ Manager      │                          │
│                    └──────────────┘                          │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             ▼
                      Execution Engine
```

---

## Stop-Loss Configuration

### Configuration File

All stop-loss settings are configured in `config/risk_limits.toml`:

```toml
[stop_loss]
# Default stop loss percentage below entry price
default_stop_loss_percent = 2.0

# Minimum stop loss percentage (cannot be set lower)
min_stop_loss_percent = 0.5

# Maximum stop loss percentage (cannot be set higher)
max_stop_loss_percent = 10.0

# Enable trailing stop loss
enable_trailing_stop = true

# Trailing stop distance (percentage)
trailing_stop_percent = 1.5

# Trailing stop activation (only activate after profit exceeds this %)
trailing_activation_percent = 2.0
```

### Static Stop-Loss

**How it works:**
- Set at order entry based on `default_stop_loss_percent`
- Remains fixed at the calculated price
- Triggers market sell when price falls below stop level

**Example:**
```rust
// Entry price: $100.00
// Stop-loss: 2% below entry = $98.00
// If price drops to $98.00 → market sell triggered

let position = Position {
    entry_price: 100.00,
    stop_loss: 98.00, // 2% below entry
    quantity: 100,
    // ...
};
```

**Configuration:**
```toml
[stop_loss]
default_stop_loss_percent = 2.0  # 2% below entry
min_stop_loss_percent = 0.5      # Minimum allowed: 0.5%
max_stop_loss_percent = 10.0     # Maximum allowed: 10%
```

### Trailing Stop-Loss

**How it works:**
1. Only activates after profit exceeds `trailing_activation_percent`
2. Follows price up, maintaining `trailing_stop_percent` distance
3. Never moves down (only up)
4. Locks in profits as price rises

**Example:**
```rust
// Entry: $100.00
// Trailing activation: 2% profit = $102.00
// Trailing distance: 1.5%

// Price reaches $102.00 → trailing stop activates at $100.47 (1.5% below)
// Price rises to $105.00 → trailing stop moves to $103.43
// Price falls to $103.43 → market sell triggered
```

**Configuration:**
```toml
[stop_loss]
enable_trailing_stop = true
trailing_stop_percent = 1.5        # 1.5% below current high
trailing_activation_percent = 2.0  # Activate after 2% profit
```

**Visual Example:**

```
Price Movement:
$100 ───┬─→ $102 ───┬─→ $105 ───┬─→ $104 ───┬─→ $103.43 ─→ SELL
        │           │           │           │
Entry   │  Trailing │  Trailing │  Trailing │  Stop Hit
        │  Activates│  Moves Up │  Holds    │
        │           │           │           │
Stop:   │  $98.00   │  $100.47  │  $103.43  │  $103.43
```

### Take-Profit Configuration

```toml
[take_profit]
# Default take profit percentage above entry price
default_take_profit_percent = 5.0

# Minimum risk/reward ratio for new trades
min_risk_reward_ratio = 2.0

# Enable partial profit taking
enable_partial_profit = true

# Percentage of position to close at first target
partial_profit_percent = 50.0

# First take profit target (percentage above entry)
first_target_percent = 3.0

# Second take profit target (percentage above entry)
second_target_percent = 5.0
```

**Partial Profit Taking Example:**

```rust
// Entry: $100.00, Quantity: 200 shares
// First target: $103.00 (3%) → sell 100 shares (50%)
// Second target: $105.00 (5%) → sell 100 shares (remaining 50%)

// Price reaches $103.00:
//   - Sell 100 shares at market
//   - Move stop-loss to breakeven ($100.00)
//   - Wait for second target

// Price reaches $105.00:
//   - Sell remaining 100 shares
//   - Position closed completely
```

---

## Position Sizing

### Position Limits

```toml
[position_limits]
# Maximum shares per position
max_shares = 1000

# Maximum notional value per position (USD)
max_notional_per_position = 10000.0

# Maximum total notional exposure across all positions (USD)
max_total_exposure = 50000.0

# Maximum number of concurrent open positions
max_open_positions = 5

# Maximum concentration in a single symbol (percentage of total portfolio)
max_concentration_percent = 25.0
```

### Volatility-Based Position Sizing

```toml
[volatility]
# Maximum allowed volatility (ATR as percentage of price)
max_atr_percent = 5.0

# Reduce position size when volatility exceeds threshold
reduce_on_high_volatility = true

# Volatility-based position sizing
enable_volatility_scaling = true

# Base volatility for scaling (percentage)
base_volatility_percent = 2.0
```

**Formula:**

```rust
// Position size = (Account risk / (Stop distance × Price)) × Volatility adjustment

let account_risk = 1000.0; // $1,000 max loss
let stop_distance = 0.02;  // 2%
let price = 100.0;
let current_volatility = 3.0; // 3% ATR
let base_volatility = 2.0;    // 2% base

let base_shares = account_risk / (stop_distance * price);
// base_shares = 1000 / (0.02 * 100) = 500

let volatility_adjustment = base_volatility / current_volatility;
// adjustment = 2.0 / 3.0 = 0.667

let adjusted_shares = base_shares * volatility_adjustment;
// adjusted_shares = 500 * 0.667 = 333 shares
```

### Correlation Limits

```toml
[correlation]
# Maximum correlation between positions
max_position_correlation = 0.7

# Check correlation before opening new positions
enforce_correlation_check = true

# Lookback period for correlation calculation (days)
correlation_lookback_days = 30
```

**Example:**

```rust
// Portfolio: AAPL (100 shares), Current correlation: 0.85
// Attempting to buy MSFT: correlation_check(AAPL, MSFT) = 0.85

if correlation > 0.7 {
    // REJECTED: Too highly correlated with existing position
    return Err("Position correlation exceeds limit (0.85 > 0.7)");
}
```

---

## Circuit Breakers

### Configuration

```toml
[circuit_breaker]
# Enable circuit breaker mechanism
enabled = true

# Daily loss threshold to trigger circuit breaker (USD)
daily_loss_threshold = 5000.0

# Maximum consecutive losing trades before pause
max_consecutive_losses = 5

# Maximum number of trades per day
max_trades_per_day = 50

# Cooldown period after circuit breaker trips (minutes)
cooldown_minutes = 60

# Auto-resume after cooldown
auto_resume = false
```

### Triggers

The circuit breaker activates when **ANY** of these conditions are met:

1. **Daily Loss Limit:** Total losses exceed $5,000 in a single day
2. **Consecutive Losses:** 5 losing trades in a row
3. **Trade Limit:** 50 trades executed in a single day

### Behavior

When circuit breaker trips:

```
1. ✓ All pending orders are cancelled
2. ✓ No new orders accepted
3. ✓ Existing positions remain open (protected by stop-losses)
4. ✓ System enters cooldown mode
5. ⏰ Wait 60 minutes (configurable)
6. 🔐 Manual resume required (auto_resume = false)
```

### Manual Resume

```bash
# Check circuit breaker status
curl http://localhost:8000/api/system/circuit-breaker/status

# Resume trading (requires authentication)
curl -X POST http://localhost:8000/api/system/circuit-breaker/resume \
  -H "Authorization: Bearer <token>"
```

### Example Scenario

```rust
// Scenario: 5 consecutive losses
// Trade 1: -$200
// Trade 2: -$150
// Trade 3: -$300
// Trade 4: -$100
// Trade 5: -$250 → CIRCUIT BREAKER TRIGGERED

let losses = vec![-200, -150, -300, -100, -250];
let consecutive_losses = 5;

if consecutive_losses >= max_consecutive_losses {
    trigger_circuit_breaker(CircuitBreakerReason::ConsecutiveLosses);
    cancel_all_pending_orders();
    notify_admin("Circuit breaker activated: 5 consecutive losses");
    enter_cooldown(60); // minutes
}
```

---

## Risk Limits

### Loss Limits

```toml
[loss_limits]
# Maximum loss per trade (USD)
max_loss_per_trade = 500.0

# Maximum daily loss (USD) - triggers circuit breaker
max_daily_loss = 5000.0

# Maximum weekly loss (USD)
max_weekly_loss = 15000.0

# Maximum monthly loss (USD)
max_monthly_loss = 50000.0

# Drawdown percentage that triggers position reduction
drawdown_threshold_percent = 10.0
```

### Order Validation

```toml
[order_validation]
# Minimum order size (shares)
min_order_size = 1

# Maximum order size (shares)
max_order_size = 1000

# Maximum order value (USD)
max_order_value = 10000.0

# Minimum price for orders (USD)
min_price = 0.01

# Maximum price for orders (USD)
max_price = 10000.0

# Maximum slippage tolerance (percentage)
max_slippage_percent = 0.5
```

### Time Restrictions

```toml
[time_restrictions]
# Allow trading only during market hours
enforce_market_hours = true

# Allow trading in pre-market (4:00 AM - 9:30 AM ET)
allow_premarket = false

# Allow trading in after-hours (4:00 PM - 8:00 PM ET)
allow_afterhours = false

# Blackout periods (no trading) in format "HH:MM-HH:MM ET"
blackout_periods = [
    "09:30-09:45",  # Market open volatility
    "15:45-16:00"   # Market close volatility
]
```

---

## Examples

### Example 1: Basic Stop-Loss Trade

```rust
use common::types::*;

// Create order with default stop-loss (2%)
let order = OrderBuilder::new()
    .symbol("AAPL")
    .limit_order(150.00)
    .quantity(100)
    .with_stop_loss(2.0) // 2% below entry
    .build();

// Entry: $150.00
// Stop-loss: $147.00 (2% below)
// Max loss: $300 (100 shares × $3)

// Verify stop-loss
assert_eq!(order.stop_loss_price, Some(147.00));
assert_eq!(order.max_loss(), 300.00);
```

### Example 2: Trailing Stop-Loss

```rust
// Create position with trailing stop
let mut position = Position {
    symbol: "TSLA".to_string(),
    entry_price: 200.00,
    quantity: 50,
    trailing_stop_enabled: true,
    trailing_stop_percent: 1.5,
    trailing_activation_percent: 2.0,
    highest_price: 200.00,
    stop_loss_price: 196.00, // Initial: 2% below
    // ...
};

// Price moves to $204.00 (2% profit)
position.update_price(204.00);
// Trailing stop activates at $200.94 (1.5% below $204)
assert_eq!(position.stop_loss_price, 200.94);

// Price moves to $210.00
position.update_price(210.00);
// Trailing stop moves to $206.85 (1.5% below $210)
assert_eq!(position.stop_loss_price, 206.85);

// Price falls to $206.85
position.update_price(206.85);
// STOP HIT → Market sell triggered
assert!(position.should_trigger_stop());
```

### Example 3: Partial Profit Taking

```rust
// Create position with partial profit targets
let mut position = Position {
    symbol: "NVDA".to_string(),
    entry_price: 500.00,
    quantity: 200,
    partial_profit_enabled: true,
    first_target_percent: 3.0,   // $515.00
    second_target_percent: 5.0,  // $525.00
    partial_profit_percent: 50.0, // 50% at first target
    // ...
};

// Price reaches $515.00 (first target)
if position.current_price >= position.first_target_price() {
    let shares_to_sell = position.quantity * 0.5; // 100 shares
    position.close_partial(shares_to_sell);
    position.move_stop_to_breakeven(); // Move stop to $500.00
}

// Price reaches $525.00 (second target)
if position.current_price >= position.second_target_price() {
    position.close_remaining(); // Sell remaining 100 shares
}
```

### Example 4: Volatility-Based Sizing

```rust
fn calculate_position_size(
    account_risk: f64,
    price: f64,
    stop_loss_percent: f64,
    current_volatility: f64,
    base_volatility: f64,
) -> i32 {
    // Base position size
    let base_shares = account_risk / (stop_loss_percent * price);

    // Adjust for volatility
    let volatility_ratio = base_volatility / current_volatility;
    let adjusted_shares = base_shares * volatility_ratio;

    // Round down to whole shares
    adjusted_shares.floor() as i32
}

// Example usage
let account_risk = 1000.0;  // Risk $1,000 per trade
let price = 100.0;
let stop_loss = 0.02;       // 2%
let current_vol = 4.0;      // 4% ATR (high volatility)
let base_vol = 2.0;         // 2% base

let shares = calculate_position_size(
    account_risk,
    price,
    stop_loss,
    current_vol,
    base_vol,
);

// Result: 250 shares (reduced from 500 due to high volatility)
assert_eq!(shares, 250);
```

### Example 5: Circuit Breaker Recovery

```rust
// Monitor daily P&L
let mut daily_pnl = -4500.0; // Current losses
let max_daily_loss = -5000.0;

// Check for circuit breaker conditions
fn check_circuit_breaker(
    daily_pnl: f64,
    max_loss: f64,
    consecutive_losses: usize,
) -> Option<CircuitBreakerReason> {
    if daily_pnl <= max_loss {
        return Some(CircuitBreakerReason::DailyLossLimit);
    }

    if consecutive_losses >= 5 {
        return Some(CircuitBreakerReason::ConsecutiveLosses);
    }

    None
}

// Trade results in additional loss
daily_pnl -= 600.0; // Now -$5,100

if let Some(reason) = check_circuit_breaker(daily_pnl, max_daily_loss, 3) {
    println!("Circuit breaker triggered: {:?}", reason);

    // Actions:
    // 1. Cancel all pending orders
    cancel_all_orders();

    // 2. Disable new order submission
    set_trading_enabled(false);

    // 3. Send notification
    notify_admin(format!("Circuit breaker: {:?}", reason));

    // 4. Enter cooldown
    start_cooldown(Duration::minutes(60));
}
```

---

## Best Practices

### 1. Always Use Stop-Losses

**❌ Bad:**
```rust
let order = OrderBuilder::new()
    .symbol("AAPL")
    .limit_order(150.00)
    .quantity(100)
    .build(); // No stop-loss!
```

**✅ Good:**
```rust
let order = OrderBuilder::new()
    .symbol("AAPL")
    .limit_order(150.00)
    .quantity(100)
    .with_stop_loss(2.0) // 2% stop-loss
    .build();
```

### 2. Size Positions Based on Risk

**❌ Bad:**
```rust
// Always buy 1000 shares regardless of price or volatility
let quantity = 1000;
```

**✅ Good:**
```rust
// Calculate position size based on risk tolerance
let max_risk = 1000.0; // $1,000 max loss
let stop_distance = 0.02; // 2%
let price = 100.0;

let quantity = (max_risk / (stop_distance * price)) as i32;
// Result: 500 shares
```

### 3. Respect Circuit Breakers

**❌ Bad:**
```rust
// Force trading even when circuit breaker is active
if circuit_breaker.is_active() {
    circuit_breaker.override_and_resume(); // DANGEROUS!
}
```

**✅ Good:**
```rust
// Wait for cooldown and review before resuming
if circuit_breaker.is_active() {
    log::warn!("Circuit breaker active, waiting for cooldown...");
    return Err("Trading suspended due to risk limits");
}

// Manual review required before resume
```

### 4. Monitor Correlation

**❌ Bad:**
```rust
// Open multiple highly correlated positions
buy("AAPL", 100);
buy("MSFT", 100); // 0.85 correlation
buy("GOOGL", 100); // 0.78 correlation
// Too much tech sector exposure!
```

**✅ Good:**
```rust
// Check correlation before opening new position
let existing = vec!["AAPL"];
let correlation = calculate_correlation("MSFT", &existing);

if correlation > 0.7 {
    log::warn!("High correlation detected: {}", correlation);
    return Err("Position would exceed correlation limit");
}
```

### 5. Use Partial Profit Taking

**❌ Bad:**
```rust
// All-or-nothing approach
if price >= target {
    sell_all(); // Miss out if reverses before full target
}
```

**✅ Good:**
```rust
// Scale out at multiple targets
if price >= first_target {
    sell_partial(50%); // Take half off
    move_stop_to_breakeven(); // Protect remaining
}

if price >= second_target {
    sell_remaining(); // Exit completely
}
```

---

## Troubleshooting

### Stop-Loss Not Triggering

**Symptoms:**
- Position continues to lose money beyond stop-loss level
- No sell order generated when price hits stop

**Diagnosis:**
```bash
# Check stop-loss configuration
cat config/risk_limits.toml | grep -A 10 "\[stop_loss\]"

# Check stop manager logs
tail -f logs/risk_manager/stop_manager.log

# Verify position has stop-loss set
curl http://localhost:8000/api/positions/AAPL | jq '.stop_loss_price'
```

**Solutions:**

1. **Verify stop-loss is enabled:**
```toml
[stop_loss]
default_stop_loss_percent = 2.0  # Must be > 0
```

2. **Check position creation:**
```rust
// Ensure stop-loss is set when opening position
let position = Position {
    stop_loss_price: Some(entry_price * 0.98), // 2% below
    // ...
};
```

3. **Monitor stop manager:**
```rust
// Ensure stop manager is running
let stop_manager = StopManager::new(config);
stop_manager.check_all_positions(); // Should run continuously
```

### Circuit Breaker False Triggers

**Symptoms:**
- Circuit breaker activates unexpectedly
- Trading halted during normal operations

**Diagnosis:**
```bash
# Check circuit breaker status
curl http://localhost:8000/api/system/circuit-breaker/status

# Review recent trades
curl http://localhost:8000/api/trades/history?limit=10

# Check daily P&L
curl http://localhost:8000/api/trades/pnl?period=today
```

**Solutions:**

1. **Adjust thresholds:**
```toml
[circuit_breaker]
daily_loss_threshold = 7500.0  # Increase from 5000
max_consecutive_losses = 7     # Increase from 5
```

2. **Enable auto-resume (with caution):**
```toml
[circuit_breaker]
auto_resume = true  # Resume after cooldown
cooldown_minutes = 30  # Reduce cooldown
```

3. **Review trading strategy:**
```bash
# Analyze why consecutive losses occurred
python3 scripts/analyze_trades.py --period=today --focus=losses
```

### Position Size Too Large/Small

**Symptoms:**
- Orders rejected due to size limits
- Positions not filling completely

**Diagnosis:**
```bash
# Check position limits
cat config/risk_limits.toml | grep -A 5 "\[position_limits\]"

# Review recent order rejections
tail -f logs/risk_manager/rejections.log

# Check calculated position size
curl http://localhost:8000/api/risk/calculate-size?symbol=AAPL&risk=1000
```

**Solutions:**

1. **Adjust position limits:**
```toml
[position_limits]
max_shares = 2000  # Increase from 1000
max_notional_per_position = 20000.0  # Increase from 10000
```

2. **Fix volatility scaling:**
```toml
[volatility]
enable_volatility_scaling = false  # Disable if too aggressive
base_volatility_percent = 3.0  # Adjust base volatility
```

3. **Review order validation:**
```toml
[order_validation]
max_order_size = 2000  # Must be >= max_shares
max_order_value = 20000.0  # Must be >= max_notional
```

---

## API Reference

### Risk Check Endpoint

```bash
POST /api/risk/check-order
Content-Type: application/json

{
  "symbol": "AAPL",
  "side": "buy",
  "quantity": 100,
  "price": 150.00
}

Response:
{
  "approved": true,
  "reason": null,
  "max_quantity": 500,
  "position_size_after": 100,
  "total_exposure_after": 15000.00
}
```

### Position Query

```bash
GET /api/positions/AAPL

Response:
{
  "symbol": "AAPL",
  "quantity": 100,
  "entry_price": 150.00,
  "current_price": 155.00,
  "unrealized_pnl": 500.00,
  "stop_loss_price": 147.00,
  "trailing_stop_enabled": true,
  "highest_price": 156.50
}
```

### Circuit Breaker Status

```bash
GET /api/system/circuit-breaker/status

Response:
{
  "active": false,
  "reason": null,
  "triggered_at": null,
  "cooldown_remaining": 0,
  "daily_pnl": -2500.00,
  "daily_loss_limit": -5000.00,
  "consecutive_losses": 2,
  "max_consecutive_losses": 5,
  "trades_today": 15,
  "max_trades_per_day": 50
}
```

---

## Monitoring

### Key Metrics

Monitor these metrics in the observability dashboard:

1. **Daily P&L:** Track against daily loss limit
2. **Consecutive Losses:** Alert when approaching circuit breaker threshold
3. **Position Concentration:** Ensure diversification
4. **Stop-Loss Distance:** Monitor distance from current price
5. **Circuit Breaker Status:** Alert when activated

### Alerts

Configure alerts for:

```yaml
# config/alerts.yaml
alerts:
  - name: "Daily Loss Warning"
    condition: "daily_pnl < -4000"
    severity: "warning"

  - name: "Daily Loss Critical"
    condition: "daily_pnl < -4500"
    severity: "critical"

  - name: "Circuit Breaker Imminent"
    condition: "consecutive_losses >= 4"
    severity: "warning"

  - name: "Circuit Breaker Activated"
    condition: "circuit_breaker_active == true"
    severity: "critical"
```

---

## Summary

The risk management system provides comprehensive protection through:

✅ **Stop-Loss Management:** Static and trailing stops
✅ **Position Sizing:** Volatility-adjusted sizing
✅ **Circuit Breakers:** Automatic trading suspension
✅ **Loss Limits:** Multi-level loss controls
✅ **Correlation Limits:** Portfolio diversification
✅ **Time Restrictions:** Market hours enforcement

**Always test risk settings in paper trading before live deployment!**

For more information, see:
- `config/risk_limits.toml` - Risk configuration
- `docs/API_DOCUMENTATION.md` - API reference
- `docs/OBSERVABILITY_INTEGRATION.md` - Monitoring guide
