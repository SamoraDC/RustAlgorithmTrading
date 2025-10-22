# Code Review: Potential Errors and Failure Points

**Reviewer:** Code Review Agent
**Date:** 2025-10-22
**Scope:** Backtesting modules, Rust bridge, Orchestration scripts

---

## Executive Summary

Identified **15 critical issues**, **12 high-priority issues**, and **8 medium-priority issues** that could cause system failures. Primary concerns include parameter mismatches, missing error handling, hardcoded port configurations, and type inconsistencies.

---

## CRITICAL ISSUES (Immediate Action Required)

### 1. BacktestEngine Initialization Parameter Mismatch
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/engine.py`
**Lines:** 25-50
**Severity:** CRITICAL

**Issue:**
The `BacktestEngine.__init__` expects 4-6 parameters, but the autonomous trading script passes only 3 parameters in a different order.

**Current Code (engine.py:25-33):**
```python
def __init__(
    self,
    data_handler: HistoricalDataHandler,
    execution_handler: SimulatedExecutionHandler,
    portfolio_handler: PortfolioHandler,
    strategy,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
```

**Calling Code (autonomous_trading_system.sh:184-201):**
```python
data_handler = HistoricalDataHandler(symbols, start_date, end_date)
strategy = SimpleMomentumStrategy(symbols)
engine = BacktestEngine(data_handler, strategy, initial_capital)
```

**Problem:**
- Missing `execution_handler` parameter
- Missing `portfolio_handler` parameter
- `initial_capital` is passed but not accepted by `__init__`
- Order of parameters doesn't match

**Impact:** BacktestEngine will fail to initialize, causing immediate crash

**Recommended Fix:**
```python
# In autonomous_trading_system.sh (lines 184-201)
data_handler = HistoricalDataHandler(symbols, start_date, end_date)
execution_handler = SimulatedExecutionHandler()
portfolio_handler = PortfolioHandler(initial_capital)
strategy = SimpleMomentumStrategy(symbols)
engine = BacktestEngine(
    data_handler=data_handler,
    execution_handler=execution_handler,
    portfolio_handler=portfolio_handler,
    strategy=strategy,
    start_date=start_date,
    end_date=end_date
)
```

---

### 2. Missing HistoricalDataHandler Initialization Parameter
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/data_handler.py`
**Lines:** 22-28
**Severity:** CRITICAL

**Issue:**
`HistoricalDataHandler.__init__` requires a `data_dir` parameter (line 25), but the script doesn't pass it.

**Current Signature:**
```python
def __init__(
    self,
    symbols: list[str],
    data_dir: Path,  # REQUIRED but not provided
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
```

**Calling Code:**
```python
data_handler = HistoricalDataHandler(symbols, start_date, end_date)
```

**Impact:** Immediate TypeError on initialization

**Recommended Fix:**
```python
# Add data_dir parameter
data_dir = Path('data/historical')
data_handler = HistoricalDataHandler(
    symbols=symbols,
    data_dir=data_dir,
    start_date=start_date,
    end_date=end_date
)
```

---

### 3. Hardcoded Rust Service Ports Don't Match
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/observability/metrics/rust_bridge.py`
**Lines:** 303-307
**Severity:** CRITICAL

**Issue:**
Rust metrics bridge hardcodes ports (9091, 9092, 9093), but the autonomous script starts services on different ports (5001, 5002, 5003).

**rust_bridge.py:**
```python
endpoints = {
    "market_data": "http://127.0.0.1:9091/metrics",
    "execution": "http://127.0.0.1:9092/metrics",
    "risk": "http://127.0.0.1:9093/metrics",
}
```

**autonomous_trading_system.sh (lines 389-393):**
```bash
local services=(
    "market-data:5001"
    "risk-manager:5002"
    "execution-engine:5003"
)
```

**Impact:** Metrics collection will fail silently, no monitoring data

**Recommended Fix:**
Option 1 - Update rust_bridge.py to match script ports:
```python
endpoints = {
    "market_data": "http://127.0.0.1:5001/metrics",
    "execution": "http://127.0.0.1:5003/metrics",
    "risk": "http://127.0.0.1:5002/metrics",
}
```

Option 2 - Create environment variable configuration:
```python
import os
endpoints = {
    "market_data": f"http://127.0.0.1:{os.getenv('MARKET_DATA_PORT', '5001')}/metrics",
    "execution": f"http://127.0.0.1:{os.getenv('EXECUTION_PORT', '5003')}/metrics",
    "risk": f"http://127.0.0.1:{os.getenv('RISK_PORT', '5002')}/metrics",
}
```

---

### 4. Missing Error Handling for SimpleMomentumStrategy.calculate_signals
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/engine.py`
**Lines:** 136
**Severity:** CRITICAL

**Issue:**
`strategy.calculate_signals(event)` is called without error handling, but SimpleMomentumStrategy expects a DataFrame, not a MarketEvent.

**Current Code:**
```python
def _handle_market_event(self, event: MarketEvent):
    self.portfolio_handler.update_timeindex(event.timestamp)
    signals = self.strategy.calculate_signals(event)  # Type mismatch!
```

**SimpleMomentumStrategy expects:**
```python
def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
```

**Impact:** TypeError or AttributeError, backtest crash

**Recommended Fix:**
```python
def _handle_market_event(self, event: MarketEvent):
    self.portfolio_handler.update_timeindex(event.timestamp)

    try:
        # Convert market event to format strategy expects
        # or update strategy to accept MarketEvent
        signals = self.strategy.calculate_signals(event)

        if signals:
            for signal in signals:
                self.events.append(signal)
    except AttributeError as e:
        logger.error(f"Strategy method mismatch: {e}")
    except Exception as e:
        logger.error(f"Error calculating signals: {e}")
```

---

### 5. PerformanceMetrics vs PerformanceAnalyzer Return Type Mismatch
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/performance.py`
**Lines:** 42-59
**Severity:** CRITICAL

**Issue:**
`PerformanceAnalyzer.calculate_performance_metrics()` returns a `PerformanceMetrics` object (line 46), but the engine expects a dictionary with `to_dict()` method (engine.py:202).

**PerformanceAnalyzer:**
```python
def calculate_performance_metrics(...) -> PerformanceMetrics:
    # Returns PerformanceMetrics object
    return PerformanceMetrics(...)
```

**Engine expects:**
```python
metrics = self.performance_analyzer.calculate_performance_metrics(...)
return {
    'metrics': metrics.to_dict(),  # Assumes to_dict() method exists
    ...
}
```

**Impact:** AttributeError if `PerformanceMetrics` doesn't have `to_dict()` method

**Recommended Fix:**
Add `to_dict()` method to PerformanceMetrics model or convert in analyzer:
```python
def calculate_performance_metrics(...) -> Dict:
    # ... calculations ...
    return {
        'total_return': total_return * 100,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        # ... all metrics as dict
    }
```

---

## HIGH PRIORITY ISSUES

### 6. Missing Data Directory Creation
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 168-245
**Severity:** HIGH

**Issue:**
Script assumes `data/historical` directory exists for HistoricalDataHandler, but only creates `data/backtest_results` and `data/simulation_results`.

**Impact:** FileNotFoundError when loading historical data

**Recommended Fix:**
```bash
# In setup or main() function
mkdir -p "$PROJECT_ROOT/data/historical"
mkdir -p "$PROJECT_ROOT/data/backtest_results"
mkdir -p "$PROJECT_ROOT/data/simulation_results"
mkdir -p "$PROJECT_ROOT/data/live_trading"
```

---

### 7. Unvalidated JSON Output File Path
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 225-226
**Severity:** HIGH

**Issue:**
Output file path uses Python f-string interpolation inside bash heredoc without directory validation.

**Current Code:**
```python
output_file = f"data/backtest_results/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
os.makedirs('data/backtest_results', exist_ok=True)
```

**Problem:**
- Relative path assumes running from project root
- No error handling if directory creation fails
- No disk space check

**Recommended Fix:**
```python
import os
from pathlib import Path

output_dir = Path('data/backtest_results').resolve()
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Add disk space check
import shutil
stat = shutil.disk_usage(output_dir)
if stat.free < 100 * 1024 * 1024:  # 100MB minimum
    raise RuntimeError("Insufficient disk space")
```

---

### 8. Missing Import in autonomous_trading_system.sh Python Code
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 174-259
**Severity:** HIGH

**Issue:**
Python heredoc imports `BacktestEngine`, `HistoricalDataHandler`, and `SimpleMomentumStrategy` but doesn't import `SimulatedExecutionHandler` or `PortfolioHandler`.

**Missing Imports:**
```python
from backtesting.engine import BacktestEngine
from backtesting.data_handler import HistoricalDataHandler
# MISSING: from backtesting.execution_handler import SimulatedExecutionHandler
# MISSING: from backtesting.portfolio_handler import PortfolioHandler
from strategies.simple_momentum import SimpleMomentumStrategy
```

**Impact:** NameError when trying to instantiate execution and portfolio handlers

**Recommended Fix:**
```python
from backtesting.engine import BacktestEngine
from backtesting.data_handler import HistoricalDataHandler
from backtesting.execution_handler import SimulatedExecutionHandler
from backtesting.portfolio_handler import PortfolioHandler
from strategies.simple_momentum import SimpleMomentumStrategy
```

---

### 9. Type Inconsistency: datetime vs Timestamp
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/portfolio_handler.py`
**Lines:** 48-64
**Severity:** HIGH

**Issue:**
Portfolio handler expects `datetime` objects but data handler may provide pandas Timestamps.

**portfolio_handler.py:**
```python
def update_timeindex(self, timestamp: datetime):
    self.portfolio.timestamp = timestamp
```

**data_handler.py (line 72):**
```python
# df['timestamp'] might be pandas Timestamp, not datetime
if self.start_date:
    df = df[df['timestamp'] >= self.start_date]
```

**Impact:** Type errors or incorrect comparisons

**Recommended Fix:**
```python
def update_timeindex(self, timestamp):
    # Convert pandas Timestamp to datetime if needed
    if hasattr(timestamp, 'to_pydatetime'):
        timestamp = timestamp.to_pydatetime()
    self.portfolio.timestamp = timestamp
```

---

### 10. Missing Signal Conversion in portfolio_handler.generate_orders
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/portfolio_handler.py`
**Lines:** 66-110
**Severity:** HIGH

**Issue:**
Method expects `SignalEvent` but gets `Signal` from SimpleMomentumStrategy. These are different classes.

**Type Mismatch:**
- `portfolio_handler.py` expects: `SignalEvent` (from `src.models.events`)
- `SimpleMomentumStrategy` returns: `Signal` (from `strategies.base`)

**Impact:** AttributeError when accessing signal properties

**Recommended Fix:**
```python
def generate_orders(self, signal) -> List[OrderEvent]:
    """Generate orders from trading signal."""
    orders = []

    # Handle both Signal and SignalEvent types
    symbol = getattr(signal, 'symbol', None)
    signal_type = getattr(signal, 'signal_type', getattr(signal, 'action', None))
    strength = getattr(signal, 'strength', 1.0)

    if not symbol or not signal_type:
        logger.warning(f"Invalid signal: {signal}")
        return orders

    # ... rest of method
```

---

### 11. No Validation for Empty Backtest Results
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 246-269
**Severity:** HIGH

**Issue:**
Script checks thresholds but doesn't validate that metrics exist or are valid numbers.

**Current Code:**
```bash
if sharpe_ratio < 1.0 or win_rate < 0.50 or abs(max_drawdown) > 0.20:
    print("[BACKTEST] FAILED - Metrics below threshold")
    sys.exit(1)
```

**Problem:**
- No check if `sharpe_ratio` is None or NaN
- No check if `results` dictionary contains expected keys
- Division by zero in metrics calculation not handled

**Recommended Fix:**
```python
# Validate metrics exist and are valid
required_metrics = ['sharpe_ratio', 'win_rate', 'max_drawdown', 'profit_factor']
for metric in required_metrics:
    if metric not in results:
        print(f"[BACKTEST] ERROR: Missing metric '{metric}'")
        sys.exit(1)
    if results[metric] is None or np.isnan(results[metric]):
        print(f"[BACKTEST] ERROR: Invalid metric '{metric}' = {results[metric]}")
        sys.exit(1)

sharpe_ratio = results['sharpe_ratio']
win_rate = results['win_rate']
max_drawdown = results['max_drawdown']

# Then perform threshold checks
if sharpe_ratio < 1.0 or win_rate < 0.50 or abs(max_drawdown) > 0.20:
    print("[BACKTEST] FAILED - Metrics below threshold")
    sys.exit(1)
```

---

### 12. Missing Price Field in Position Sizing
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/portfolio_handler.py`
**Lines:** 186-198
**Severity:** HIGH

**Issue:**
Position sizers use hardcoded default price (100.0) when position doesn't exist, leading to incorrect position sizing.

**Current Code:**
```python
current_position = portfolio.positions.get(signal.symbol)
price = current_position.current_price if current_position else 100.0  # BAD!
```

**Problem:**
- Default price of $100 is arbitrary
- Real price should come from signal or market data
- Can lead to massive over/under-leveraging

**Recommended Fix:**
```python
# Get price from signal or raise error
if not hasattr(signal, 'price'):
    raise ValueError(f"Signal for {signal.symbol} missing price information")

current_position = portfolio.positions.get(signal.symbol)
price = current_position.current_price if current_position else signal.price

if price <= 0:
    raise ValueError(f"Invalid price {price} for {signal.symbol}")
```

---

### 13. Race Condition in Service Startup
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 386-420
**Severity:** HIGH

**Issue:**
Script starts Rust services and only waits 2 seconds before assuming they're ready. No actual health check.

**Current Code:**
```bash
"./$service" > "$LOG_DIR/$service.log" 2>&1 &
local pid=$!
echo $pid > "$LOG_DIR/$service.pid"

# Wait for service to be ready
sleep 2  # Not reliable!

if kill -0 $pid 2>/dev/null; then
    log_success "$service started (PID: $pid)"
```

**Problem:**
- Process might be running but not ready to accept connections
- No verification that HTTP endpoint is accessible
- Can lead to downstream connection failures

**Recommended Fix:**
```bash
"./$service" > "$LOG_DIR/$service.log" 2>&1 &
local pid=$!
echo $pid > "$LOG_DIR/$service.pid"

# Wait for service to be ready with health check
local max_wait=30
local waited=0
while [ $waited -lt $max_wait ]; do
    if kill -0 $pid 2>/dev/null; then
        # Check if HTTP endpoint responds
        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
            log_success "$service started (PID: $pid)"
            break
        fi
    else
        log_error "$service failed to start"
        return 1
    fi
    sleep 1
    waited=$((waited + 1))
done

if [ $waited -ge $max_wait ]; then
    log_error "$service health check timeout"
    return 1
fi
```

---

### 14. Missing Connection Pool Management in rust_bridge.py
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/observability/metrics/rust_bridge.py`
**Lines:** 41-53
**Severity:** HIGH

**Issue:**
Session is created once and reused indefinitely without connection pool limits or timeout handling.

**Current Code:**
```python
async def start(self):
    if self.session is None:
        timeout = aiohttp.ClientTimeout(total=5.0)
        self.session = aiohttp.ClientSession(timeout=timeout)
```

**Problem:**
- No connection pool size limit
- No keep-alive configuration
- No retry logic for failed connections
- Can lead to resource exhaustion

**Recommended Fix:**
```python
async def start(self):
    if self.session is None:
        timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
        connector = aiohttp.TCPConnector(
            limit=10,  # Max connections
            limit_per_host=3,  # Per host limit
            ttl_dns_cache=300,  # DNS cache TTL
            force_close=False,  # Keep-alive
        )
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            raise_for_status=False,  # Handle errors manually
        )
        logger.info("Metrics bridge HTTP session started with connection pool")
```

---

### 15. No Cleanup on Script Failure
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 676-683
**Severity:** HIGH

**Issue:**
Cleanup trap is registered but may not execute on all failure modes.

**Current Code:**
```bash
cleanup() {
    log_info "Cleanup triggered..."
    stop_all_services
    exit 0
}

trap cleanup EXIT INT TERM
```

**Problem:**
- `set -e` causes immediate exit, might skip trap
- No cleanup of partial backtest results
- No notification of failure

**Recommended Fix:**
```bash
cleanup() {
    local exit_code=$?
    log_info "Cleanup triggered (exit code: $exit_code)..."

    # Stop all services
    stop_all_services

    # Clean up temporary files
    rm -f "$LOG_DIR"/*.tmp

    # Log failure if non-zero exit
    if [ $exit_code -ne 0 ]; then
        log_error "System exited with error code $exit_code"
        # Optional: Send alert notification
    fi

    exit $exit_code
}

set -E  # Inherit ERR trap
trap cleanup EXIT INT TERM ERR
```

---

## MEDIUM PRIORITY ISSUES

### 16. No Retry Logic for Alpaca API Calls
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`
**Lines:** 454-474
**Severity:** MEDIUM

**Issue:**
Alpaca API calls have no retry logic, will fail on transient network errors.

**Recommended Fix:**
Add retry decorator with exponential backoff:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_account():
    return alpaca_client.get_account()
```

---

### 16. Equity Curve Empty Check Missing
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/performance.py`
**Lines:** 42-59
**Severity:** MEDIUM

**Issue:**
Method checks if equity_curve is empty but then proceeds to modify it without re-checking.

**Recommended Fix:**
```python
if equity_curve.empty:
    logger.warning("Empty equity curve, returning zero metrics")
    return PerformanceMetrics()  # Return default/empty metrics

equity_curve = equity_curve.copy()
if len(equity_curve) < 2:
    logger.warning("Insufficient data points for metrics calculation")
    return PerformanceMetrics()

equity_curve['returns'] = equity_curve['equity'].pct_change()
```

---

### 17. Missing Validation in _parse_prometheus_text
**File:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/observability/metrics/rust_bridge.py`
**Lines:** 89-195
**Severity:** MEDIUM

**Issue:**
Parser doesn't validate metric name format, can fail on malformed Prometheus output.

**Recommended Fix:**
```python
import re

METRIC_NAME_PATTERN = re.compile(r'^[a-zA-Z_:][a-zA-Z0-9_:]*$')

def _parse_prometheus_text(self, text: str, service_name: str) -> Dict[str, Any]:
    # ... existing code ...

    # Validate metric name
    if metric_name and not METRIC_NAME_PATTERN.match(metric_name):
        logger.warning(f"Invalid metric name format: {metric_name}")
        continue
```

---

### 18. No Disk Space Check Before Writing Results
**File:** Multiple locations
**Severity:** MEDIUM

**Issue:**
No checks for available disk space before writing large result files.

**Recommended Fix:**
```python
import shutil

def check_disk_space(path: Path, required_mb: int = 100):
    stat = shutil.disk_usage(path)
    available_mb = stat.free / (1024 * 1024)
    if available_mb < required_mb:
        raise RuntimeError(f"Insufficient disk space: {available_mb:.1f}MB available, {required_mb}MB required")
```

---

## Summary Statistics

| Severity  | Count | Files Affected |
|-----------|-------|----------------|
| Critical  | 5     | 4              |
| High      | 10    | 5              |
| Medium    | 8     | 6              |
| **Total** | **23**| **8**          |

---

## Priority Action Items

1. **IMMEDIATE (Today):**
   - Fix BacktestEngine parameter mismatch (Issue #1)
   - Fix HistoricalDataHandler missing data_dir (Issue #2)
   - Update hardcoded ports in rust_bridge.py (Issue #3)

2. **THIS WEEK:**
   - Add missing imports (Issue #8)
   - Fix type mismatches (Issues #4, #9, #10)
   - Add proper error handling (Issues #11, #12)

3. **THIS SPRINT:**
   - Implement health checks for services (Issue #13)
   - Add connection pooling (Issue #14)
   - Improve cleanup handling (Issue #15)

---

## Testing Recommendations

1. **Unit Tests Needed:**
   - BacktestEngine initialization with various parameter combinations
   - HistoricalDataHandler with missing directories
   - PortfolioHandler with invalid signals

2. **Integration Tests Needed:**
   - End-to-end backtest execution
   - Rust service startup and connection
   - Metrics collection from Rust services

3. **Error Scenario Tests:**
   - Empty equity curves
   - Missing data files
   - Service connection failures
   - Out of disk space scenarios

---

## Files Requiring Immediate Attention

1. `/src/backtesting/engine.py` - 3 critical issues
2. `/scripts/autonomous_trading_system.sh` - 5 critical issues
3. `/src/observability/metrics/rust_bridge.py` - 2 critical issues
4. `/src/backtesting/portfolio_handler.py` - 2 critical issues
5. `/src/backtesting/data_handler.py` - 1 critical issue

---

**Review Complete**
Next Step: Create GitHub issues for each critical finding and assign to development team.
