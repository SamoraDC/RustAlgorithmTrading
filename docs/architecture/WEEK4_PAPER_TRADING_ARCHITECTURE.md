# Week 4: Paper Trading Architecture

**Project**: RustAlgorithmTrading
**Document Version**: 1.0
**Date**: 2025-10-29
**Status**: Design Complete - Ready for Implementation
**Prepared By**: System Architecture Agent (Hive Mind)

---

## Executive Summary

This document defines the comprehensive architecture for **Week 4: Paper Trading Deployment**, the final validation phase before production. The system will deploy the momentum strategy (optimized in Week 3) to Alpaca's paper trading environment for a **minimum 2-week live validation** period.

### Critical Requirements

**From fix_it.txt Week 4 Goals:**
- Deploy to Alpaca paper trading environment
- Run for 2 weeks minimum (target: 14+ calendar days)
- Daily performance monitoring and reporting
- Risk management validation in live conditions
- Emergency stop-loss at -5% total capital
- Automated health checks and alerts

### Success Criteria

| Metric | Minimum Threshold | Target | Decision |
|--------|------------------|--------|----------|
| **Win Rate** | ≥35% | ≥40% | GO to production |
| **Sharpe Ratio** | ≥0.3 | ≥0.5 | GO to production |
| **Max Drawdown** | ≤20% | ≤15% | GO to production |
| **System Uptime** | ≥95% | ≥99% | Critical for production |
| **Order Fill Rate** | ≥90% | ≥95% | Critical for production |
| **Emergency Stop** | Triggers at -5% | N/A | Safety requirement |

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Alpaca Integration](#alpaca-integration)
4. [Real-time Monitoring](#real-time-monitoring)
5. [Alert System](#alert-system)
6. [Risk Management](#risk-management)
7. [Logging Infrastructure](#logging-infrastructure)
8. [Daily Reporting](#daily-reporting)
9. [Operational Procedures](#operational-procedures)
10. [Technology Stack](#technology-stack)
11. [Implementation Timeline](#implementation-timeline)
12. [Deployment Checklist](#deployment-checklist)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   PAPER TRADING SYSTEM                           │
│                    (Week 4 Deployment)                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
    ┌──────────────────┐ ┌────────────┐ ┌─────────────────┐
    │ Trading Engine   │ │ Monitoring │ │ Alert System    │
    │ (Live Execution) │ │ Dashboard  │ │ (Real-time)     │
    └──────────────────┘ └────────────┘ └─────────────────┘
                │               │               │
                │               │               │
                ▼               ▼               ▼
    ┌─────────────────────────────────────────────────────┐
    │              Alpaca Paper Trading API                │
    │  (Market Data + Order Execution + Positions)         │
    └─────────────────────────────────────────────────────┘
                                │
                                ▼
    ┌─────────────────────────────────────────────────────┐
    │           Data Persistence Layer                     │
    │  • DuckDB (metrics.duckdb)                          │
    │  • SQLite (events.db)                               │
    │  • Log files (trades/, metrics/, system/)           │
    └─────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction Flow

```
[Market Open] → Strategy generates signals
                     ↓
             Risk checks (position limits, drawdown)
                     ↓
             Order validation (qty, price, capital)
                     ↓
             Submit to Alpaca Paper Trading API
                     ↓
             Monitor order status (pending → filled)
                     ↓
             Update portfolio state (positions, P&L)
                     ↓
             Record metrics (DuckDB + logs)
                     ↓
             Check alert conditions (drawdown, errors)
                     ↓
             [Real-time Dashboard Update]
```

---

## 2. Architecture Components

### 2.1 Trading Engine (Live Execution)

**Location**: `src/live_trading/paper_trading_engine.py`

**Responsibilities:**
- Market data subscription (real-time bars from Alpaca)
- Strategy signal generation (MomentumStrategy from Week 3)
- Order creation and submission
- Position tracking and P&L calculation
- Portfolio state management
- Emergency stop logic

**Key Features:**
```python
class PaperTradingEngine:
    """
    Live paper trading engine with safety controls.

    Features:
    - Real-time market data from Alpaca
    - Signal generation using validated strategies
    - Risk-managed order execution
    - Emergency stop at -5% drawdown
    - Comprehensive logging and metrics
    """

    def __init__(self, config: TradingConfig):
        self.alpaca_client = AlpacaPaperTrading()
        self.strategy = MomentumStrategy()  # Week 3 optimized
        self.risk_manager = RiskManager()
        self.portfolio_tracker = PortfolioTracker()
        self.emergency_stop_triggered = False

    def run(self):
        """Main trading loop"""
        while self.is_market_open() and not self.emergency_stop_triggered:
            # 1. Fetch market data
            # 2. Generate signals
            # 3. Risk checks
            # 4. Execute orders
            # 5. Update metrics
            # 6. Check emergency stop
            pass
```

**State Machine:**
```
[INITIALIZING] → [WAITING_FOR_MARKET_OPEN]
                        ↓
               [MARKET_OPEN_TRADING]
                        ↓
          ┌─────────────┴─────────────┐
          ▼                           ▼
   [ACTIVE_TRADING]          [EMERGENCY_STOP]
          ↓                           ↓
   [MARKET_CLOSE]              [LIQUIDATE_POSITIONS]
          ↓                           ↓
   [POST_MARKET_PROCESSING]    [HALT_TRADING]
          ↓                           ↓
   [IDLE]                      [NOTIFY_ADMIN]
```

### 2.2 Market Data Handler

**Location**: `src/live_trading/market_data_handler.py`

**Responsibilities:**
- Subscribe to Alpaca real-time data streams
- Maintain current price cache
- Calculate technical indicators (RSI, MACD, ADX)
- Handle market regime detection
- Manage data quality (missing bars, stale data)

**Data Flow:**
```python
class MarketDataHandler:
    """
    Real-time market data management.

    Uses Alpaca's StockDataStream for live bars.
    """

    async def subscribe_to_symbols(self, symbols: List[str]):
        """Subscribe to real-time bar data"""
        self.stream = StockDataStream(
            api_key=self.api_key,
            secret_key=self.secret_key
        )

        async def bar_handler(bar):
            # Update price cache
            self.price_cache[bar.symbol] = bar.close

            # Calculate indicators
            self.indicator_cache[bar.symbol] = self._calculate_indicators(bar)

            # Trigger strategy evaluation
            await self.on_bar_received(bar)

        self.stream.subscribe_bars(bar_handler, *symbols)
        await self.stream.run()
```

### 2.3 Order Manager

**Location**: `src/live_trading/order_manager.py`

**Responsibilities:**
- Order validation (quantity, price, capital availability)
- Order submission to Alpaca
- Order status tracking (pending → filled → complete)
- Fill notification and portfolio updates
- Error handling and retries

**Order Lifecycle:**
```
[SIGNAL_GENERATED]
       ↓
[VALIDATE_ORDER] ← Check: capital, position limits, risk
       ↓
[SUBMIT_TO_ALPACA] ← API call: submit_order()
       ↓
[PENDING] ← Status: waiting for fill
       ↓
[FILLED] ← Status: order executed
       ↓
[UPDATE_PORTFOLIO] ← Update positions, cash, P&L
       ↓
[RECORD_TRADE] ← Log to database and files
```

### 2.4 Portfolio Tracker

**Location**: `src/live_trading/portfolio_tracker.py`

**Responsibilities:**
- Track all open positions (symbol, qty, entry price, current P&L)
- Calculate portfolio metrics (total equity, cash, exposure)
- Monitor drawdown (current vs peak equity)
- Track daily P&L and cumulative returns
- Detect risk threshold breaches

**Core Metrics:**
```python
@dataclass
class PortfolioState:
    timestamp: datetime
    cash: Decimal
    equity: Decimal
    portfolio_value: Decimal
    peak_equity: Decimal  # For drawdown calculation

    # Positions
    positions: Dict[str, Position]
    total_position_value: Decimal

    # Performance
    total_pnl: Decimal
    total_pnl_pct: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: Decimal

    # Risk metrics
    current_drawdown: Decimal  # (peak - current) / peak
    max_drawdown: Decimal
    position_count: int
    total_exposure: Decimal  # Sum of abs(position values)
```

### 2.5 Risk Manager

**Location**: `src/live_trading/risk_manager.py`

**Responsibilities:**
- Pre-trade risk checks (before order submission)
- Position limit enforcement (max positions, position size)
- Drawdown monitoring (emergency stop at -5%)
- Exposure limits (total capital at risk)
- Concentration limits (max % in single position)

**Risk Rules:**
```python
class RiskManager:
    """
    Comprehensive risk management for paper trading.

    Rules:
    - Max 5 concurrent positions
    - Max 20% capital per position
    - Max 80% total exposure
    - Emergency stop at -5% drawdown
    - Max 3 trades per symbol per day
    """

    def validate_order(self, order: Order, portfolio: PortfolioState) -> RiskCheckResult:
        checks = [
            self._check_position_limit(portfolio),
            self._check_position_size(order, portfolio),
            self._check_exposure_limit(order, portfolio),
            self._check_drawdown(portfolio),
            self._check_daily_trade_limit(order),
        ]

        if all(check.passed for check in checks):
            return RiskCheckResult(passed=True)
        else:
            return RiskCheckResult(
                passed=False,
                reason=[c.reason for c in checks if not c.passed]
            )
```

**Emergency Stop Trigger:**
```python
def check_emergency_stop(self, portfolio: PortfolioState) -> bool:
    """
    Check if emergency stop should trigger.

    Emergency stop conditions:
    - Drawdown >= 5.0% from peak equity
    - Immediate liquidation of all positions
    - Trading halted until manual override
    """
    drawdown_pct = (portfolio.peak_equity - portfolio.equity) / portfolio.peak_equity

    if drawdown_pct >= 0.05:  # 5% emergency threshold
        logger.critical(
            f"🚨 EMERGENCY STOP TRIGGERED: Drawdown {drawdown_pct:.2%} >= 5.0% threshold"
        )
        return True

    return False
```

---

## 3. Alpaca Integration

### 3.1 Existing Integration

**Files:**
- `src/api/alpaca_client.py` - Basic client wrapper
- `src/api/alpaca_paper_trading.py` - Enhanced paper trading client

**Current Capabilities:**
✅ Account information retrieval
✅ Position tracking
✅ Order submission (market, limit, stop)
✅ Historical data fetching
✅ Real-time quote data
✅ Portfolio metrics calculation

### 3.2 Paper Trading Configuration

**Environment Variables** (`.env`):
```bash
# Alpaca Paper Trading Credentials
ALPACA_API_KEY=your_paper_api_key
ALPACA_SECRET_KEY=your_paper_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_PAPER_TRADING=true

# Trading Configuration
TRADING_MODE=paper
INITIAL_CAPITAL=100000.00
MAX_POSITIONS=5
MAX_POSITION_SIZE=0.20
EMERGENCY_STOP_DRAWDOWN=0.05

# Symbols to Trade
TRADING_SYMBOLS=AAPL,MSFT,GOOGL,AMZN,NVDA
```

### 3.3 API Integration Points

**1. Account Management**
```python
# Check account status before trading
account = alpaca_client.get_account_info()
if account['trading_blocked']:
    raise RuntimeError("Trading is blocked on this account")

# Verify buying power
if account['buying_power'] < min_required_capital:
    logger.warning("Insufficient buying power")
```

**2. Real-time Market Data**
```python
# Subscribe to bar updates (1-minute bars)
async def on_bar(bar):
    # Update strategy indicators
    strategy.update_data(bar)

    # Generate signal
    signal = strategy.generate_signal(bar.symbol)

    # Execute if valid
    if signal:
        await order_manager.process_signal(signal)

stream.subscribe_bars(on_bar, *symbols)
await stream.run()
```

**3. Order Submission**
```python
# Market order with validation
order = alpaca_client.place_order(
    symbol="AAPL",
    qty=10,
    side="buy",
    order_type=OrderType.MARKET,
    time_in_force="day"
)

# Track order status
while order['status'] == 'pending':
    await asyncio.sleep(1)
    order = alpaca_client.get_order(order['id'])

# Update portfolio on fill
if order['status'] == 'filled':
    portfolio.update_position(order)
```

**4. Position Monitoring**
```python
# Get all positions (every minute)
positions = alpaca_client.get_positions()

# Calculate P&L
for position in positions:
    pnl = (position.current_price - position.avg_entry_price) * position.qty
    pnl_pct = pnl / (position.avg_entry_price * position.qty)

    # Check exit conditions
    if strategy.should_exit(position, pnl_pct):
        await close_position(position.symbol)
```

### 3.4 Error Handling

**API Error Scenarios:**
- **Rate Limiting**: Exponential backoff, retry after delay
- **Network Errors**: Retry with exponential backoff (3 attempts)
- **Invalid Orders**: Log error, skip order, notify admin
- **Market Closed**: Queue orders for next market open
- **Account Restrictions**: Halt trading, notify admin

```python
class AlpacaAPIError(Exception):
    """Base exception for Alpaca API errors"""
    pass

def handle_api_error(error: Exception) -> ErrorAction:
    if isinstance(error, RateLimitError):
        return ErrorAction.RETRY_WITH_BACKOFF
    elif isinstance(error, NetworkError):
        return ErrorAction.RETRY_IMMEDIATE
    elif isinstance(error, InvalidOrderError):
        return ErrorAction.SKIP_AND_LOG
    elif isinstance(error, AccountBlockedError):
        return ErrorAction.HALT_TRADING
    else:
        return ErrorAction.NOTIFY_ADMIN
```

---

## 4. Real-time Monitoring

### 4.1 Monitoring Dashboard

**Technology**: React + WebSocket (existing observability stack)

**Dashboard URL**: `http://localhost:3000`

**Dashboard Sections:**

**A. Portfolio Overview**
```
┌─────────────────────────────────────────────────┐
│ PORTFOLIO OVERVIEW                              │
├─────────────────────────────────────────────────┤
│ Total Equity:        $102,450.00   (+2.45%)    │
│ Cash:                $85,200.00                 │
│ Positions Value:     $17,250.00                 │
│ Buying Power:        $250,000.00                │
│ Day P&L:            +$1,250.00     (+1.23%)    │
│ Total P&L:          +$2,450.00     (+2.45%)    │
│ Max Drawdown:       -1.2%                       │
│ Peak Equity:         $103,500.00                │
└─────────────────────────────────────────────────┘
```

**B. Open Positions**
```
┌─────────────────────────────────────────────────┐
│ OPEN POSITIONS (3)                              │
├─────────────────────────────────────────────────┤
│ Symbol  Qty   Entry    Current   P&L      %     │
├─────────────────────────────────────────────────┤
│ AAPL    50   $175.20  $178.50  +$165.00  +1.9% │
│ MSFT    30   $380.50  $382.10  +$48.00   +0.4% │
│ GOOGL   25   $140.30  $139.80  -$12.50   -0.4% │
└─────────────────────────────────────────────────┘
```

**C. Today's Trades**
```
┌─────────────────────────────────────────────────┐
│ TODAY'S TRADES                                  │
├─────────────────────────────────────────────────┤
│ Time     Symbol  Side  Qty  Price    Status    │
├─────────────────────────────────────────────────┤
│ 09:35    AAPL    BUY   50  $175.20  FILLED     │
│ 10:12    MSFT    BUY   30  $380.50  FILLED     │
│ 11:45    GOOGL   BUY   25  $140.30  FILLED     │
└─────────────────────────────────────────────────┘
```

**D. Risk Metrics**
```
┌─────────────────────────────────────────────────┐
│ RISK METRICS                                    │
├─────────────────────────────────────────────────┤
│ Current Drawdown:     -1.2%  [SAFE]            │
│ Emergency Stop:       -5.0%  [NOT TRIGGERED]   │
│ Position Count:       3/5    [60% utilized]    │
│ Total Exposure:       17.3%  [LOW]             │
│ Largest Position:     8.2%   [AAPL]            │
│ Concentration Risk:   LOW                       │
└─────────────────────────────────────────────────┘
```

**E. Performance Chart**
```
┌─────────────────────────────────────────────────┐
│ EQUITY CURVE (Last 7 Days)                     │
├─────────────────────────────────────────────────┤
│                                     ╭─╮         │
│                               ╭─╮  │ │         │
│                          ╭──╮│ │  │ │         │
│                     ╭──╮│  ││ │  │ │         │
│ $102,500 ─────────╮│  ││  ││ │  │ │         │
│                   ││  ││  ││ │  │ │         │
│ $100,000 ─────────╰╯  ╰╯  ╰╯ ╰──╯ ╰─────── │
└─────────────────────────────────────────────────┘
```

### 4.2 WebSocket Metrics Stream

**Endpoint**: `ws://localhost:8000/ws/metrics`

**Update Frequency**: 1 second (1Hz)

**Streamed Data:**
```json
{
  "timestamp": "2025-10-29T14:30:15.123Z",
  "portfolio": {
    "equity": 102450.00,
    "cash": 85200.00,
    "positions_value": 17250.00,
    "buying_power": 250000.00,
    "daily_pnl": 1250.00,
    "daily_pnl_pct": 1.23,
    "total_pnl": 2450.00,
    "total_pnl_pct": 2.45,
    "position_count": 3
  },
  "risk": {
    "current_drawdown": 0.012,
    "max_drawdown": 0.012,
    "emergency_stop_triggered": false,
    "total_exposure": 0.173,
    "largest_position_pct": 0.082
  },
  "positions": [
    {
      "symbol": "AAPL",
      "qty": 50,
      "avg_entry_price": 175.20,
      "current_price": 178.50,
      "unrealized_pnl": 165.00,
      "unrealized_pnl_pct": 1.9
    }
  ],
  "system": {
    "status": "ACTIVE_TRADING",
    "market_open": true,
    "uptime_seconds": 7200,
    "last_signal_time": "2025-10-29T14:28:45Z",
    "last_order_time": "2025-10-29T11:45:12Z"
  }
}
```

### 4.3 Monitoring API Endpoints

**Base URL**: `http://localhost:8000/api`

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/portfolio/current` | GET | Current portfolio state |
| `/portfolio/history?days=7` | GET | Historical portfolio snapshots |
| `/positions/current` | GET | All open positions |
| `/trades/today` | GET | Today's completed trades |
| `/trades/history?days=14` | GET | Historical trade log |
| `/risk/metrics` | GET | Current risk metrics |
| `/system/status` | GET | System health and status |
| `/alerts/active` | GET | Active alerts and warnings |

---

## 5. Alert System

### 5.1 Alert Categories

**1. Critical Alerts** (Immediate Action Required)
- Emergency stop triggered (-5% drawdown)
- Trading API connection lost
- Account restrictions detected
- System crash or unexpected shutdown

**2. High Priority Alerts**
- Drawdown exceeds -3%
- Order submission failures (3+ consecutive)
- Position limit reached
- Unusual trade frequency (>10 trades/day)

**3. Medium Priority Alerts**
- Daily loss exceeds -2%
- Position P&L < -5% for any single position
- Strategy signal generation stopped
- Data quality issues (missing bars, stale data)

**4. Low Priority Alerts**
- Daily trade count exceeds target (>10 trades)
- Low trading activity (<3 trades in 5 days)
- Minor system warnings

### 5.2 Alert Delivery Channels

**A. Console Logging** (All Alerts)
```python
logger.critical("🚨 EMERGENCY STOP TRIGGERED: Drawdown -5.2%")
logger.error("❌ Order submission failed: Insufficient buying power")
logger.warning("⚠️ Drawdown approaching emergency threshold: -4.2%")
logger.info("ℹ️ Daily trade count: 8 (approaching limit of 10)")
```

**B. Dashboard Notifications** (All Alerts)
- Real-time banner at top of dashboard
- Alert history panel
- Visual indicators (red/yellow/green status)

**C. Email Notifications** (Critical + High Priority)
```python
class EmailAlerter:
    """
    Email notification system for critical alerts.
    """

    def send_emergency_stop_alert(self, portfolio: PortfolioState):
        subject = "🚨 EMERGENCY STOP TRIGGERED - Paper Trading Halted"
        body = f"""
        Emergency stop has been triggered for paper trading system.

        Drawdown: {portfolio.current_drawdown:.2%}
        Emergency Threshold: 5.0%

        All positions have been liquidated.
        Trading has been halted.

        Please review system logs and investigate.
        """

        send_email(
            to=config.admin_email,
            subject=subject,
            body=body,
            priority="CRITICAL"
        )
```

**D. Slack Notifications** (Critical + High Priority)
```python
class SlackAlerter:
    """
    Slack webhook integration for alerts.
    """

    def post_alert(self, alert: Alert):
        payload = {
            "text": f"🚨 {alert.severity.upper()}: {alert.message}",
            "attachments": [
                {
                    "color": "danger" if alert.severity == "critical" else "warning",
                    "fields": [
                        {"title": "Time", "value": alert.timestamp.isoformat()},
                        {"title": "System", "value": "Paper Trading"},
                        {"title": "Details", "value": alert.details}
                    ]
                }
            ]
        }

        requests.post(config.slack_webhook_url, json=payload)
```

### 5.3 Alert Rules Configuration

**File**: `config/alert_rules.yaml`

```yaml
alert_rules:
  emergency_stop:
    severity: critical
    condition: "portfolio.current_drawdown >= 0.05"
    action: "halt_trading_and_liquidate"
    channels: ["console", "dashboard", "email", "slack"]

  high_drawdown:
    severity: high
    condition: "portfolio.current_drawdown >= 0.03"
    action: "notify_admin"
    channels: ["console", "dashboard", "email"]

  daily_loss:
    severity: medium
    condition: "portfolio.daily_pnl_pct <= -0.02"
    action: "log_and_notify"
    channels: ["console", "dashboard"]

  order_failure:
    severity: high
    condition: "consecutive_order_failures >= 3"
    action: "pause_trading_and_notify"
    channels: ["console", "dashboard", "email", "slack"]

  position_limit:
    severity: medium
    condition: "portfolio.position_count >= max_positions"
    action: "log_and_notify"
    channels: ["console", "dashboard"]
```

---

## 6. Risk Management

### 6.1 Risk Control Framework

**Pre-Trade Risk Checks:**
```python
class PreTradeRiskCheck:
    """
    Validate order before submission to Alpaca.
    """

    def validate(self, order: Order, portfolio: PortfolioState) -> RiskCheckResult:
        # 1. Position count limit
        if portfolio.position_count >= config.max_positions:
            return RiskCheckResult(
                passed=False,
                reason="Position limit reached"
            )

        # 2. Position size limit
        order_value = order.qty * order.price
        if order_value > portfolio.equity * config.max_position_size:
            return RiskCheckResult(
                passed=False,
                reason=f"Position size exceeds {config.max_position_size:.0%} limit"
            )

        # 3. Total exposure limit
        new_exposure = portfolio.total_exposure + order_value
        if new_exposure > portfolio.equity * config.max_exposure:
            return RiskCheckResult(
                passed=False,
                reason=f"Total exposure would exceed {config.max_exposure:.0%} limit"
            )

        # 4. Drawdown check
        if portfolio.current_drawdown >= config.emergency_stop_threshold:
            return RiskCheckResult(
                passed=False,
                reason="Emergency stop active"
            )

        # 5. Daily trade limit (per symbol)
        if self.get_daily_trade_count(order.symbol) >= config.max_daily_trades_per_symbol:
            return RiskCheckResult(
                passed=False,
                reason="Daily trade limit reached for this symbol"
            )

        return RiskCheckResult(passed=True)
```

**Post-Trade Risk Monitoring:**
```python
class PostTradeRiskMonitor:
    """
    Monitor portfolio after each trade execution.
    """

    async def monitor_portfolio(self, portfolio: PortfolioState):
        # 1. Check emergency stop
        if self.check_emergency_stop(portfolio):
            await self.trigger_emergency_stop(portfolio)
            return

        # 2. Check high drawdown warning
        if portfolio.current_drawdown >= 0.03:
            await self.alert_high_drawdown(portfolio)

        # 3. Check position P&L
        for position in portfolio.positions.values():
            if position.unrealized_pnl_pct <= -0.05:
                await self.alert_position_loss(position)

        # 4. Check daily P&L
        if portfolio.daily_pnl_pct <= -0.02:
            await self.alert_daily_loss(portfolio)
```

### 6.2 Emergency Stop Mechanism

**Trigger Conditions:**
- Drawdown ≥ 5.0% from peak equity

**Emergency Stop Actions:**
1. **IMMEDIATE**: Set `emergency_stop_triggered = True`
2. **IMMEDIATE**: Cancel all pending orders
3. **IMMEDIATE**: Liquidate all positions (market orders)
4. **IMMEDIATE**: Log emergency stop event
5. **IMMEDIATE**: Send critical alerts (email, Slack, dashboard)
6. **IMMEDIATE**: Halt trading loop
7. **POST-LIQUIDATION**: Generate emergency stop report
8. **POST-LIQUIDATION**: Notify administrator for manual review

**Code Implementation:**
```python
async def trigger_emergency_stop(self, portfolio: PortfolioState):
    """
    Execute emergency stop procedure.
    """
    logger.critical("="*60)
    logger.critical("🚨 EMERGENCY STOP TRIGGERED")
    logger.critical(f"Drawdown: {portfolio.current_drawdown:.2%}")
    logger.critical(f"Peak Equity: ${portfolio.peak_equity:,.2f}")
    logger.critical(f"Current Equity: ${portfolio.equity:,.2f}")
    logger.critical("="*60)

    # Set flag
    self.emergency_stop_triggered = True

    # Cancel all pending orders
    cancelled_count = self.alpaca_client.cancel_all_orders()
    logger.critical(f"Cancelled {cancelled_count} pending orders")

    # Liquidate all positions
    positions = self.alpaca_client.get_positions()
    logger.critical(f"Liquidating {len(positions)} positions...")

    for position in positions:
        try:
            self.alpaca_client.close_position(position.symbol)
            logger.critical(f"✓ Liquidated {position.symbol}")
        except Exception as e:
            logger.critical(f"✗ Failed to liquidate {position.symbol}: {e}")

    # Send alerts
    await self.alert_system.send_emergency_stop_alert(portfolio)

    # Generate report
    report = self.generate_emergency_stop_report(portfolio)
    self.save_report(report, "emergency_stop_report.json")

    # Halt trading
    logger.critical("Trading halted. Manual intervention required.")
    logger.critical("="*60)
```

### 6.3 Risk Parameters

**Configuration** (`config/risk_config.yaml`):
```yaml
risk_management:
  # Position limits
  max_positions: 5
  max_position_size: 0.20  # 20% of equity per position
  max_exposure: 0.80       # 80% total capital at risk

  # Drawdown limits
  emergency_stop_threshold: 0.05  # -5% drawdown
  high_drawdown_warning: 0.03     # -3% drawdown

  # Trade limits
  max_daily_trades_per_symbol: 3
  max_daily_trades_total: 10

  # Concentration limits
  max_sector_exposure: 0.40       # 40% max in any sector
  max_single_stock_exposure: 0.25 # 25% max in any stock

  # Stop-loss and take-profit (from strategy)
  stop_loss_pct: 0.02             # -2% stop-loss
  take_profit_pct: 0.03           # +3% take-profit
  trailing_stop_pct: 0.015        # 1.5% trailing stop
```

---

## 7. Logging Infrastructure

### 7.1 Log Structure

**Log Directories:**
```
logs/
├── paper_trading/
│   ├── trading_YYYYMMDD.log        # Daily trading logs
│   ├── orders_YYYYMMDD.log         # Order execution logs
│   ├── positions_YYYYMMDD.log      # Position updates
│   ├── risk_YYYYMMDD.log           # Risk check logs
│   └── system_YYYYMMDD.log         # System health logs
├── alerts/
│   ├── critical_YYYYMMDD.log       # Critical alerts
│   └── warnings_YYYYMMDD.log       # Warning alerts
└── performance/
    ├── daily_summary_YYYYMMDD.log  # Daily P&L summaries
    └── weekly_report_YYYYWW.log    # Weekly reports
```

### 7.2 Log Levels and Format

**Log Levels:**
- **CRITICAL**: Emergency stop, system crashes, trading halts
- **ERROR**: Order failures, API errors, data quality issues
- **WARNING**: High drawdown, position limits, risk warnings
- **INFO**: Trade executions, signal generation, system state changes
- **DEBUG**: Detailed calculations, indicator values, internal state

**Log Format:**
```
[2025-10-29 14:30:15.123] [LEVEL] [module] message | context_key=value
```

**Example Logs:**
```
[2025-10-29 09:30:05.001] [INFO] [trading_engine] Market opened | status=ACTIVE_TRADING
[2025-10-29 09:35:12.456] [INFO] [strategy] Signal generated | symbol=AAPL signal=LONG confidence=0.75 rsi=65.2 macd_hist=0.025
[2025-10-29 09:35:12.789] [INFO] [risk_manager] Risk check passed | symbol=AAPL order_value=$8760.00 position_size_pct=8.8% exposure_pct=17.3%
[2025-10-29 09:35:13.123] [INFO] [order_manager] Order submitted | symbol=AAPL side=BUY qty=50 price=$175.20 order_id=abc123
[2025-10-29 09:35:15.456] [INFO] [order_manager] Order filled | symbol=AAPL order_id=abc123 fill_price=$175.25 fill_qty=50
[2025-10-29 09:35:15.789] [INFO] [portfolio] Position opened | symbol=AAPL qty=50 entry_price=$175.25 value=$8762.50
[2025-10-29 14:30:20.123] [WARNING] [risk_manager] High drawdown detected | drawdown=-3.2% threshold=-3.0%
[2025-10-29 14:45:30.456] [ERROR] [order_manager] Order submission failed | symbol=MSFT reason="Insufficient buying power" retry_count=1
[2025-10-29 15:55:10.789] [CRITICAL] [risk_manager] Emergency stop triggered | drawdown=-5.2% peak_equity=$103500.00 current_equity=$98094.00
```

### 7.3 Structured Logging

**Implementation:**
```python
from loguru import logger
import json

# Configure Loguru
logger.remove()  # Remove default handler

# Add file handlers
logger.add(
    "logs/paper_trading/trading_{time:YYYYMMDD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="INFO",
    rotation="00:00",  # New file at midnight
    retention="30 days",
    compression="zip"
)

logger.add(
    "logs/alerts/critical_{time:YYYYMMDD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
    level="CRITICAL",
    rotation="00:00",
    retention="90 days"
)

# Structured logging helper
def log_trade_execution(order: Order, fill: Fill):
    logger.info(
        "Trade executed",
        extra={
            "event_type": "trade_execution",
            "symbol": order.symbol,
            "side": order.side,
            "qty": fill.qty,
            "price": fill.price,
            "order_id": order.id,
            "timestamp": fill.timestamp.isoformat()
        }
    )
```

### 7.4 Log Rotation and Retention

**Rotation Policy:**
- **Daily Logs**: Rotate at midnight (00:00)
- **Weekly Reports**: Generate every Monday at 00:00
- **Emergency Logs**: No rotation (keep indefinitely)

**Retention Policy:**
- **Trading Logs**: 30 days
- **Alert Logs**: 90 days
- **Performance Reports**: 180 days
- **Emergency Stop Reports**: Indefinite

**Compression:**
- Compress rotated logs to `.zip` format
- Saves ~80% disk space

---

## 8. Daily Reporting

### 8.1 Daily Performance Report

**Schedule**: Generated daily at 16:30 (30 minutes after market close)

**Report Location**: `data/reports/daily_YYYYMMDD.json`

**Report Sections:**

**A. Executive Summary**
```json
{
  "report_date": "2025-10-29",
  "trading_day": 5,
  "summary": {
    "equity_start": 100000.00,
    "equity_end": 102450.00,
    "daily_pnl": 1250.00,
    "daily_pnl_pct": 1.25,
    "cumulative_pnl": 2450.00,
    "cumulative_pnl_pct": 2.45,
    "trades_executed": 3,
    "positions_opened": 3,
    "positions_closed": 0,
    "win_rate": 0.67,
    "sharpe_ratio": 0.45,
    "max_drawdown": -0.012
  }
}
```

**B. Trade Details**
```json
{
  "trades": [
    {
      "time": "09:35:15",
      "symbol": "AAPL",
      "side": "BUY",
      "qty": 50,
      "entry_price": 175.25,
      "current_price": 178.50,
      "unrealized_pnl": 165.00,
      "unrealized_pnl_pct": 1.88
    }
  ]
}
```

**C. Risk Metrics**
```json
{
  "risk_metrics": {
    "current_drawdown": -0.012,
    "max_drawdown": -0.012,
    "emergency_stop_distance": -0.038,
    "position_count": 3,
    "max_position_count": 5,
    "total_exposure": 0.173,
    "max_exposure": 0.80,
    "largest_position_symbol": "AAPL",
    "largest_position_pct": 0.082
  }
}
```

**D. Strategy Performance**
```json
{
  "strategy_metrics": {
    "signals_generated": 5,
    "signals_executed": 3,
    "signals_rejected": 2,
    "rejection_reasons": {
      "insufficient_capital": 1,
      "position_limit": 1
    },
    "avg_signal_confidence": 0.72,
    "signal_quality_score": 0.68
  }
}
```

**E. System Health**
```json
{
  "system_health": {
    "uptime_seconds": 23400,
    "uptime_pct": 100.0,
    "api_errors": 0,
    "order_failures": 0,
    "data_quality_score": 1.0,
    "alerts_triggered": 1,
    "alert_details": [
      {
        "time": "14:30:20",
        "severity": "warning",
        "message": "High drawdown detected: -3.2%"
      }
    ]
  }
}
```

### 8.2 Weekly Summary Report

**Schedule**: Generated every Monday at 08:00

**Report Location**: `data/reports/weekly_YYYYWW.json`

**Report Sections:**

**A. Week Overview**
```json
{
  "week_number": 44,
  "start_date": "2025-10-27",
  "end_date": "2025-11-02",
  "trading_days": 5,
  "summary": {
    "equity_start": 100000.00,
    "equity_end": 105250.00,
    "weekly_pnl": 5250.00,
    "weekly_pnl_pct": 5.25,
    "total_trades": 15,
    "winning_trades": 9,
    "losing_trades": 6,
    "win_rate": 0.60,
    "avg_win": 850.00,
    "avg_loss": -320.00,
    "profit_factor": 2.66,
    "sharpe_ratio": 1.25,
    "max_drawdown": -0.025,
    "best_day": {
      "date": "2025-10-29",
      "pnl": 2450.00,
      "pnl_pct": 2.45
    },
    "worst_day": {
      "date": "2025-10-28",
      "pnl": -850.00,
      "pnl_pct": -0.85
    }
  }
}
```

**B. Performance vs Targets**
```json
{
  "targets_vs_actual": {
    "win_rate": {
      "target": 0.40,
      "actual": 0.60,
      "status": "ABOVE_TARGET"
    },
    "sharpe_ratio": {
      "target": 0.50,
      "actual": 1.25,
      "status": "ABOVE_TARGET"
    },
    "max_drawdown": {
      "target": -0.15,
      "actual": -0.025,
      "status": "WITHIN_LIMIT"
    },
    "trade_frequency": {
      "target_min": 10,
      "target_max": 30,
      "actual": 15,
      "status": "ON_TARGET"
    }
  }
}
```

**C. GO/NO-GO Assessment**
```json
{
  "go_no_go_assessment": {
    "criteria": {
      "win_rate_above_35": true,
      "sharpe_ratio_above_0_3": true,
      "max_drawdown_below_20": true,
      "system_uptime_above_95": true,
      "no_emergency_stops": true
    },
    "criteria_met": 5,
    "criteria_total": 5,
    "recommendation": "GO - All criteria met",
    "confidence": "HIGH",
    "notes": "Strategy performing above expectations. Ready for production."
  }
}
```

### 8.3 Report Distribution

**Delivery Channels:**
1. **File System**: JSON reports saved to `data/reports/`
2. **Dashboard**: Summary displayed on monitoring dashboard
3. **Email**: Daily summaries emailed to admin at 17:00
4. **Slack**: Weekly summaries posted to #paper-trading channel

**Email Template:**
```
Subject: [Paper Trading] Daily Report - 2025-10-29

Daily Performance Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 5 of Paper Trading

Portfolio Performance:
  • Equity: $102,450 (+2.45% total, +1.25% today)
  • Trades: 3 executed (9 total)
  • Win Rate: 67% (60% cumulative)
  • Max Drawdown: -1.2%

Risk Status:
  ✓ All systems operational
  ✓ Emergency stop: Not triggered
  ⚠ High drawdown warning: -3.2% (14:30)

Top Performers:
  1. AAPL: +$165 (+1.88%)
  2. MSFT: +$48 (+0.42%)
  3. GOOGL: -$12 (-0.36%)

Full Report: data/reports/daily_20251029.json
Dashboard: http://localhost:3000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 9. Operational Procedures

### 9.1 Daily Startup Procedure

**Time**: 09:00 (30 minutes before market open)

**Checklist:**

1. **Pre-flight Checks** (09:00 - 09:15)
   ```bash
   # Check system dependencies
   ./scripts/check_dependencies.sh

   # Verify Alpaca credentials
   python -c "from src.api.alpaca_paper_trading import AlpacaPaperTrading; AlpacaPaperTrading().connect()"

   # Check disk space
   df -h | grep data

   # Review overnight logs
   tail -n 100 logs/paper_trading/trading_$(date +%Y%m%d -d yesterday).log
   ```

2. **Start Observability Stack** (09:15 - 09:20)
   ```bash
   # Start monitoring dashboard
   ./scripts/start_observability.sh

   # Verify dashboard accessible
   curl http://localhost:8000/health
   ```

3. **Start Paper Trading Engine** (09:20 - 09:25)
   ```bash
   # Start trading engine
   python src/live_trading/paper_trading_engine.py --mode=live --config=config/paper_trading_config.yaml

   # Verify engine status
   curl http://localhost:8000/api/system/status
   ```

4. **Pre-Market Verification** (09:25 - 09:30)
   ```bash
   # Check account status
   curl http://localhost:8000/api/portfolio/current

   # Verify positions from previous day
   curl http://localhost:8000/api/positions/current

   # Review risk metrics
   curl http://localhost:8000/api/risk/metrics
   ```

5. **Market Open** (09:30)
   - Monitor dashboard for first signal
   - Verify order submission works
   - Check real-time data updates

### 9.2 Daily Shutdown Procedure

**Time**: 16:30 (30 minutes after market close)

**Checklist:**

1. **Post-Market Review** (16:00 - 16:15)
   ```bash
   # Get final portfolio state
   curl http://localhost:8000/api/portfolio/current > data/snapshots/portfolio_$(date +%Y%m%d).json

   # Get today's trades
   curl http://localhost:8000/api/trades/today > data/snapshots/trades_$(date +%Y%m%d).json

   # Get risk metrics
   curl http://localhost:8000/api/risk/metrics > data/snapshots/risk_$(date +%Y%m%d).json
   ```

2. **Generate Daily Report** (16:15 - 16:20)
   ```bash
   # Generate report
   python scripts/generate_daily_report.py --date=$(date +%Y%m%d)

   # Verify report created
   ls -lh data/reports/daily_$(date +%Y%m%d).json
   ```

3. **Review Alerts** (16:20 - 16:25)
   ```bash
   # Check for critical alerts
   grep "CRITICAL" logs/paper_trading/trading_$(date +%Y%m%d).log

   # Review warnings
   grep "WARNING" logs/paper_trading/trading_$(date +%Y%m%d).log | wc -l
   ```

4. **Backup Data** (16:25 - 16:30)
   ```bash
   # Backup DuckDB
   cp data/metrics.duckdb data/backups/metrics_$(date +%Y%m%d).duckdb

   # Backup logs
   tar -czf data/backups/logs_$(date +%Y%m%d).tar.gz logs/paper_trading/
   ```

5. **Optional: Stop Services** (16:30+)
   ```bash
   # Keep running 24/7 for continuous monitoring
   # OR stop if needed:
   pkill -f paper_trading_engine.py
   pkill -f start_observability.sh
   ```

### 9.3 Weekly Review Procedure

**Time**: Every Monday at 08:00

**Checklist:**

1. **Generate Weekly Report** (08:00 - 08:15)
   ```bash
   python scripts/generate_weekly_report.py --week=$(date +%Y%W)
   ```

2. **Review Performance vs Targets** (08:15 - 08:30)
   - Win rate ≥40%? ✓
   - Sharpe ratio ≥0.5? ✓
   - Max drawdown ≤15%? ✓
   - System uptime ≥95%? ✓

3. **Assess GO/NO-GO Status** (08:30 - 08:45)
   - If Week 2+ and all criteria met → Prepare for production
   - If Week 1 or some criteria not met → Continue monitoring

4. **Distribute Report** (08:45 - 09:00)
   - Email weekly summary to stakeholders
   - Post to Slack #paper-trading channel
   - Update documentation with findings

### 9.4 Emergency Stop Procedure

**Trigger**: Drawdown ≥ 5.0%

**Automated Actions** (Immediate):
1. Set `emergency_stop_triggered = True`
2. Cancel all pending orders
3. Liquidate all positions (market orders)
4. Send critical alerts (email, Slack)
5. Halt trading loop

**Manual Actions** (Within 1 hour):
1. Review emergency stop report
2. Analyze root cause (code bug, market conditions, strategy flaw)
3. Determine corrective action:
   - **Code Bug**: Fix bug, test, resume
   - **Market Conditions**: Wait for normalcy, resume
   - **Strategy Flaw**: Halt paper trading, redesign strategy
4. Document incident in `docs/incidents/emergency_stop_YYYYMMDD.md`
5. Update risk parameters if needed
6. Get approval before resuming

**Resume Trading** (Manual Override Required):
```bash
# Reset emergency stop flag
python scripts/reset_emergency_stop.py --confirm

# Restart trading engine
python src/live_trading/paper_trading_engine.py --mode=live
```

---

## 10. Technology Stack

### 10.1 Core Technologies

**Programming Language:**
- Python 3.12+ (primary)

**Trading Infrastructure:**
- **Alpaca API**: Paper trading, market data, order execution
  - `alpaca-py` SDK (official Python library)
  - REST API for orders and portfolio
  - WebSocket API for real-time data

**Data Storage:**
- **DuckDB**: Time-series metrics (`data/metrics.duckdb`)
  - Market data, strategy metrics, execution metrics, system metrics
- **SQLite**: Real-time events (`data/events.db`)
  - Trade events, alert events
- **File System**: Logs, reports, backups

**Observability:**
- **FastAPI**: REST API for metrics (`http://localhost:8000`)
- **Uvicorn**: ASGI server for FastAPI
- **WebSocket**: Real-time metric streaming (1Hz)
- **React**: Dashboard frontend (`http://localhost:3000`)

**Logging:**
- **Loguru**: Structured logging with rotation and compression

**Configuration:**
- **Pydantic**: Type-safe configuration management
- **python-dotenv**: Environment variable loading
- **YAML**: Configuration files

### 10.2 Python Dependencies

**File**: `requirements.txt`
```txt
# Trading and Market Data
alpaca-py==0.12.0
pandas==2.1.4
numpy==1.26.2

# Data Storage
duckdb==0.9.2
sqlalchemy==2.0.23

# Web Framework
fastapi==0.105.0
uvicorn[standard]==0.25.0
websockets==12.0

# Configuration
pydantic==2.5.2
pydantic-settings==2.1.0
python-dotenv==1.0.0
PyYAML==6.0.1

# Logging
loguru==0.7.2

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1

# Utilities
requests==2.31.0
aiohttp==3.9.1
```

### 10.3 Project Structure

```
RustAlgorithmTrading/
├── src/
│   ├── api/
│   │   ├── alpaca_client.py           # Basic Alpaca wrapper
│   │   └── alpaca_paper_trading.py    # Enhanced paper trading client
│   ├── live_trading/                  # NEW: Week 4 paper trading
│   │   ├── __init__.py
│   │   ├── paper_trading_engine.py    # Main trading engine
│   │   ├── market_data_handler.py     # Real-time data management
│   │   ├── order_manager.py           # Order submission and tracking
│   │   ├── portfolio_tracker.py       # Portfolio state management
│   │   └── risk_manager.py            # Risk checks and emergency stop
│   ├── strategies/
│   │   └── momentum.py                # Week 3 optimized strategy
│   ├── backtesting/
│   │   └── portfolio_handler.py       # Reuse for position tracking
│   ├── observability/                 # Existing observability stack
│   │   ├── api/main.py
│   │   ├── dashboard/
│   │   └── metrics/
│   └── utils/
│       └── market_regime.py           # Market regime detection
├── config/
│   ├── config.py                      # Configuration classes
│   ├── paper_trading_config.yaml      # NEW: Paper trading config
│   ├── risk_config.yaml               # NEW: Risk parameters
│   └── alert_rules.yaml               # NEW: Alert configuration
├── scripts/
│   ├── start_paper_trading.sh         # NEW: Startup script
│   ├── generate_daily_report.py       # NEW: Daily report generator
│   ├── generate_weekly_report.py      # NEW: Weekly report generator
│   └── reset_emergency_stop.py        # NEW: Emergency stop reset
├── data/
│   ├── metrics.duckdb                 # Metrics database
│   ├── events.db                      # Events database
│   ├── reports/                       # NEW: Daily/weekly reports
│   ├── snapshots/                     # NEW: Daily portfolio snapshots
│   └── backups/                       # NEW: Database/log backups
├── logs/
│   ├── paper_trading/                 # NEW: Trading logs
│   ├── alerts/                        # NEW: Alert logs
│   └── performance/                   # NEW: Performance reports
├── docs/
│   ├── architecture/
│   │   └── WEEK4_PAPER_TRADING_ARCHITECTURE.md  # This document
│   └── incidents/                     # NEW: Incident reports
└── tests/
    └── live_trading/                  # NEW: Paper trading tests
        ├── test_paper_trading_engine.py
        ├── test_order_manager.py
        ├── test_risk_manager.py
        └── test_emergency_stop.py
```

---

## 11. Implementation Timeline

### Phase 1: Core Infrastructure (Days 1-2)

**Day 1: Trading Engine Foundation**
- [ ] Create `src/live_trading/` module structure
- [ ] Implement `paper_trading_engine.py` main loop
- [ ] Implement `market_data_handler.py` with Alpaca WebSocket
- [ ] Implement `order_manager.py` with order lifecycle
- [ ] Write unit tests for core components
- **Deliverable**: Basic trading engine that can receive market data and submit orders

**Day 2: Portfolio and Risk Management**
- [ ] Implement `portfolio_tracker.py` with P&L tracking
- [ ] Implement `risk_manager.py` with pre-trade checks
- [ ] Implement emergency stop mechanism
- [ ] Add drawdown monitoring
- [ ] Write unit tests for risk management
- **Deliverable**: Complete risk-managed trading engine

### Phase 2: Monitoring and Alerts (Day 3)

**Day 3: Observability Integration**
- [ ] Extend existing FastAPI routes for paper trading metrics
- [ ] Add WebSocket endpoint for live portfolio updates
- [ ] Update React dashboard with paper trading components
- [ ] Implement alert system (email, Slack integration)
- [ ] Create alert rules configuration
- **Deliverable**: Real-time monitoring dashboard with alerts

### Phase 3: Reporting and Operations (Day 4)

**Day 4: Reporting and Procedures**
- [ ] Implement `generate_daily_report.py`
- [ ] Implement `generate_weekly_report.py`
- [ ] Create startup/shutdown scripts
- [ ] Write operational procedures documentation
- [ ] Create emergency stop reset script
- **Deliverable**: Complete reporting and operational procedures

### Phase 4: Testing and Validation (Day 5)

**Day 5: Integration Testing**
- [ ] End-to-end testing with Alpaca paper account
- [ ] Test emergency stop trigger and recovery
- [ ] Test alert delivery (email, Slack, dashboard)
- [ ] Load testing (handle 10+ concurrent positions)
- [ ] Test daily/weekly report generation
- **Deliverable**: Fully tested and validated system

### Phase 5: Deployment (Day 6)

**Day 6: Live Deployment**
- [ ] Deploy to paper trading environment
- [ ] Run pre-flight checks
- [ ] Start trading engine at market open
- [ ] Monitor first day of trading
- [ ] Generate first daily report
- **Deliverable**: System deployed and running in paper trading

### Phase 6: Monitoring Period (Days 7-19)

**Days 7-19: 2-Week Paper Trading Run**
- [ ] Daily monitoring and report review
- [ ] Weekly performance assessments
- [ ] Adjust risk parameters if needed
- [ ] Document any issues or incidents
- [ ] Prepare final GO/NO-GO recommendation
- **Deliverable**: 2 weeks of paper trading data and final recommendation

---

## 12. Deployment Checklist

### 12.1 Pre-Deployment Checklist

**Environment Setup:**
- [ ] Python 3.12+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Alpaca paper trading account created
- [ ] API keys obtained and stored in `.env`
- [ ] `.env` file configured with all variables

**Configuration:**
- [ ] `config/paper_trading_config.yaml` reviewed and validated
- [ ] `config/risk_config.yaml` configured with appropriate limits
- [ ] `config/alert_rules.yaml` configured with alert channels
- [ ] Admin email and Slack webhook configured

**Infrastructure:**
- [ ] Directory structure created (`logs/`, `data/`, `reports/`)
- [ ] DuckDB database initialized (`data/metrics.duckdb`)
- [ ] SQLite database initialized (`data/events.db`)
- [ ] FastAPI observability server running
- [ ] React dashboard accessible

**Testing:**
- [ ] Unit tests passing (95%+ coverage)
- [ ] Integration tests passing
- [ ] Alpaca API connection verified
- [ ] Emergency stop mechanism tested
- [ ] Alert delivery tested (email, Slack)

### 12.2 Deployment Day Checklist

**Morning (09:00 - 09:30):**
- [ ] Run pre-flight checks (`./scripts/check_dependencies.sh`)
- [ ] Verify Alpaca account status
- [ ] Review overnight news/market events
- [ ] Start observability stack
- [ ] Start paper trading engine
- [ ] Verify real-time data streaming

**Market Open (09:30 - 10:00):**
- [ ] Monitor first signal generation
- [ ] Verify first order submission
- [ ] Check order fill status
- [ ] Verify portfolio update
- [ ] Monitor dashboard for real-time updates

**Throughout Day:**
- [ ] Check dashboard every hour
- [ ] Review alerts as they occur
- [ ] Monitor system logs for errors
- [ ] Verify data quality (no missing bars)

**Market Close (16:00 - 16:30):**
- [ ] Review final portfolio state
- [ ] Generate daily report
- [ ] Check for any alerts or errors
- [ ] Backup databases and logs
- [ ] Prepare summary for stakeholders

### 12.3 First Week Milestones

**Day 1:**
- [ ] First successful trade executed
- [ ] No system crashes or errors
- [ ] All monitoring systems operational
- [ ] Daily report generated successfully

**Day 3:**
- [ ] At least 3-5 trades executed
- [ ] Risk management working (no breaches)
- [ ] Portfolio P&L tracked accurately
- [ ] Alert system tested (if triggered)

**Day 5:**
- [ ] First weekly report generated
- [ ] Win rate calculated (target ≥35%)
- [ ] Sharpe ratio calculated (target ≥0.3)
- [ ] No emergency stops triggered

**Day 7:**
- [ ] System uptime ≥95%
- [ ] Order fill rate ≥90%
- [ ] Data quality score ≥95%
- [ ] All operational procedures validated

### 12.4 Week 2+ Monitoring

**Weekly Review (Every Monday):**
- [ ] Generate and review weekly report
- [ ] Assess performance vs targets
- [ ] Check GO/NO-GO criteria
- [ ] Document any adjustments needed
- [ ] Update stakeholders on progress

**Continuous Monitoring:**
- [ ] Daily portfolio review
- [ ] Risk metrics within limits
- [ ] System health checks
- [ ] Alert response (< 1 hour for critical)
- [ ] Backup verification

**GO/NO-GO Decision (End of Week 2):**
- [ ] Win rate ≥35% (target: ≥40%)
- [ ] Sharpe ratio ≥0.3 (target: ≥0.5)
- [ ] Max drawdown ≤20% (target: ≤15%)
- [ ] System uptime ≥95% (target: ≥99%)
- [ ] No emergency stops triggered
- [ ] Final recommendation prepared

---

## Appendix A: Configuration Examples

### A.1 Paper Trading Configuration

**File**: `config/paper_trading_config.yaml`
```yaml
# Week 4 Paper Trading Configuration

# Alpaca API
alpaca:
  api_key: ${ALPACA_API_KEY}
  secret_key: ${ALPACA_SECRET_KEY}
  base_url: "https://paper-api.alpaca.markets"
  paper_trading: true

# Trading Configuration
trading:
  mode: "paper"
  initial_capital: 100000.00
  symbols:
    - AAPL
    - MSFT
    - GOOGL
    - AMZN
    - NVDA

  # Strategy
  strategy:
    name: "momentum"
    config_file: "config/momentum_strategy.yaml"

  # Execution
  execution:
    order_type: "market"
    time_in_force: "day"
    retry_attempts: 3
    retry_delay_seconds: 5

# Risk Management
risk:
  max_positions: 5
  max_position_size: 0.20
  max_exposure: 0.80
  emergency_stop_threshold: 0.05
  high_drawdown_warning: 0.03
  stop_loss_pct: 0.02
  take_profit_pct: 0.03
  trailing_stop_pct: 0.015

# Monitoring
monitoring:
  dashboard_url: "http://localhost:3000"
  api_url: "http://localhost:8000"
  websocket_update_frequency: 1.0  # seconds
  metrics_log_frequency: 60.0      # seconds

# Alerts
alerts:
  email:
    enabled: true
    admin_email: ${ADMIN_EMAIL}
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
  slack:
    enabled: true
    webhook_url: ${SLACK_WEBHOOK_URL}
    channel: "#paper-trading"

# Logging
logging:
  level: "INFO"
  log_dir: "logs/paper_trading"
  rotation: "midnight"
  retention: "30 days"
  compression: "zip"

# Reporting
reporting:
  daily_report_time: "16:30"
  weekly_report_day: "monday"
  weekly_report_time: "08:00"
  report_dir: "data/reports"
```

### A.2 Risk Configuration

**File**: `config/risk_config.yaml`
```yaml
# Risk Management Configuration

position_limits:
  max_positions: 5
  max_position_size: 0.20       # 20% of equity
  max_exposure: 0.80            # 80% total capital
  max_sector_exposure: 0.40     # 40% per sector
  max_single_stock: 0.25        # 25% per stock

trade_limits:
  max_daily_trades_per_symbol: 3
  max_daily_trades_total: 10
  min_trade_interval_minutes: 30

drawdown_limits:
  emergency_stop_threshold: 0.05    # -5% emergency stop
  high_drawdown_warning: 0.03       # -3% warning
  daily_loss_warning: 0.02          # -2% daily loss warning

stop_loss:
  stop_loss_pct: 0.02               # -2% hard stop
  trailing_stop_pct: 0.015          # 1.5% trailing stop
  trailing_stop_activation: 0.01    # Activate after +1% gain

take_profit:
  take_profit_pct: 0.03             # +3% take profit
  partial_take_profit_pct: 0.02     # +2% partial take profit (50%)

validation:
  min_confidence: 0.60              # Minimum signal confidence
  min_volume_ratio: 1.05            # Volume must be 5% above average
  max_spread_pct: 0.02              # Max 2% bid-ask spread
```

### A.3 Alert Rules

**File**: `config/alert_rules.yaml`
```yaml
# Alert Configuration

alert_rules:
  emergency_stop:
    severity: "critical"
    condition: "portfolio.current_drawdown >= 0.05"
    action: "halt_trading_and_liquidate"
    channels: ["console", "dashboard", "email", "slack"]
    cooldown_minutes: 0

  high_drawdown:
    severity: "high"
    condition: "portfolio.current_drawdown >= 0.03"
    action: "notify_admin"
    channels: ["console", "dashboard", "email"]
    cooldown_minutes: 60

  daily_loss:
    severity: "medium"
    condition: "portfolio.daily_pnl_pct <= -0.02"
    action: "log_and_notify"
    channels: ["console", "dashboard"]
    cooldown_minutes: 120

  order_failure:
    severity: "high"
    condition: "consecutive_order_failures >= 3"
    action: "pause_trading_and_notify"
    channels: ["console", "dashboard", "email", "slack"]
    cooldown_minutes: 0

  position_limit:
    severity: "medium"
    condition: "portfolio.position_count >= max_positions"
    action: "log_and_notify"
    channels: ["console", "dashboard"]
    cooldown_minutes: 300

  position_loss:
    severity: "medium"
    condition: "position.unrealized_pnl_pct <= -0.05"
    action: "log_and_notify"
    channels: ["console", "dashboard"]
    cooldown_minutes: 60

  api_connection_lost:
    severity: "critical"
    condition: "api_connection_error"
    action: "halt_trading_and_notify"
    channels: ["console", "dashboard", "email", "slack"]
    cooldown_minutes: 0

  data_quality:
    severity: "high"
    condition: "missing_bars > 3"
    action: "log_and_notify"
    channels: ["console", "dashboard", "email"]
    cooldown_minutes: 30

# Channel Configuration
channels:
  console:
    enabled: true
    format: "structured"

  dashboard:
    enabled: true
    websocket_url: "ws://localhost:8000/ws/alerts"

  email:
    enabled: true
    from_email: "paper-trading@example.com"
    to_emails:
      - ${ADMIN_EMAIL}
    subject_prefix: "[Paper Trading]"

  slack:
    enabled: true
    webhook_url: ${SLACK_WEBHOOK_URL}
    username: "Paper Trading Bot"
    icon_emoji: ":chart_with_upwards_trend:"
```

---

## Appendix B: Data Schemas

### B.1 DuckDB Schema

**File**: `src/observability/database/duckdb_schema.sql`
```sql
-- Market Data Metrics
CREATE TABLE IF NOT EXISTS market_data_metrics (
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR NOT NULL,
    price DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    bid DOUBLE,
    ask DOUBLE,
    spread DOUBLE,
    PRIMARY KEY (timestamp, symbol)
);

-- Portfolio Metrics
CREATE TABLE IF NOT EXISTS portfolio_metrics (
    timestamp TIMESTAMP NOT NULL PRIMARY KEY,
    equity DOUBLE NOT NULL,
    cash DOUBLE NOT NULL,
    portfolio_value DOUBLE NOT NULL,
    buying_power DOUBLE NOT NULL,
    total_pnl DOUBLE NOT NULL,
    total_pnl_pct DOUBLE NOT NULL,
    daily_pnl DOUBLE NOT NULL,
    daily_pnl_pct DOUBLE NOT NULL,
    position_count INTEGER NOT NULL,
    peak_equity DOUBLE NOT NULL,
    current_drawdown DOUBLE NOT NULL,
    max_drawdown DOUBLE NOT NULL
);

-- Position Snapshots
CREATE TABLE IF NOT EXISTS position_snapshots (
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR NOT NULL,
    qty DOUBLE NOT NULL,
    avg_entry_price DOUBLE NOT NULL,
    current_price DOUBLE NOT NULL,
    market_value DOUBLE NOT NULL,
    cost_basis DOUBLE NOT NULL,
    unrealized_pnl DOUBLE NOT NULL,
    unrealized_pnl_pct DOUBLE NOT NULL,
    side VARCHAR NOT NULL,
    PRIMARY KEY (timestamp, symbol)
);

-- Trade Executions
CREATE TABLE IF NOT EXISTS trade_executions (
    timestamp TIMESTAMP NOT NULL,
    trade_id VARCHAR NOT NULL PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    side VARCHAR NOT NULL,
    qty DOUBLE NOT NULL,
    entry_price DOUBLE NOT NULL,
    exit_price DOUBLE,
    pnl DOUBLE,
    pnl_pct DOUBLE,
    strategy VARCHAR NOT NULL,
    signal_confidence DOUBLE,
    status VARCHAR NOT NULL
);

-- Risk Events
CREATE TABLE IF NOT EXISTS risk_events (
    timestamp TIMESTAMP NOT NULL,
    event_id VARCHAR NOT NULL PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    description TEXT NOT NULL,
    metrics JSON,
    action_taken VARCHAR
);

-- System Metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    timestamp TIMESTAMP NOT NULL PRIMARY KEY,
    cpu_percent DOUBLE NOT NULL,
    memory_percent DOUBLE NOT NULL,
    disk_usage_percent DOUBLE NOT NULL,
    active_threads INTEGER NOT NULL,
    uptime_seconds INTEGER NOT NULL,
    api_errors_count INTEGER NOT NULL,
    order_failures_count INTEGER NOT NULL
);
```

### B.2 SQLite Schema

**File**: `src/observability/database/sqlite_schema.sql`
```sql
-- Alert Events
CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    severity TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_at REAL,
    acknowledged_by TEXT
);

-- Order Events
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty REAL NOT NULL,
    order_type TEXT NOT NULL,
    status TEXT NOT NULL,
    fill_price REAL,
    fill_qty REAL,
    error_message TEXT
);

-- Strategy Signals
CREATE TABLE IF NOT EXISTS strategy_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    indicators TEXT,
    executed BOOLEAN DEFAULT 0,
    rejection_reason TEXT
);

-- System Events
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    component TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_alert_events_timestamp ON alert_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_order_events_timestamp ON order_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_timestamp ON strategy_signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp);
```

---

## Conclusion

This architecture provides a comprehensive, production-ready paper trading system for Week 4 validation. Key features include:

✅ **Complete Alpaca Integration**: Leverages existing paper trading client
✅ **Real-time Monitoring**: Dashboard with 1Hz WebSocket updates
✅ **Comprehensive Risk Management**: Emergency stop at -5% drawdown
✅ **Robust Alert System**: Email, Slack, and dashboard notifications
✅ **Detailed Logging**: Structured logs with rotation and compression
✅ **Daily/Weekly Reporting**: Automated performance summaries
✅ **Operational Procedures**: Clear startup, shutdown, and emergency protocols

**Next Steps:**
1. Review and approve this architecture
2. Begin implementation (Phase 1: Days 1-2)
3. Complete testing and validation (Phase 4-5: Days 5-6)
4. Deploy to paper trading (Phase 6: Day 6)
5. Run 2-week monitoring period (Days 7-19)
6. Make final GO/NO-GO decision for production

**Prepared By**: System Architecture Agent
**Coordination**: Hive Mind Swarm (swarm-1761761393507-k9l37n3pp)
**Date**: 2025-10-29
**Status**: ✅ Architecture Design Complete
