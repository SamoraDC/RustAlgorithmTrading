#!/usr/bin/env python3
"""
Test Strategy 2: Simplified Momentum Strategy
Removes SMA filter and volume confirmation to test if over-optimization is the issue
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.momentum_simplified import SimplifiedMomentumStrategy
from src.backtesting.engine import BacktestEngine
from src.backtesting.portfolio_handler import PortfolioHandler
from src.backtesting.data_handler import HistoricalDataHandler
from src.backtesting.execution_handler import SimulatedExecutionHandler
from src.api.alpaca_client import AlpacaClient


def run_strategy2_test():
    """Run Strategy 2 backtest with simplified momentum"""
    logger.info("=" * 80)
    logger.info("STRATEGY 2 TEST: Simplified Momentum (No SMA, No Volume)")
    logger.info("=" * 80)

    # Initialize components
    alpaca_client = AlpacaClient()

    # Create simplified strategy
    strategy = SimplifiedMomentumStrategy(
        rsi_period=14,
        ema_fast=12,
        ema_slow=26,
        macd_signal=9,
        macd_histogram_threshold=0.0005,
        position_size=0.15,
        stop_loss_pct=0.02,
        take_profit_pct=0.03,
        min_holding_period=10,
        use_trailing_stop=True,
        trailing_stop_pct=0.015,
    )

    logger.info(f"Strategy: {strategy.name}")
    logger.info(f"Parameters: {strategy.parameters}")

    # Define test parameters
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    initial_capital = 100000.0

    logger.info(f"\nBacktest Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")

    # Load market data
    logger.info("\nLoading market data...")
    market_data = {}
    for symbol in symbols:
        try:
            data = alpaca_client.get_historical_bars(
                symbol=symbol,
                start=start_date,
                end=end_date
            )
            if data is not None and len(data) > 0:
                market_data[symbol] = data
                logger.info(f"  {symbol}: {len(data)} bars loaded")
            else:
                logger.warning(f"  {symbol}: No data available")
        except Exception as e:
            logger.error(f"  {symbol}: Error loading data - {e}")

    if not market_data:
        logger.error("No market data loaded. Cannot proceed with backtest.")
        return None

    # Run backtest
    logger.info("\nRunning backtest...")

    # Initialize backtest components
    data_handler = HistoricalDataHandler(symbols, market_data)
    portfolio_handler = PortfolioHandler(initial_capital=initial_capital)
    execution_handler = SimulatedExecutionHandler()

    engine = BacktestEngine(
        data_handler=data_handler,
        execution_handler=execution_handler,
        portfolio_handler=portfolio_handler,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date
    )

    results = engine.run()

    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("STRATEGY 2 RESULTS: Simplified Momentum")
    logger.info("=" * 80)

    metrics = results.get('metrics', {})
    logger.info(f"\nPerformance Metrics:")
    logger.info(f"  Total Return: {metrics.get('total_return', 0):.2%}")
    logger.info(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    logger.info(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
    logger.info(f"  Win Rate: {metrics.get('win_rate', 0):.2%}")

    trade_stats = results.get('trade_statistics', {})
    logger.info(f"\nTrade Statistics:")
    logger.info(f"  Total Trades: {trade_stats.get('total_trades', 0)}")
    logger.info(f"  Winning Trades: {trade_stats.get('winning_trades', 0)}")
    logger.info(f"  Losing Trades: {trade_stats.get('losing_trades', 0)}")
    logger.info(f"  Avg Win: {trade_stats.get('avg_win', 0):.2%}")
    logger.info(f"  Avg Loss: {trade_stats.get('avg_loss', 0):.2%}")

    # Save results
    output_dir = project_root / "data" / "backtest_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "strategy2_simplified.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {output_file}")

    return results


def create_summary_report(results):
    """Create markdown summary report"""
    if results is None:
        logger.error("No results to report")
        return

    metrics = results.get('metrics', {})
    trade_stats = results.get('trade_statistics', {})

    report = f"""# Strategy 2 Results: Simplified Momentum Strategy

## Test Configuration
- **Strategy**: Simplified Momentum (No SMA, No Volume)
- **Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Changes Made**:
  - ✅ Removed 50 SMA trend filter
  - ✅ Removed volume confirmation
  - ✅ Kept RSI 50 crossings
  - ✅ Kept MACD histogram threshold (0.0005)
  - ✅ Kept stop-loss and take-profit

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total Return | {metrics.get('total_return', 0):.2%} |
| Sharpe Ratio | {metrics.get('sharpe_ratio', 0):.2f} |
| Max Drawdown | {metrics.get('max_drawdown', 0):.2%} |
| Win Rate | {metrics.get('win_rate', 0):.2%} |
| Final Portfolio Value | ${metrics.get('final_value', 0):,.2f} |

## Trade Statistics

| Statistic | Value |
|-----------|-------|
| Total Trades | {trade_stats.get('total_trades', 0)} |
| Winning Trades | {trade_stats.get('winning_trades', 0)} |
| Losing Trades | {trade_stats.get('losing_trades', 0)} |
| Average Win | {trade_stats.get('avg_win', 0):.2%} |
| Average Loss | {trade_stats.get('avg_loss', 0):.2%} |
| Profit Factor | {trade_stats.get('profit_factor', 0):.2f} |

## Analysis

### Expected vs Actual
- **Expected Trades**: 20-50 trades
- **Actual Trades**: {trade_stats.get('total_trades', 0)}
- **Expected Win Rate**: >50%
- **Actual Win Rate**: {metrics.get('win_rate', 0):.2%}

### Comparison to Current Strategy
- Current strategy generates ~5 trades
- Simplified strategy generates {trade_stats.get('total_trades', 0)} trades
- {'✅ MORE signals as expected' if trade_stats.get('total_trades', 0) > 10 else '❌ Still too few signals'}

## Conclusions

### Signal Generation
- {'✅ SUCCESS: Removing filters increased trade frequency' if trade_stats.get('total_trades', 0) > 10 else '❌ FAILED: Still generating too few trades'}

### Win Rate
- {'✅ SUCCESS: Win rate improved (>50%)' if metrics.get('win_rate', 0) > 0.5 else '⚠️ WARNING: Win rate still below 50%'}

### Overall Assessment
{'✅ Strategy 2 shows improvement - simplified approach generates more trades' if trade_stats.get('total_trades', 0) > 10 else '❌ Strategy 2 did not solve the issue - need to investigate data quality'}

## Next Steps
1. {'Compare with Strategy 1 results' if trade_stats.get('total_trades', 0) > 10 else 'Investigate data loading and validation'}
2. {'Test on longer time period' if trade_stats.get('total_trades', 0) > 10 else 'Check if RSI/MACD calculations are correct'}
3. {'Consider Strategy 3 if needed' if trade_stats.get('total_trades', 0) > 10 else 'Verify market data has sufficient volatility'}

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Save report
    docs_dir = Path(__file__).parent.parent / "docs" / "strategy_comparison"
    docs_dir.mkdir(parents=True, exist_ok=True)

    report_file = docs_dir / "strategy2_results.md"
    with open(report_file, 'w') as f:
        f.write(report)

    logger.info(f"Summary report saved to: {report_file}")


if __name__ == "__main__":
    # Run backtest
    results = run_strategy2_test()

    # Create summary report
    create_summary_report(results)

    logger.info("\nStrategy 2 test complete!")
