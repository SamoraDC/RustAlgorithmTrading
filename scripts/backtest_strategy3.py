#!/usr/bin/env python3
"""
Test Strategy 3: Mean Reversion Strategy using Bollinger Bands
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.mean_reversion import MeanReversion
from src.backtesting.engine import BacktestEngine
from src.backtesting.data_handler import HistoricalDataHandler
from src.backtesting.execution_handler import SimulatedExecutionHandler
from src.backtesting.portfolio_handler import PortfolioHandler, PercentageOfEquitySizer


def run_strategy3_test():
    """Run Strategy 3 backtest with Mean Reversion"""
    logger.info("=" * 80)
    logger.info("STRATEGY 3 TEST: Mean Reversion (Bollinger Bands)")
    logger.info("=" * 80)

    # Create mean reversion strategy
    strategy = MeanReversion(
        bb_period=20,
        bb_std=2.0,
        position_size=0.15,
        stop_loss_pct=0.02,
        take_profit_pct=0.03,
        touch_threshold=1.001,  # 0.1% tolerance for band touches
    )

    logger.info(f"Strategy: {strategy.name}")
    logger.info(f"Parameters: {strategy.parameters}")

    # Define test parameters
    # Use only symbols we have data for
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    start_date = datetime(2024, 10, 1)  # Use recent data we have
    end_date = datetime(2024, 12, 31)
    initial_capital = 100000.0

    logger.info(f"\nBacktest Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")

    # Initialize components
    data_dir = project_root / 'data' / 'historical'
    data_handler = HistoricalDataHandler(
        symbols=symbols,
        data_dir=data_dir,
        start_date=start_date,
        end_date=end_date
    )

    execution_handler = SimulatedExecutionHandler()

    portfolio_handler = PortfolioHandler(
        initial_capital=initial_capital,
        position_sizer=PercentageOfEquitySizer(0.15),
        data_handler=data_handler
    )

    # Create engine
    engine = BacktestEngine(
        data_handler=data_handler,
        execution_handler=execution_handler,
        portfolio_handler=portfolio_handler,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date
    )

    # Run backtest
    logger.info("\nRunning backtest...")
    results = engine.run()

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("STRATEGY 3 RESULTS: Mean Reversion")
    logger.info("=" * 80)

    metrics = results.get('metrics', {})
    logger.info(f"\nPerformance Metrics:")
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            logger.info(f"  {key}: {value}")

    # Save results
    output_dir = project_root / "data" / "backtest_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "strategy3_mean_reversion.json"

    # Prepare JSON-serializable results
    json_results = {
        'strategy': 'Mean Reversion (Bollinger Bands)',
        'timestamp': datetime.now().isoformat(),
        'parameters': strategy.parameters,
        'symbols': symbols,
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'initial_capital': initial_capital,
        'metrics': {}
    }

    # Convert metrics to JSON-serializable format
    for key, value in metrics.items():
        if isinstance(value, (int, float, str, bool, type(None))):
            json_results['metrics'][key] = value
        elif isinstance(value, pd.Timestamp):
            json_results['metrics'][key] = value.isoformat()
        else:
            json_results['metrics'][key] = str(value)

    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2)

    logger.info(f"\nResults saved to: {output_file}")

    return results, metrics


def create_summary_report(results, metrics):
    """Create markdown summary report"""
    if results is None:
        logger.error("No results to report")
        return

    total_return = metrics.get('total_return', 0)
    sharpe_ratio = metrics.get('sharpe_ratio', 0)
    max_drawdown = metrics.get('max_drawdown', 0)
    total_trades = metrics.get('total_trades', 0)
    winning_trades = metrics.get('winning_trades', 0)
    losing_trades = metrics.get('losing_trades', 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    report = f"""# Strategy 3 Results: Mean Reversion Strategy

## Test Configuration
- **Strategy**: Mean Reversion (Bollinger Bands)
- **Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Logic**:
  - ✅ BUY when price touches lower band (2σ) → Expect reversion UP
  - ✅ SELL when price touches upper band (2σ) → Expect reversion DOWN
  - ✅ EXIT when price returns to middle band (20 SMA)
  - ✅ Stop-loss: -2% | Take-profit: +3%

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total Return | {total_return:.2%} |
| Sharpe Ratio | {sharpe_ratio:.2f} |
| Max Drawdown | {max_drawdown:.2%} |
| Win Rate | {win_rate:.2%} |

## Trade Statistics

| Statistic | Value |
|-----------|-------|
| Total Trades | {total_trades} |
| Winning Trades | {winning_trades} |
| Losing Trades | {losing_trades} |

## Analysis

### Expected vs Actual
- **Expected Trades**: 50-100 trades per year (mean reversion is more frequent)
- **Actual Trades**: {total_trades}
- **Expected Win Rate**: 60-70% (works well in sideways markets)
- **Actual Win Rate**: {win_rate:.2%}

### Strategy Characteristics
- Mean reversion excels in **range-bound markets**
- More frequent trades than momentum strategies
- Lower average profit per trade, but higher win rate
- {'✅ Performance consistent with expectations' if total_trades > 40 else '⚠️ Fewer trades than expected (possibly trending market)'}

## Conclusions

### Signal Generation
- {'✅ SUCCESS: Generated frequent trading opportunities' if total_trades > 40 else '⚠️ LIMITED: Market may be trending (not ideal for mean reversion)'}

### Win Rate
- {'✅ EXCELLENT: High win rate (>60%)' if win_rate > 0.6 else '⚠️ MODERATE: Win rate below expectations'}

### Risk Management
- Stop-loss protection: -2%
- Take-profit target: +3%
- Risk/Reward Ratio: 1.5:1

### Overall Assessment
{'✅ Strategy 3 performs well in current market conditions' if total_return > 0 and total_trades > 30 else '⚠️ Strategy 3 shows market conditions not ideal for mean reversion'}

## Comparison with Other Strategies

### vs Momentum Strategies (Strategy 1 & 2):
- **Trade Frequency**: Mean reversion typically 2-3x more trades
- **Win Rate**: Mean reversion typically higher (60-70% vs 50-60%)
- **Avg Profit Per Trade**: Momentum strategies typically higher
- **Market Conditions**:
  - Momentum: Works best in **trending markets**
  - Mean Reversion: Works best in **sideways/range-bound markets**

### Best Use Case:
- Use Strategy 3 when market is **consolidating** or **range-bound**
- Use Strategies 1/2 when market shows **strong trends**
- Consider combining both for **all-weather portfolio**

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Save report
    docs_dir = Path(__file__).parent.parent / "docs" / "strategy_comparison"
    docs_dir.mkdir(parents=True, exist_ok=True)

    report_file = docs_dir / "strategy3_results.md"
    with open(report_file, 'w') as f:
        f.write(report)

    logger.info(f"Summary report saved to: {report_file}")


if __name__ == "__main__":
    try:
        # Run backtest
        results, metrics = run_strategy3_test()

        # Create summary report
        create_summary_report(results, metrics)

        logger.info("\nStrategy 3 test complete!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Strategy 3 backtest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
