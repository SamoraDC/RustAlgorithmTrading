# Stop-Loss Risk Management Implementation

## Overview

This document describes the comprehensive stop-loss risk management system implemented in the Rust algorithmic trading platform. The system provides multiple stop-loss strategies to protect trading positions from excessive losses.

## Features

### 1. Stop-Loss Types

#### Static Stop-Loss
- Fixed percentage loss threshold from entry price
- Set at position entry and remains constant
- Best for: Conservative risk management with predictable max loss

**Example:**
```rust
use risk_manager::{StopLossConfig, StopManager};

let config = StopLossConfig::static_stop(5.0)?; // 5% stop-loss
manager.set_stop(&position, config)?;
```

#### Trailing Stop-Loss
- Follows price movements in profitable direction
- Locks in profits as price moves favorably
- Automatically adjusts stop level
- Best for: Trend-following strategies, profit protection

**Example:**
```rust
let config = StopLossConfig::trailing_stop(3.0)?; // 3% trailing stop
manager.set_stop(&position, config)?;
```

**Behavior:**
- **Long positions**: Stop trails upward as price increases
- **Short positions**: Stop trails downward as price decreases
- Stop level never moves against the position

#### Absolute Stop-Loss
- Fixed price level regardless of entry
- Support/resistance based stops
- Best for: Technical analysis-based trading

**Example:**
```rust
use common::types::Price;

let config = StopLossConfig::absolute_stop(Price(48000.0))?;
manager.set_stop(&position, config)?;
```

### 2. Maximum Loss Value Constraint

All stop types support an additional absolute value constraint:

```rust
let config = StopLossConfig::static_stop(10.0)?
    .with_max_loss(2000.0)?; // Max $2000 loss

manager.set_stop(&position, config)?;
```

This triggers stop-loss if either:
- Price-based stop is hit, OR
- Absolute dollar loss exceeds threshold

## Architecture

### Core Components

#### StopLossConfig
Configuration for stop-loss behavior:
```rust
pub struct StopLossConfig {
    pub stop_type: StopLossType,
    pub percentage: Option<f64>,
    pub price_level: Option<Price>,
    pub max_loss_value: Option<f64>,
}
```

#### StopManager
Main stop-loss management engine:
```rust
pub struct StopManager {
    config: RiskConfig,
    stops: HashMap<String, StopLossState>,
    triggered_stops: Vec<(Symbol, String)>,
}
```

**Key Methods:**
- `set_stop()`: Configure stop for a position
- `check()`: Evaluate position against stop rules
- `remove_stop()`: Remove stop configuration
- `get_active_stops()`: View all active stops

#### StopLossTrigger
Event emitted when stop is triggered:
```rust
pub struct StopLossTrigger {
    pub symbol: Symbol,
    pub position: Position,
    pub trigger_price: Price,
    pub current_price: Price,
    pub unrealized_pnl: f64,
    pub stop_type: StopLossType,
    pub reason: String,
}
```

**Helper Methods:**
- `close_quantity()`: Returns position quantity to close
- `close_side()`: Returns opposite side for closing order

### Integration with Risk Manager

```rust
pub struct RiskManagerService {
    stop_manager: StopManager,
    // ... other components
}

impl RiskManagerService {
    pub fn update_position(&mut self, position: Position) -> Option<StopLossTrigger> {
        // Returns trigger if stop-loss activated
        self.stop_manager.check(&position)
    }

    pub fn set_stop_loss(&mut self, position: &Position, config: StopLossConfig) -> Result<()> {
        self.stop_manager.set_stop(position, config)
    }
}
```

### Execution Integration

#### StopLossExecutor
Handles creation and execution of stop-loss orders:

```rust
pub struct StopLossExecutor {
    use_market_orders: bool,
    slippage_tolerance: f64,
}
```

**Features:**
- Market orders for immediate execution
- Limit orders with configurable slippage tolerance
- Automatic order creation from triggers
- Validation and error handling

**Example Usage:**
```rust
use execution_engine::StopLossExecutor;

let executor = StopLossExecutor::new(false, 0.5); // Limit orders, 0.5% slippage

if let Some(trigger) = risk_manager.update_position(position) {
    let close_order = executor.create_stop_loss_order(
        trigger.symbol,
        trigger.close_side(),
        trigger.close_quantity(),
        trigger.current_price,
        trigger.trigger_price,
    )?;

    executor.execute_stop_order(close_order).await?;
}
```

## Usage Examples

### Basic Setup

```rust
use risk_manager::{RiskManagerService, StopLossConfig};
use common::config::RiskConfig;

// Initialize risk manager with default stops from config
let config = RiskConfig {
    stop_loss_percent: 5.0,      // Default 5% static stop
    trailing_stop_percent: 3.0,  // Available for trailing
    // ... other config
};

let mut risk_manager = RiskManagerService::new(config)?;
```

### Auto-Configuration

If no explicit stop is set, the system auto-configures based on `RiskConfig`:

```rust
// First position update auto-configures stop
let trigger = risk_manager.update_position(position);

// Stop is now active using config.stop_loss_percent
```

### Custom Stop Configuration

```rust
// Long position with 5% static stop and $1000 max loss
let long_position = create_long_position(symbol, 50000.0, 1.0);

let config = StopLossConfig::static_stop(5.0)?
    .with_max_loss(1000.0)?;

risk_manager.set_stop_loss(&long_position, config)?;

// Check on price updates
if let Some(trigger) = risk_manager.update_position(updated_position) {
    println!("Stop triggered: {}", trigger.reason);
    // Execute closing order
}
```

### Trailing Stop Example

```rust
// Trailing stop that locks in profits
let config = StopLossConfig::trailing_stop(3.0)?;
risk_manager.set_stop_loss(&position, config)?;

// As price moves favorably, stop trails automatically
// Price goes from $50k -> $52k, stop moves from $48.5k -> $50.44k
```

### Multi-Asset Management

```rust
// Different stops for different assets
for position in positions {
    let config = match position.symbol.0.as_str() {
        "BTCUSDT" => StopLossConfig::trailing_stop(3.0)?,
        "ETHUSDT" => StopLossConfig::static_stop(5.0)?,
        _ => StopLossConfig::static_stop(7.0)?,
    };

    risk_manager.set_stop_loss(&position, config)?;
}
```

## Logging and Monitoring

### Log Levels

**INFO**: Configuration and state changes
```
Stop-loss set for BTCUSDT: type=Static, trigger_price=47500.00000000, entry_price=50000.00000000
```

**DEBUG**: Trailing stop updates
```
Trailing stop updated: 48500.0 -> 50440.0
```

**WARN**: Stop-loss triggers
```
STOP-LOSS TRIGGERED for BTCUSDT: Static stop triggered at 47500.00000000 (current: 47450.00000000)
```

### Monitoring Active Stops

```rust
// View all active stops
let active = risk_manager.stop_manager().get_active_stops();

for (symbol, state) in active {
    println!("{}: trigger at {:.2}", symbol, state.trigger_price.0);
}

// Check if position has stop
if risk_manager.stop_manager().has_stop(&symbol) {
    println!("Stop configured for {}", symbol.0);
}
```

## Error Handling

All operations use `Result<T>` types:

```rust
// Configuration errors
match StopLossConfig::static_stop(150.0) {
    Ok(_) => unreachable!(),
    Err(TradingError::Configuration(msg)) => {
        // Handle: "Stop-loss percentage must be between 0 and 100"
    }
}

// Set stop errors
match risk_manager.set_stop_loss(&position, config) {
    Ok(_) => println!("Stop configured"),
    Err(e) => eprintln!("Failed to set stop: {}", e),
}
```

## Testing

Comprehensive test coverage includes:

### Unit Tests
- Static stop-loss for long/short positions
- Trailing stop behavior
- Absolute price stops
- Maximum loss value enforcement
- Auto-configuration
- Invalid configuration handling
- Stop removal

### Running Tests
```bash
cd rust/risk-manager
cargo test stops

# Run with output
cargo test stops -- --nocapture

# Run specific test
cargo test test_trailing_stop_follows_price_up
```

### Test Coverage
```bash
# Install tarpaulin
cargo install cargo-tarpaulin

# Generate coverage
cargo tarpaulin --out Html --output-dir target/coverage
```

## Performance Considerations

### Complexity
- `check()`: O(1) - HashMap lookup
- `set_stop()`: O(1) - HashMap insertion
- `update()`: O(1) - Price comparison and arithmetic

### Memory
- Per-position overhead: ~200 bytes (StopLossState)
- 10,000 positions: ~2 MB

### Optimization Tips
1. **Batch Updates**: Group position updates
2. **Remove Closed Positions**: Call `remove_stop()` when positions close
3. **Clear Triggered**: Call `clear_triggered()` after processing

## Best Practices

### 1. Always Set Stops
```rust
// Bad: No stop protection
risk_manager.update_position(position);

// Good: Explicit stop configuration
risk_manager.set_stop_loss(&position, config)?;
risk_manager.update_position(position);
```

### 2. Handle Triggers Immediately
```rust
if let Some(trigger) = risk_manager.update_position(position) {
    // Create and execute closing order immediately
    let order = executor.create_stop_loss_order(
        trigger.symbol,
        trigger.close_side(),
        trigger.close_quantity(),
        trigger.current_price,
        trigger.trigger_price,
    )?;

    executor.execute_stop_order(order).await?;
}
```

### 3. Use Appropriate Stop Type
- **Static**: Conservative, predictable loss limits
- **Trailing**: Trend-following, profit protection
- **Absolute**: Technical levels, support/resistance

### 4. Configure Slippage Tolerance
```rust
// Market orders: Fast but unpredictable execution
let executor = StopLossExecutor::new(true, 0.0);

// Limit orders: Controlled slippage but may not fill
let executor = StopLossExecutor::new(false, 0.5);
```

### 5. Log All Triggers
```rust
use tracing::warn;

if let Some(trigger) = risk_manager.update_position(position) {
    warn!(
        "Stop-loss triggered: {} - {} - P&L: ${:.2}",
        trigger.symbol.0,
        trigger.reason,
        trigger.unrealized_pnl
    );

    // Execute closure
}
```

## Integration Checklist

- [ ] Configure `RiskConfig` with default stop percentages
- [ ] Initialize `RiskManagerService` in main application
- [ ] Create `StopLossExecutor` with execution preferences
- [ ] Set stop-loss on all new positions
- [ ] Check positions on every price update
- [ ] Handle `StopLossTrigger` events with order execution
- [ ] Log all stop-loss activity
- [ ] Monitor triggered stops in production
- [ ] Set up alerts for frequent stop triggers
- [ ] Review and adjust stop parameters based on strategy performance

## Configuration Reference

### RiskConfig Parameters
```rust
pub struct RiskConfig {
    pub stop_loss_percent: f64,        // Default static stop (0-100)
    pub trailing_stop_percent: f64,    // Default trailing stop (0-100)
    pub max_loss_threshold: f64,       // Maximum total loss before circuit breaker
    // ... other risk parameters
}
```

### StopLossExecutor Parameters
```rust
pub struct StopLossExecutor {
    pub use_market_orders: bool,       // true = market, false = limit
    pub slippage_tolerance: f64,       // Percentage for limit orders (0-100)
}
```

## Future Enhancements

Potential improvements for future versions:

1. **Time-based stops**: Activate after holding period
2. **Volatility-adjusted stops**: Dynamic based on ATR/volatility
3. **Partial stops**: Close portion of position at different levels
4. **Stop-loss laddering**: Multiple stop levels
5. **Cooldown periods**: Prevent re-entry after stop
6. **Historical analysis**: Track stop-loss effectiveness
7. **Machine learning**: Optimize stop parameters

## Support and Issues

For questions or issues:
- Check logs with `RUST_LOG=debug`
- Review test cases in `rust/risk-manager/src/stops.rs`
- Verify configuration in `RiskConfig`
- Ensure proper error handling

## License

MIT License - See LICENSE file for details
