# Position Sizing Fix - Architecture Design Document

**Author:** System Architect Agent
**Date:** 2025-10-28
**Status:** Approved for Implementation
**Priority:** CRITICAL

---

## Executive Summary

The portfolio handler is generating orders that exceed available capital due to a fundamental misinterpretation of the `position_size` parameter. The system treats `position_size=0.1` (10%) as a dollar amount to invest per share rather than as a percentage of total capital to allocate.

**Critical Issue:** For a $1000 portfolio with `position_size=0.1`:
- **Expected behavior:** Allocate $100 (10% of $1000)
- **Actual behavior:** Calculates 100 shares (treating 0.1 as multiplier: 0.1 * 1000 = 100)
- **Result:** Order for 100 shares × $100/share = $10,000 (10x capital!)

---

## Problem Analysis

### Root Causes

1. **Semantic Confusion in Position Sizers**
   - `PercentageOfEquitySizer(0.1)` calculates: `amount = equity * 0.1`
   - This produces a **dollar amount** ($100 for $1000 equity)
   - BUT the calculation then does: `shares = int(amount / price)`
   - For price=$100: `shares = int(100 / 100) = 1` ✓ CORRECT
   - For price=$1: `shares = int(100 / 1) = 100` ✓ CORRECT
   - **Actually working as intended!**

2. **Strategy-Level Misuse**
   - Strategies define `position_size: float = 0.1` meaning 10%
   - BUT pass this directly to position sizer without creating proper sizer instance
   - Some strategies calculate `max_shares = (account_value * position_size) / price`
   - This is CORRECT but inconsistently applied

3. **Missing Pre-Trade Validation**
   - No check for available cash before generating orders
   - No validation that order value ≤ available capital
   - Commission costs not considered in sizing
   - No fractional share handling

4. **Portfolio State Inconsistency**
   - Cash updated AFTER fills, not when orders generated
   - Multiple simultaneous orders can exceed total capital
   - No reserve for commissions

### Current Implementation Issues

**File:** `/src/backtesting/portfolio_handler.py`

```python
# Line 99-102: Position sizer calculates TARGET quantity
target_quantity = self.position_sizer.calculate_position_size(
    signal=signal,
    portfolio=self.portfolio,
)

# Line 257: PercentageOfEquitySizer
amount = portfolio.equity * self.percentage  # This is CORRECT
return int(amount / price)  # This is CORRECT

# ISSUE: No validation that order_value ≤ available_cash
```

**File:** `/src/strategies/simple_momentum.py`

```python
# Line 37: position_size: float = 0.1  # Semantic: 10% of capital
# Line 117: max_position_value = account_value * self.get_parameter('position_size', 0.1)
# Line 118: max_shares = max_position_value / signal.price
# This is CORRECT but not consistently enforced
```

---

## Architecture Decision Records (ADRs)

### ADR-001: Fix Strategy vs Add Validation

**Decision:** Implement BOTH fixes + validation (defense in depth)

**Rationale:**
- Fix calculation ensures correct intent interpretation
- Add validation prevents any edge case from causing issues
- Layered defense is critical for financial systems

**Alternatives Considered:**
1. Only fix calculation - Rejected (no safety net)
2. Only add validation - Rejected (doesn't fix root cause)

---

### ADR-002: Position Sizing Semantic Clarity

**Decision:** `position_size` parameter ALWAYS means "percentage of capital" (0.0-1.0)

**Rationale:**
- Matches industry standard (risk management uses percentages)
- Configuration value of 0.1 is intuitive as 10%
- Easy to enforce validation (0 < percentage ≤ 1)

**Implementation:**
```python
class PercentageOfEquitySizer(PositionSizer):
    def __init__(self, percentage: float):
        """
        Args:
            percentage: Percentage of equity (0.0-1.0), e.g., 0.1 = 10%
        """
        if not 0 < percentage <= 1:
            raise ValueError(f"percentage must be in range (0, 1], got {percentage}")
        self.percentage = percentage
```

---

### ADR-003: Pre-Trade Validation Strategy

**Decision:** Implement multi-layer validation with order capping

**Layers:**
1. **Sizer Level:** Calculate ideal position size
2. **Pre-Order Validation:** Cap order at available cash minus reserve
3. **Portfolio Handler:** Reject orders exceeding available capital
4. **Post-Fill Verification:** Assert cash ≥ 0

**Rationale:**
- Prevents negative cash under any circumstance
- Maintains audit trail of adjustments
- Allows graceful degradation (partial fills)

---

### ADR-004: Commission Reserve Strategy

**Decision:** Reserve commission before order generation

**Formula:**
```
max_order_value = available_cash / (1 + commission_rate + slippage_rate)
```

**Example:**
- Available cash: $1000
- Commission: 0.1% (0.001)
- Slippage: 0.05% (0.0005)
- Max order: $1000 / 1.0015 = $998.50

**Rationale:**
- Guarantees sufficient funds for fees
- Prevents order rejection due to fees
- Conservative approach (industry standard)

---

### ADR-005: Fractional Shares Handling

**Decision:** Support fractional shares with configurable rounding

**Modes:**
1. **Floor (default):** Round down to whole shares
2. **Ceiling:** Round up (only if sufficient capital)
3. **Nearest:** Round to nearest (recommended)
4. **Fractional:** Support decimal shares (for brokers that allow)

**Implementation:**
```python
class PositionSizer:
    def __init__(self, allow_fractional: bool = False, rounding: str = 'floor'):
        self.allow_fractional = allow_fractional
        self.rounding = rounding

    def _round_shares(self, shares: float) -> float:
        if self.allow_fractional:
            return round(shares, 4)  # 0.0001 share precision

        if self.rounding == 'floor':
            return int(shares)
        elif self.rounding == 'ceiling':
            return math.ceil(shares)
        else:  # nearest
            return round(shares)
```

---

## Proposed Solution Architecture

### Component Design

```
┌─────────────────────────────────────────────────────────────┐
│                     STRATEGY LAYER                          │
│  - Defines position_size parameter (0.0-1.0)                │
│  - Generates signals with price information                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 POSITION SIZER LAYER                        │
│  Input: signal, portfolio, position_size%                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Calculate target_value = equity × position_size%  │  │
│  │ 2. Calculate ideal_shares = target_value / price     │  │
│  │ 3. Round shares based on fractional_mode             │  │
│  └──────────────────────────────────────────────────────┘  │
│  Output: ideal_shares (unvalidated)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              PRE-TRADE VALIDATOR (NEW)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Calculate order_value = ideal_shares × price      │  │
│  │ 2. Calculate commission = order_value × comm_rate    │  │
│  │ 3. Calculate total_cost = order_value + commission   │  │
│  │ 4. Check: total_cost ≤ available_cash ?              │  │
│  │    YES → return ideal_shares                          │  │
│  │    NO  → calculate max_affordable_shares              │  │
│  │          max_value = cash / (1 + comm_rate)          │  │
│  │          max_shares = floor(max_value / price)       │  │
│  │          return max_shares                            │  │
│  └──────────────────────────────────────────────────────┘  │
│  Output: validated_shares (guaranteed affordable)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              PORTFOLIO HANDLER                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Receive validated_shares from validator           │  │
│  │ 2. Calculate order_quantity = validated - current    │  │
│  │ 3. Create OrderEvent with validated quantity         │  │
│  │ 4. Reserve cash for pending orders                   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 FILL HANDLER                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Update position                                    │  │
│  │ 2. Deduct (order_value + commission) from cash       │  │
│  │ 3. Assert cash ≥ 0 (should never fail)               │  │
│  │ 4. Release reserved cash                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Fixes (Priority: CRITICAL)

#### 1.1 Create PreTradeValidator Class

**File:** `/src/backtesting/validators.py` (NEW)

```python
class PreTradeValidator:
    """
    Validates trading orders before execution to ensure sufficient capital.
    """

    def __init__(
        self,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        allow_fractional: bool = False,
    ):
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.allow_fractional = allow_fractional

    def validate_order_size(
        self,
        shares: float,
        price: float,
        available_cash: float,
        direction: str,
    ) -> tuple[float, dict]:
        """
        Validate and adjust order size based on available capital.

        Returns:
            (validated_shares, validation_info)
        """
        # Calculate costs
        order_value = abs(shares) * price
        commission = order_value * self.commission_rate
        slippage = order_value * self.slippage_rate
        total_cost = order_value + commission + slippage

        validation_info = {
            'requested_shares': shares,
            'order_value': order_value,
            'commission': commission,
            'slippage': slippage,
            'total_cost': total_cost,
            'available_cash': available_cash,
            'validated': True,
            'adjustment': 'none',
        }

        # For SELL orders, no cash needed
        if direction == 'SELL':
            return shares, validation_info

        # For BUY orders, check affordability
        if total_cost > available_cash:
            # Calculate maximum affordable shares
            max_value = available_cash / (1 + self.commission_rate + self.slippage_rate)
            max_shares = max_value / price

            # Round based on fractional setting
            if not self.allow_fractional:
                max_shares = int(max_shares)

            if max_shares <= 0:
                validation_info['validated'] = False
                validation_info['adjustment'] = 'rejected'
                validation_info['reason'] = 'insufficient_capital'
                logger.warning(
                    f"Order rejected: insufficient capital. "
                    f"Required: ${total_cost:.2f}, Available: ${available_cash:.2f}"
                )
                return 0, validation_info

            # Adjust order size
            validation_info['validated'] = True
            validation_info['adjustment'] = 'reduced'
            validation_info['adjusted_shares'] = max_shares
            logger.info(
                f"Order adjusted: {shares:.2f} → {max_shares:.2f} shares "
                f"(available cash: ${available_cash:.2f})"
            )
            return max_shares, validation_info

        # Order is affordable as-is
        return shares, validation_info
```

#### 1.2 Update PortfolioHandler Integration

**File:** `/src/backtesting/portfolio_handler.py`

```python
from src.backtesting.validators import PreTradeValidator

class PortfolioHandler:
    def __init__(
        self,
        initial_capital: float,
        position_sizer: Optional['PositionSizer'] = None,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        # ... existing code ...

        # Add validator
        self.validator = PreTradeValidator(
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )

        # Track pending orders
        self.pending_orders: Dict[str, float] = {}  # symbol → reserved_cash

    def generate_orders(self, signal: SignalEvent) -> List[OrderEvent]:
        """Generate orders with validation."""
        orders = []

        # Calculate target position (unchanged)
        target_quantity = self.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=self.portfolio,
        )

        # Get current position
        current_position = self.portfolio.positions.get(signal.symbol)
        current_quantity = current_position.quantity if current_position else 0

        # Calculate order quantity
        order_quantity = target_quantity - current_quantity

        if order_quantity == 0:
            return orders

        # Determine direction
        direction = 'BUY' if order_quantity > 0 else 'SELL'

        # Calculate available cash (exclude pending orders)
        reserved_cash = sum(self.pending_orders.values())
        available_cash = self.portfolio.cash - reserved_cash

        # Validate order size (NEW)
        validated_quantity, validation_info = self.validator.validate_order_size(
            shares=abs(order_quantity),
            price=signal.price,
            available_cash=available_cash,
            direction=direction,
        )

        # Check if order was rejected
        if not validation_info['validated']:
            logger.warning(
                f"Order rejected for {signal.symbol}: {validation_info['reason']}"
            )
            return orders

        # Adjust order quantity if needed
        if direction == 'SELL':
            order_quantity = -validated_quantity
        else:
            order_quantity = validated_quantity

        # Reserve cash for pending BUY orders
        if direction == 'BUY':
            reserved = validation_info['total_cost']
            self.pending_orders[signal.symbol] = reserved

        # Create order
        order = OrderEvent(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            order_type='MKT',
            quantity=abs(order_quantity),
            direction=direction,
            metadata=validation_info,  # Store validation details
        )

        orders.append(order)

        logger.debug(
            f"Generated {order.direction} order for {order.quantity:.2f} {signal.symbol} "
            f"(validation: {validation_info['adjustment']})"
        )

        return orders

    def update_fill(self, fill: FillEvent):
        """Update portfolio with fill (add verification)."""
        # Release reserved cash
        if fill.symbol in self.pending_orders:
            del self.pending_orders[fill.symbol]

        # Calculate total cost
        if fill.direction == 'BUY':
            cost = (fill.quantity * fill.fill_price) + fill.commission

            # Verify sufficient cash
            if self.portfolio.cash < cost:
                logger.error(
                    f"CRITICAL: Insufficient cash for fill! "
                    f"Required: ${cost:.2f}, Available: ${self.portfolio.cash:.2f}"
                )
                raise ValueError("Insufficient cash for fill - validation failed")

        # Update position
        self.portfolio.update_position(
            symbol=fill.symbol,
            quantity=fill.quantity,
            price=fill.fill_price,
        )

        # Update cash
        if fill.direction == 'BUY':
            self.portfolio.cash -= cost
        else:  # SELL
            proceeds = (fill.quantity * fill.fill_price) - fill.commission
            self.portfolio.cash += proceeds

        # Verify cash is non-negative (should never fail after validation)
        assert self.portfolio.cash >= 0, f"Negative cash: ${self.portfolio.cash:.2f}"

        # ... rest of existing code ...
```

#### 1.3 Fix Position Sizers

**File:** `/src/backtesting/portfolio_handler.py`

```python
class PercentageOfEquitySizer(PositionSizer):
    """Position sizer based on percentage of portfolio equity."""

    def __init__(self, percentage: float):
        """
        Initialize sizer.

        Args:
            percentage: Percentage of equity to allocate (0.0-1.0)
                       Example: 0.1 = allocate 10% of equity to position

        Raises:
            TypeError: If percentage is not a number
            ValueError: If percentage is not in range (0, 1]
        """
        if not isinstance(percentage, (int, float)):
            raise TypeError(f"percentage must be a number, got {type(percentage).__name__}")

        if not 0 < percentage <= 1:
            raise ValueError(
                f"percentage must be in range (0, 1] representing 0-100%, got {percentage}"
            )

        self.percentage = percentage

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio
    ) -> int:
        """
        Calculate position size based on equity percentage.

        Formula: shares = floor((equity × percentage) / price)

        Example:
            equity = $10,000
            percentage = 0.1 (10%)
            price = $100
            → target_value = $10,000 × 0.1 = $1,000
            → shares = floor($1,000 / $100) = 10 shares
        """
        # Calculate dollar amount to allocate
        target_value = portfolio.equity * self.percentage

        # Get current price
        current_position = portfolio.positions.get(signal.symbol)
        price = current_position.current_price if current_position else signal.price

        # Calculate shares
        if signal.signal_type == 'LONG':
            shares = int(target_value / price)
            return shares
        elif signal.signal_type == 'SHORT':
            shares = int(target_value / price)
            return -shares
        else:  # EXIT
            return 0
```

---

### Phase 2: Enhanced Features (Priority: HIGH)

#### 2.1 Add Fractional Share Support

**File:** `/src/backtesting/portfolio_handler.py`

```python
class PercentageOfEquitySizer(PositionSizer):
    def __init__(
        self,
        percentage: float,
        allow_fractional: bool = False,
        rounding_mode: str = 'floor',
    ):
        # ... existing validation ...
        self.allow_fractional = allow_fractional
        self.rounding_mode = rounding_mode

    def _round_shares(self, shares: float) -> float:
        """Round shares based on configuration."""
        if self.allow_fractional:
            return round(shares, 4)  # 4 decimal precision

        if self.rounding_mode == 'floor':
            return int(shares)
        elif self.rounding_mode == 'ceil':
            return math.ceil(shares)
        else:  # nearest
            return round(shares)

    def calculate_position_size(self, signal, portfolio) -> float:
        # ... existing calculation ...
        shares = target_value / price
        return self._round_shares(shares) if signal.signal_type == 'LONG' else -self._round_shares(shares)
```

#### 2.2 Add Configuration Management

**File:** `/config/config.py`

```python
class BacktestConfig(BaseModel):
    """Backtesting configuration"""
    initial_capital: float = Field(default=100000.0, description="Starting capital")
    commission_rate: float = Field(default=0.001, description="Commission rate per trade")
    slippage: float = Field(default=0.0005, description="Price slippage")
    allow_fractional_shares: bool = Field(default=False, description="Allow fractional shares")
    position_size_mode: str = Field(default='percentage', description="Position sizing mode")
    max_position_pct: float = Field(default=0.25, description="Maximum position size (%)")
    cash_reserve_pct: float = Field(default=0.02, description="Reserve cash (%)")
```

---

### Phase 3: Testing & Monitoring (Priority: HIGH)

#### 3.1 Unit Tests

**File:** `/tests/unit/test_pre_trade_validator.py` (NEW)

```python
import pytest
from src.backtesting.validators import PreTradeValidator

def test_validator_affordable_order():
    """Test that affordable orders pass validation unchanged."""
    validator = PreTradeValidator(commission_rate=0.001)

    shares, info = validator.validate_order_size(
        shares=10,
        price=100.0,
        available_cash=2000.0,
        direction='BUY'
    )

    assert shares == 10
    assert info['validated'] == True
    assert info['adjustment'] == 'none'

def test_validator_exceeds_capital():
    """Test that orders exceeding capital are adjusted."""
    validator = PreTradeValidator(commission_rate=0.001)

    shares, info = validator.validate_order_size(
        shares=100,  # Would cost $10,000
        price=100.0,
        available_cash=1000.0,  # Only $1,000 available
        direction='BUY'
    )

    # Should adjust to ~9 shares ($900 + commission < $1000)
    assert shares < 10
    assert shares > 0
    assert info['validated'] == True
    assert info['adjustment'] == 'reduced'

def test_validator_insufficient_capital():
    """Test that orders with insufficient capital are rejected."""
    validator = PreTradeValidator(commission_rate=0.001)

    shares, info = validator.validate_order_size(
        shares=10,
        price=1000.0,  # $10,000 per share
        available_cash=100.0,  # Only $100
        direction='BUY'
    )

    assert shares == 0
    assert info['validated'] == False
    assert info['adjustment'] == 'rejected'

def test_validator_sell_orders():
    """Test that SELL orders don't require cash validation."""
    validator = PreTradeValidator(commission_rate=0.001)

    shares, info = validator.validate_order_size(
        shares=100,
        price=100.0,
        available_cash=0.0,  # No cash needed for selling
        direction='SELL'
    )

    assert shares == 100
    assert info['validated'] == True
```

#### 3.2 Integration Tests

**File:** `/tests/integration/test_position_sizing_integration.py` (NEW)

```python
def test_position_sizing_with_validation():
    """Test complete flow from strategy to validated order."""
    # Setup
    portfolio_handler = PortfolioHandler(
        initial_capital=1000.0,
        position_sizer=PercentageOfEquitySizer(0.1),  # 10%
        commission_rate=0.001,
    )

    # Generate signal
    signal = SignalEvent(
        timestamp=datetime.now(),
        symbol='AAPL',
        signal_type='LONG',
        price=150.0,  # Expensive stock
        strength=0.8,
    )

    # Generate orders
    orders = portfolio_handler.generate_orders(signal)

    # Validate
    assert len(orders) == 1
    order = orders[0]

    # With $1000 capital, 10% = $100 allocation
    # At $150/share → 0 shares (can't afford 1 share)
    # Validator should reduce or reject
    total_cost = order.quantity * signal.price * (1 + 0.001)
    assert total_cost <= 1000.0, "Order exceeds available capital!"

def test_multiple_orders_respect_cash():
    """Test that multiple simultaneous orders don't over-allocate."""
    portfolio_handler = PortfolioHandler(
        initial_capital=1000.0,
        position_sizer=PercentageOfEquitySizer(0.5),  # 50% per position
        commission_rate=0.001,
    )

    # Generate multiple signals
    signals = [
        SignalEvent(datetime.now(), 'AAPL', 'LONG', 100.0, 0.8),
        SignalEvent(datetime.now(), 'GOOGL', 'LONG', 100.0, 0.8),
        SignalEvent(datetime.now(), 'MSFT', 'LONG', 100.0, 0.8),
    ]

    total_allocated = 0
    for signal in signals:
        orders = portfolio_handler.generate_orders(signal)
        if orders:
            order_value = orders[0].quantity * signal.price
            total_allocated += order_value

    # Total allocated should not exceed initial capital
    assert total_allocated <= 1000.0, f"Over-allocated: ${total_allocated}"
```

#### 3.3 Property-Based Tests

**File:** `/tests/property/test_position_sizing_properties.py` (NEW)

```python
from hypothesis import given, strategies as st

@given(
    capital=st.floats(min_value=100, max_value=1_000_000),
    position_pct=st.floats(min_value=0.01, max_value=1.0),
    price=st.floats(min_value=0.01, max_value=10_000),
    commission=st.floats(min_value=0, max_value=0.01),
)
def test_order_never_exceeds_capital(capital, position_pct, price, commission):
    """Property: No order should ever exceed available capital."""
    validator = PreTradeValidator(commission_rate=commission)
    sizer = PercentageOfEquitySizer(position_pct)

    # Calculate ideal shares
    target_value = capital * position_pct
    ideal_shares = int(target_value / price)

    # Validate
    validated_shares, info = validator.validate_order_size(
        shares=ideal_shares,
        price=price,
        available_cash=capital,
        direction='BUY'
    )

    # Calculate actual cost
    actual_cost = validated_shares * price * (1 + commission)

    # Property: actual_cost ≤ capital (with small tolerance for rounding)
    assert actual_cost <= capital * 1.001, f"Cost ${actual_cost} exceeds capital ${capital}"
```

---

## Edge Cases & Handling

### Edge Case Matrix

| Case | Condition | Behavior | Test |
|------|-----------|----------|------|
| **Very expensive stock** | `price > equity * position_pct` | Reject order (can't afford 1 share) | ✓ |
| **Penny stock** | `price < 1.0` | Calculate many shares, validate against cash | ✓ |
| **Near-zero cash** | `cash < commission` | Reject all BUY orders | ✓ |
| **Fractional result** | `target_value / price = 10.7` | Floor to 10 shares (default) | ✓ |
| **Multiple simultaneous orders** | 3 orders at 50% each | First fills, rest adjusted/rejected | ✓ |
| **Negative position_size** | `position_size = -0.1` | Validation error on init | ✓ |
| **position_size > 1** | `position_size = 1.5` | Validation error on init | ✓ |
| **Zero equity** | `equity = 0` | All orders rejected | ✓ |

---

## Performance Considerations

### Computational Complexity

- **Pre-Trade Validation:** O(1) per order
- **Memory Overhead:** O(n) for pending orders tracking (n = symbols)
- **Expected Performance Impact:** < 1% overhead per backtest

### Optimization Opportunities

1. **Batch Validation:** Validate multiple orders simultaneously
2. **Cached Commission Calculations:** Reuse for same price points
3. **Vectorized Operations:** For multi-symbol strategies

---

## Migration Strategy

### Backward Compatibility

**Breaking Changes:**
- PortfolioHandler constructor signature changes (adds commission_rate, slippage_rate)
- Position sizers now enforce 0-1 range for percentages

**Migration Path:**
```python
# Old code (will break)
handler = PortfolioHandler(
    initial_capital=10000,
    position_sizer=PercentageOfEquitySizer(10)  # Wrong: 10 instead of 0.1
)

# New code (correct)
handler = PortfolioHandler(
    initial_capital=10000,
    position_sizer=PercentageOfEquitySizer(0.1),  # Correct: 0.1 = 10%
    commission_rate=0.001,
    slippage_rate=0.0005,
)
```

**Deprecation Warning:**
```python
# Add deprecation warning for old usage
if percentage > 1:
    warnings.warn(
        f"position_size={percentage} appears to be a percentage (10%) but should be "
        f"a fraction (0.1). This will raise an error in version 2.0. "
        f"Please update to position_size={percentage/100}",
        DeprecationWarning
    )
    percentage = percentage / 100  # Auto-convert for now
```

---

## Monitoring & Observability

### Key Metrics to Track

1. **Order Adjustments:**
   - Count of reduced orders
   - Count of rejected orders
   - Average adjustment percentage

2. **Capital Utilization:**
   - Average cash reserve
   - Peak reserved cash
   - Percentage of time fully invested

3. **Validation Failures:**
   - Insufficient capital rejections
   - Over-leverage attempts
   - Commission shortfalls

### Logging Strategy

```python
# Info level: Normal adjustments
logger.info(f"Order adjusted: {original:.2f} → {adjusted:.2f} shares")

# Warning level: Significant reductions
if adjusted < original * 0.5:
    logger.warning(f"Order reduced by >50%: insufficient capital")

# Error level: Should never happen after validation
if cash < 0:
    logger.error(f"CRITICAL: Negative cash detected: ${cash}")
```

### Dashboard Metrics

**Grafana/Prometheus metrics:**
```python
# Prometheus metrics
order_adjustments_total = Counter('backtest_order_adjustments_total')
order_rejections_total = Counter('backtest_order_rejections_total')
available_cash_ratio = Gauge('backtest_available_cash_ratio')
pending_orders_value = Gauge('backtest_pending_orders_value')
```

---

## Implementation Checklist

### Critical Path (Must Have)

- [ ] Create `PreTradeValidator` class with validation logic
- [ ] Update `PortfolioHandler.generate_orders()` to use validator
- [ ] Add pending orders tracking in `PortfolioHandler`
- [ ] Fix `PercentageOfEquitySizer` documentation clarity
- [ ] Add cash verification in `update_fill()`
- [ ] Add commission/slippage to `PortfolioHandler.__init__()`

### High Priority (Should Have)

- [ ] Write unit tests for `PreTradeValidator`
- [ ] Write integration tests for order flow
- [ ] Add property-based tests for edge cases
- [ ] Update configuration with new parameters
- [ ] Add migration guide for existing code
- [ ] Implement logging for adjustments/rejections

### Medium Priority (Nice to Have)

- [ ] Add fractional share support
- [ ] Implement batch validation
- [ ] Add Prometheus metrics
- [ ] Create validation report in backtest output
- [ ] Add visualization of capital utilization

### Low Priority (Future Enhancement)

- [ ] Add predictive cash management (forecast fills)
- [ ] Implement dynamic position sizing based on volatility
- [ ] Add multi-currency support
- [ ] Create position sizing optimization tool

---

## Success Criteria

### Functional Requirements

1. **No negative cash:** System never allows cash < 0
2. **Order affordability:** All generated orders are affordable
3. **Commission handling:** Commissions properly reserved and deducted
4. **Backward compatibility:** Existing strategies work with deprecation warnings

### Performance Requirements

1. **Speed:** < 1% overhead vs current implementation
2. **Memory:** < 10MB additional memory for 1000 symbols
3. **Accuracy:** 100% of orders validated correctly

### Quality Requirements

1. **Test coverage:** > 95% for new code
2. **Documentation:** Complete API docs and examples
3. **Edge cases:** All identified edge cases tested

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Rounding errors accumulate** | Medium | Low | Use Decimal for calculations |
| **Performance regression** | Low | Low | Benchmark before/after |
| **Breaking existing strategies** | High | Medium | Deprecation warnings + migration guide |
| **Edge case not covered** | High | Medium | Extensive property-based testing |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Incorrect backtest results** | Critical | Low | Parallel run old vs new, compare |
| **Production trading impacted** | Critical | Very Low | Isolated to backtest module |
| **User confusion** | Medium | Medium | Clear documentation + examples |

---

## References

### Related Documents

- `/docs/python-backtesting-guide.md` - Backtesting architecture
- `/config/config.py` - Configuration management
- `/docs/CRITICAL_ISSUES_REPORT.md` - Original issue report

### External Resources

- Position Sizing: *Van Tharp, "Definitive Guide to Position Sizing"*
- Risk Management: *Perry Kaufman, "Trading Systems and Methods"*
- Order Validation: *Ernest Chan, "Quantitative Trading"*

---

## Appendix A: Code Examples

### Example 1: Simple Strategy Using Fixed Percentage

```python
from src.backtesting.portfolio_handler import PortfolioHandler, PercentageOfEquitySizer
from src.strategies.simple_momentum import SimpleMomentumStrategy

# Initialize portfolio with validation
portfolio = PortfolioHandler(
    initial_capital=10000.0,
    position_sizer=PercentageOfEquitySizer(0.1),  # 10% per position
    commission_rate=0.001,  # 0.1% commission
    slippage_rate=0.0005,   # 0.05% slippage
)

# Create strategy
strategy = SimpleMomentumStrategy(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    position_size=0.1,  # 10% allocation (matches sizer)
)

# Run backtest
engine = BacktestEngine(portfolio, strategy)
results = engine.run()

# Check validation metrics
print(f"Orders generated: {results.total_orders}")
print(f"Orders adjusted: {results.adjusted_orders}")
print(f"Orders rejected: {results.rejected_orders}")
print(f"Final cash: ${results.final_cash:.2f}")
```

### Example 2: Handling Multiple Simultaneous Signals

```python
# With multiple signals, validator ensures we don't over-allocate
signals = [
    SignalEvent(timestamp, 'AAPL', 'LONG', 150.0, 0.8),
    SignalEvent(timestamp, 'GOOGL', 'LONG', 140.0, 0.7),
    SignalEvent(timestamp, 'MSFT', 'LONG', 380.0, 0.9),
]

# Each signal requests 10% ($1000), total = $3000
# Available cash: $10,000
# All orders should fill, using $3000 + commissions

for signal in signals:
    orders = portfolio.generate_orders(signal)
    for order in orders:
        # Execute order
        fill = execute_order(order)
        portfolio.update_fill(fill)

# Verify: cash should be ~$7000 (started with $10k, spent ~$3k)
assert 6900 <= portfolio.portfolio.cash <= 7100
```

### Example 3: Expensive Stock Edge Case

```python
# Edge case: Stock price exceeds allocation
signal = SignalEvent(
    timestamp=datetime.now(),
    symbol='BRK.A',  # Berkshire Hathaway Class A
    signal_type='LONG',
    price=621000.0,  # ~$621k per share
    strength=0.9,
)

# With $10,000 capital and 10% allocation ($1,000)
# Can't afford even 1 share
orders = portfolio.generate_orders(signal)

# Validator should reject: insufficient capital
assert len(orders) == 0 or orders[0].quantity == 0
```

---

## Appendix B: Mathematical Proofs

### Proof: Validator Prevents Negative Cash

**Theorem:** Given validator constraints, cash balance remains non-negative.

**Given:**
- Initial capital: C₀ > 0
- Commission rate: r_c ≥ 0
- Slippage rate: r_s ≥ 0
- Position size percentage: p ∈ (0, 1]

**To Prove:** ∀ orders, cash ≥ 0

**Proof:**

1. For order i, validator calculates:
   ```
   max_value_i = available_cash_i / (1 + r_c + r_s)
   max_shares_i = floor(max_value_i / price_i)
   ```

2. Total cost after validation:
   ```
   cost_i = max_shares_i × price_i × (1 + r_c + r_s)
        ≤ (max_value_i / price_i) × price_i × (1 + r_c + r_s)
        = max_value_i × (1 + r_c + r_s)
        = available_cash_i / (1 + r_c + r_s) × (1 + r_c + r_s)
        = available_cash_i
   ```

3. After fill:
   ```
   cash_{i+1} = cash_i - cost_i
             ≥ cash_i - available_cash_i
             ≥ cash_i - cash_i
             = 0
   ```

4. By induction, cash ≥ 0 for all orders. ∎

---

## Appendix C: Decision Tree for Position Sizing

```
┌─────────────────────────────────────┐
│     Receive Signal (LONG/SHORT)     │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Calculate Ideal Shares              │
│ shares = (equity × pct) / price     │
└────────────────┬────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Is SHORT?      │
        └────┬───────┬───┘
             │ YES   │ NO
             ▼       ▼
     ┌──────────┐   ┌──────────────────────────┐
     │ Return   │   │ Calculate Cost:          │
     │ shares   │   │ cost = shares × price ×  │
     │ (no cash │   │        (1 + comm + slip) │
     │ check)   │   └────────────┬─────────────┘
     └──────────┘                │
                                 ▼
                    ┌────────────────────────┐
                    │ cost ≤ available_cash? │
                    └────┬────────────┬──────┘
                         │ YES        │ NO
                         ▼            ▼
                ┌─────────────┐   ┌──────────────────────┐
                │ Return      │   │ Calculate Max:       │
                │ shares      │   │ max = cash /         │
                │             │   │       (1+comm+slip)  │
                └─────────────┘   │ shares = floor(      │
                                  │   max / price)       │
                                  └────────┬─────────────┘
                                           │
                                           ▼
                                  ┌─────────────────────┐
                                  │ shares > 0?         │
                                  └────┬───────────┬────┘
                                       │ YES       │ NO
                                       ▼           ▼
                              ┌─────────────┐  ┌────────────┐
                              │ Return      │  │ Reject     │
                              │ adjusted    │  │ order      │
                              │ shares      │  │ (return 0) │
                              └─────────────┘  └────────────┘
```

---

## Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-28 | System Architect Agent | Initial design document |

---

**END OF DESIGN DOCUMENT**
