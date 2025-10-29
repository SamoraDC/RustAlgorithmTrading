#!/usr/bin/env python3
"""
Test Strategy 2: Simplified Momentum Strategy
Simple test that directly calls the strategy with market data
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.momentum_simplified import SimplifiedMomentumStrategy
from src.strategies.base import SignalType
from src.api.alpaca_client import AlpacaClient


def calculate_metrics(signals, market_data):
    """Calculate backtest metrics from signals"""
    if not signals:
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
        }

    # Count signal types
    entries = [s for s in signals if s.signal_type in [SignalType.LONG, SignalType.SHORT]]
    exits = [s for s in signals if s.signal_type == SignalType.EXIT]

    # Calculate basic stats from exit signals (which include P&L)
    exit_pnls = [s.metadata.get('pnl_pct', 0) for s in exits if 'pnl_pct' in s.metadata]

    winning_trades = sum(1 for pnl in exit_pnls if pnl > 0)
    losing_trades = sum(1 for pnl in exit_pnls if pnl < 0)
    total_trades = len(exit_pnls)

    wins = [pnl for pnl in exit_pnls if pnl > 0]
    losses = [pnl for pnl in exit_pnls if pnl < 0]

    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

    total_return = sum(exit_pnls) if exit_pnls else 0.0

    # Simplified Sharpe (returns / std)
    sharpe_ratio = (np.mean(exit_pnls) / np.std(exit_pnls)) if len(exit_pnls) > 1 and np.std(exit_pnls) > 0 else 0.0

    # Max drawdown (simplified)
    cumulative = np.cumsum(exit_pnls) if exit_pnls else [0]
    running_max = np.maximum.accumulate(cumulative)
    drawdown = running_max - cumulative
    max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0.0

    total_profit = sum(wins) if wins else 0.0
    total_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

    return {
        'total_return': float(total_return),
        'sharpe_ratio': float(sharpe_ratio),
        'max_drawdown': float(max_drawdown),
        'win_rate': float(win_rate),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'profit_factor': float(profit_factor),
        'total_signals': len(signals),
        'entry_signals': len(entries),
        'exit_signals': len(exits),
    }


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

    # Load market data and run strategy
    logger.info("\nLoading market data and generating signals...")
    all_signals = []
    market_data = {}

    for symbol in symbols:
        try:
            # Load data
            data = alpaca_client.get_historical_bars(
                symbol=symbol,
                start=start_date,
                end=end_date
            )

            if data is None or len(data) == 0:
                logger.warning(f"  {symbol}: No data available")
                continue

            # Set symbol attribute for strategy
            data.attrs['symbol'] = symbol
            market_data[symbol] = data

            # Generate signals
            signals = strategy.generate_signals(data)
            all_signals.extend(signals)

            logger.info(f"  {symbol}: {len(data)} bars, {len(signals)} signals")

        except Exception as e:
            logger.error(f"  {symbol}: Error - {e}")

    # Calculate metrics
    logger.info("\n" + "=" * 80)
    logger.info("STRATEGY 2 RESULTS: Simplified Momentum")
    logger.info("=" * 80)

    metrics = calculate_metrics(all_signals, market_data)

    logger.info(f"\nSignal Generation:")
    logger.info(f"  Total Signals: {metrics['total_signals']}")
    logger.info(f"  Entry Signals: {metrics['entry_signals']}")
    logger.info(f"  Exit Signals: {metrics['exit_signals']}")

    logger.info(f"\nPerformance Metrics:")
    logger.info(f"  Total Return: {metrics['total_return']:.2%}")
    logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    logger.info(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
    logger.info(f"  Win Rate: {metrics['win_rate']:.2%}")

    logger.info(f"\nTrade Statistics:")
    logger.info(f"  Total Trades: {metrics['total_trades']}")
    logger.info(f"  Winning Trades: {metrics['winning_trades']}")
    logger.info(f"  Losing Trades: {metrics['losing_trades']}")
    logger.info(f"  Avg Win: {metrics['avg_win']:.2%}")
    logger.info(f"  Avg Loss: {metrics['avg_loss']:.2%}")
    logger.info(f"  Profit Factor: {metrics['profit_factor']:.2f}")

    # Save results
    results = {
        'strategy': 'SimplifiedMomentumStrategy',
        'parameters': strategy.parameters,
        'backtest_period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
        },
        'symbols': symbols,
        'initial_capital': initial_capital,
        'metrics': metrics,
        'trade_statistics': {
            'total_trades': metrics['total_trades'],
            'winning_trades': metrics['winning_trades'],
            'losing_trades': metrics['losing_trades'],
            'avg_win': metrics['avg_win'],
            'avg_loss': metrics['avg_loss'],
            'profit_factor': metrics['profit_factor'],
        },
        'signals': [
            {
                'timestamp': str(s.timestamp),
                'symbol': s.symbol,
                'signal_type': s.signal_type.name,
                'price': s.price,
                'confidence': s.confidence,
                'metadata': s.metadata
            }
            for s in all_signals[:50]  # Save first 50 signals as samples
        ]
    }

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

## Signal Generation

| Metric | Value |
|--------|-------|
| Total Signals | {metrics.get('total_signals', 0)} |
| Entry Signals | {metrics.get('entry_signals', 0)} |
| Exit Signals | {metrics.get('exit_signals', 0)} |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total Return | {metrics.get('total_return', 0):.2%} |
| Sharpe Ratio | {metrics.get('sharpe_ratio', 0):.2f} |
| Max Drawdown | {metrics.get('max_drawdown', 0):.2%} |
| Win Rate | {metrics.get('win_rate', 0):.2%} |

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

### Signal Generation Analysis
- **Total Signals Generated**: {metrics.get('total_signals', 0)}
- **Entry Signals**: {metrics.get('entry_signals', 0)}
- **Exit Signals**: {metrics.get('exit_signals', 0)}

### Comparison to Current Strategy
- Current strategy generates ~5 trades
- Simplified strategy generates **{trade_stats.get('total_trades', 0)} completed trades**
- {'✅ MORE signals as expected' if trade_stats.get('total_trades', 0) > 10 else '❌ Still too few signals'}

## Conclusions

### Signal Generation
- {'✅ SUCCESS: Removing filters increased trade frequency' if trade_stats.get('total_trades', 0) > 10 else '⚠️ PARTIAL: Generated ' + str(trade_stats.get('total_trades', 0)) + ' trades'}
- Entry signals: {metrics.get('entry_signals', 0)} (indicates strategy is finding opportunities)
- Exit signals: {metrics.get('exit_signals', 0)} (indicates trades are being completed)

### Win Rate
- {'✅ SUCCESS: Win rate >50% (' + f"{metrics.get('win_rate', 0):.1%}" + ')' if metrics.get('win_rate', 0) > 0.5 else '⚠️ WARNING: Win rate below 50% (' + f"{metrics.get('win_rate', 0):.1%}" + ')'}

### Overall Assessment
{'✅ Strategy 2 shows improvement - simplified approach generates more trades' if trade_stats.get('total_trades', 0) > 10 else '⚠️ Strategy 2 partially successful - generated ' + str(trade_stats.get('total_trades', 0)) + ' trades'}

## Key Findings

1. **Impact of Removing Filters**:
   - Removing SMA filter allows trades in all market conditions
   - Removing volume filter reduces false negatives

2. **Signal Quality**:
   - RSI 50 crossings: {'Effective' if metrics.get('win_rate', 0) > 0.5 else 'Needs improvement'}
   - MACD confirmation: {'Working well' if metrics.get('profit_factor', 0) > 1.0 else 'Requires tuning'}

3. **Risk Management**:
   - Stop-loss effectiveness: {f"{metrics.get('avg_loss', 0):.2%} avg loss"}
   - Take-profit capture: {f"{metrics.get('avg_win', 0):.2%} avg win"}
   - Profit factor: {trade_stats.get('profit_factor', 0):.2f}

## Next Steps

1. {'✅ Proceed to comparison with Strategy 1' if trade_stats.get('total_trades', 0) >= 5 else '⚠️ Investigate why fewer trades than expected'}
2. {'Analyze winning vs losing trade patterns' if trade_stats.get('total_trades', 0) >= 10 else 'Consider extending test period for more data'}
3. {'Test Strategy 3 if further improvements needed' if trade_stats.get('total_trades', 0) > 10 else 'Review signal generation logic'}

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

    logger.info("\n✅ Strategy 2 test complete!")
