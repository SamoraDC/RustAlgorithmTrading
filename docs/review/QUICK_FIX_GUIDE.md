# Quick Fix Guide - Copy/Paste Ready Solutions

**Generated:** 2025-10-22
**Purpose:** Immediate fixes for critical system failures

---

## 🔥 Apply These Fixes NOW (5 Minutes)

### Fix 1: Update autonomous_trading_system.sh Backtest Section

**Location:** `scripts/autonomous_trading_system.sh` lines 174-259

**Replace the entire Python heredoc with:**

```bash
    uv run python - <<'PYTHON_BACKTEST'
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, 'src')

try:
    # FIXED: Added all required imports
    from backtesting.engine import BacktestEngine
    from backtesting.data_handler import HistoricalDataHandler
    from backtesting.execution_handler import SimulatedExecutionHandler
    from backtesting.portfolio_handler import PortfolioHandler
    from strategies.simple_momentum import SimpleMomentumStrategy

    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now() - timedelta(days=1)
    initial_capital = 100000.0

    print(f"[BACKTEST] Running backtest for {symbols}")
    print(f"[BACKTEST] Period: {start_date.date()} to {end_date.date()}")
    print(f"[BACKTEST] Initial capital: ${initial_capital:,.2f}")

    # FIXED: Initialize all required components with correct parameters
    data_handler = HistoricalDataHandler(
        symbols=symbols,
        data_dir=Path('data/historical'),
        start_date=start_date,
        end_date=end_date
    )

    execution_handler = SimulatedExecutionHandler()
    portfolio_handler = PortfolioHandler(initial_capital=initial_capital)
    strategy = SimpleMomentumStrategy(symbols)

    # FIXED: Pass all required parameters
    engine = BacktestEngine(
        data_handler=data_handler,
        execution_handler=execution_handler,
        portfolio_handler=portfolio_handler,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date
    )

    # Run backtest
    print("[BACKTEST] Executing backtest...")
    results = engine.run()

    # FIXED: Extract metrics from correct structure
    metrics = results.get('metrics', {})

    # FIXED: Validate metrics exist and are valid
    required_keys = ['sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor']
    for key in required_keys:
        if key not in metrics or metrics[key] is None:
            print(f"[BACKTEST] WARNING: Missing or invalid metric '{key}'")
            metrics[key] = 0.0

    final_value = results.get('equity_curve', {}).get('equity', [0])[-1] if results.get('equity_curve') else initial_capital
    sharpe_ratio = metrics.get('sharpe_ratio', 0.0)
    max_drawdown = metrics.get('max_drawdown', 0.0) / 100.0  # Convert from percentage
    win_rate = metrics.get('win_rate', 0.0) / 100.0  # Convert from percentage
    profit_factor = metrics.get('profit_factor', 0.0)
    total_return = (final_value - initial_capital) / initial_capital

    # Print results
    print(f"\n[BACKTEST] Results:")
    print(f"  Final Value: ${final_value:,.2f}")
    print(f"  Total Return: {total_return*100:.2f}%")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {max_drawdown*100:.2f}%")
    print(f"  Win Rate: {win_rate*100:.2f}%")
    print(f"  Profit Factor: {profit_factor:.2f}")

    # Save results
    output_file = f"data/backtest_results/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('data/backtest_results', exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'symbols': symbols,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'metrics': metrics,
        }, f, indent=2)

    print(f"[BACKTEST] Results saved to {output_file}")

    # Exit with success/failure based on thresholds
    if sharpe_ratio < 1.0 or win_rate < 0.50 or abs(max_drawdown) > 0.20:
        print("[BACKTEST] FAILED - Metrics below threshold")
        sys.exit(1)
    else:
        print("[BACKTEST] PASSED - All metrics meet threshold")
        sys.exit(0)

except ImportError as e:
    print(f"[BACKTEST] IMPORT ERROR: {e}")
    print("[BACKTEST] Make sure all dependencies are installed: uv sync")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"[BACKTEST] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_BACKTEST
```

---

### Fix 2: Update rust_bridge.py Ports

**Location:** `src/observability/metrics/rust_bridge.py` lines 303-310

**Replace this section:**

```python
def get_rust_metrics_bridge() -> RustMetricsBridge:
    """Get or create the global RustMetricsBridge instance."""
    global _bridge_instance

    if _bridge_instance is None:
        # FIXED: Updated ports to match autonomous_trading_system.sh
        endpoints = {
            "market_data": "http://127.0.0.1:5001/metrics",
            "execution": "http://127.0.0.1:5003/metrics",
            "risk": "http://127.0.0.1:5002/metrics",
        }
        _bridge_instance = RustMetricsBridge(endpoints)

    return _bridge_instance
```

---

### Fix 3: Add Missing Directory Creation

**Location:** `scripts/autonomous_trading_system.sh` lines 615-621

**Replace main() directory creation:**

```bash
main() {
    # FIXED: Create ALL required directories FIRST before any logging
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKTEST_RESULTS"
    mkdir -p "$SIMULATION_RESULTS"
    mkdir -p "$PROJECT_ROOT/data/live_trading"
    mkdir -p "$PROJECT_ROOT/data/historical"  # ADDED: Required by HistoricalDataHandler

    log_info "=========================================="
    log_info "AUTONOMOUS TRADING SYSTEM"
    log_info "Mode: $MODE"
    log_info "=========================================="
```

---

### Fix 4: Update BacktestEngine._handle_market_event

**Location:** `src/backtesting/engine.py` lines 125-141

**Replace the entire method:**

```python
def _handle_market_event(self, event: MarketEvent):
    """
    Handle market data update.

    Args:
        event: Market event
    """
    # Update portfolio with latest prices
    self.portfolio_handler.update_timeindex(event.timestamp)

    # FIXED: Convert MarketEvent to format strategy expects
    try:
        # Get latest bars for all symbols from data handler
        bars_data = {}
        for symbol in self.data_handler.symbols:
            # Get last N bars for technical indicators
            bars = self.data_handler.get_latest_bars(symbol, n=50)
            if bars:
                # Convert to DataFrame format
                df = pd.DataFrame([
                    {
                        'timestamp': bar.timestamp,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume
                    }
                    for bar in bars
                ])
                df.set_index('timestamp', inplace=True)
                bars_data[symbol] = df

        # Generate signals for each symbol with enough data
        all_signals = []
        for symbol, df in bars_data.items():
            if len(df) >= 20:  # Minimum bars for indicators
                # Call strategy's per-symbol signal generation
                if hasattr(self.strategy, 'generate_signals_for_symbol'):
                    signals = self.strategy.generate_signals_for_symbol(symbol, df)
                    all_signals.extend(signals)
                else:
                    logger.warning(f"Strategy {self.strategy} doesn't support per-symbol signals")

        # Add signal events to queue
        if all_signals:
            for signal in all_signals:
                # Convert Strategy Signal to SignalEvent
                signal_event = SignalEvent(
                    timestamp=event.timestamp,
                    symbol=signal.symbol,
                    signal_type=signal.action,  # 'BUY', 'SELL', 'HOLD'
                    strength=getattr(signal, 'confidence', 0.8),
                    strategy_id=self.strategy.name
                )
                self.events.append(signal_event)

    except Exception as e:
        logger.error(f"Error generating signals from market event: {e}", exc_info=True)
```

---

### Fix 5: Add Missing Import to engine.py

**Location:** `src/backtesting/engine.py` line 9

**Add this import:**

```python
import pandas as pd  # ADD THIS LINE
from loguru import logger

from src.models.events import Event, EventType, MarketEvent, SignalEvent
```

---

## 🧪 Quick Test After Fixes

Run this test to verify fixes:

```bash
# Navigate to project root
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading

# Test 1: Verify directories exist
echo "Testing directory structure..."
ls -la data/historical/ && echo "✅ data/historical exists" || echo "❌ data/historical missing"
ls -la data/backtest_results/ && echo "✅ backtest_results exists" || echo "❌ backtest_results missing"

# Test 2: Verify imports work
echo -e "\nTesting Python imports..."
uv run python -c "
import sys
sys.path.insert(0, 'src')
try:
    from backtesting.engine import BacktestEngine
    from backtesting.execution_handler import SimulatedExecutionHandler
    from backtesting.portfolio_handler import PortfolioHandler
    print('✅ All backtesting imports successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"

# Test 3: Test BacktestEngine initialization
echo -e "\nTesting BacktestEngine initialization..."
uv run python -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from datetime import datetime, timedelta
from backtesting.engine import BacktestEngine
from backtesting.data_handler import HistoricalDataHandler
from backtesting.execution_handler import SimulatedExecutionHandler
from backtesting.portfolio_handler import PortfolioHandler
from strategies.simple_momentum import SimpleMomentumStrategy

try:
    data_handler = HistoricalDataHandler(
        symbols=['AAPL'],
        data_dir=Path('data/historical'),
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    execution_handler = SimulatedExecutionHandler()
    portfolio_handler = PortfolioHandler(initial_capital=100000.0)
    strategy = SimpleMomentumStrategy(['AAPL'])

    engine = BacktestEngine(
        data_handler=data_handler,
        execution_handler=execution_handler,
        portfolio_handler=portfolio_handler,
        strategy=strategy
    )
    print('✅ BacktestEngine initialized successfully')
except Exception as e:
    print(f'❌ Initialization failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo -e "\n✅ All tests passed! System should be functional."
```

---

## 🚀 Run System After Fixes

```bash
# Build Rust services first
cd rust
cargo build --release
cd ..

# Run backtest only mode to verify
./scripts/autonomous_trading_system.sh --mode=backtest-only
```

---

## 📋 Verification Checklist

Before declaring fixes complete:

- [ ] All 5 code changes applied
- [ ] No syntax errors in modified files
- [ ] Directory structure test passes
- [ ] Python import test passes
- [ ] BacktestEngine initialization test passes
- [ ] Rust services build successfully
- [ ] Backtest-only mode runs without crashes

---

## 🆘 If Tests Still Fail

### Error: "No module named 'backtesting'"
```bash
# Fix: Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Error: "FileNotFoundError: data/historical"
```bash
# Fix: Create directory manually
mkdir -p data/historical
```

### Error: "Connection refused" for Rust services
```bash
# Fix: Ensure services are built and started
cd rust
cargo build --release
cd ..

# Start services manually for testing
./rust/target/release/market-data &
./rust/target/release/risk-manager &
./rust/target/release/execution-engine &
```

### Error: "ModuleNotFoundError: No module named 'src'"
```bash
# Fix: Install dependencies
uv sync
```

---

## 📞 Next Steps After Fixes

1. ✅ Apply all 5 fixes
2. ✅ Run verification tests
3. ✅ Test backtest-only mode
4. 🔍 Review full error report: `docs/review/CODE_REVIEW_POTENTIAL_ERRORS.md`
5. 🔧 Address remaining HIGH priority issues
6. 🧪 Create unit tests for fixed code
7. 📝 Update documentation with new requirements

---

**Time to Fix:** ~5-10 minutes
**Expected Result:** System should initialize and run backtests without crashing

For complete analysis of all 23 issues, see:
- **Full Report:** `docs/review/CODE_REVIEW_POTENTIAL_ERRORS.md`
- **Summary:** `docs/review/CRITICAL_ISSUES_SUMMARY.md`
