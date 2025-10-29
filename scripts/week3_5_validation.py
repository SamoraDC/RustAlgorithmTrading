#!/usr/bin/env python3
"""
Week 3.5 Validation Backtest
=============================

Emergency validation after re-enabling mean reversion strategy.

CHANGES IN WEEK 3.5:
- ✅ Mean reversion RE-ENABLED (was incorrectly disabled)
- ✅ RSI zones moderated to 58-82 (from 60-80)
- ✅ SHORT signals remain disabled

TARGET METRICS:
- Win Rate: 38-42% (from 33.3% Week 2, 26.7% Week 3)
- Sharpe Ratio: >0.3 (from 0.015 Week 2, -0.378 Week 3)
- Total Trades: 35-50 (from 69 Week 2, 15 Week 3)
- Total Return: >+2% (from +4.21% Week 2, -25.7% Week 3)
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

from src.strategies.momentum import MomentumStrategy
from src.strategies.base import SignalType
from src.api.alpaca_client import AlpacaClient
import numpy as np


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


def run_week35_validation():
    """Run Week 3.5 validation backtest"""

    logger.info("=" * 80)
    logger.info("WEEK 3.5 VALIDATION BACKTEST")
    logger.info("Emergency validation after mean reversion re-enabled")
    logger.info("=" * 80)

    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    initial_capital = 100000.0
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months

    logger.info(f"Testing period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Initial capital: ${initial_capital:,.2f}")
    logger.info("")

    # Initialize Alpaca client
    alpaca_client = AlpacaClient()

    # Initialize strategy
    logger.info("Initializing Week 3.5 Momentum Strategy...")
    strategy = MomentumStrategy()

    logger.info("Strategy parameters:")
    for key, value in strategy.parameters.items():
        logger.info(f"  {key}: {value}")
    logger.info("")

    # Verify critical settings
    logger.info("WEEK 3.5 CONFIGURATION VERIFICATION:")
    logger.info(f"  Mean Reversion Enabled: {strategy.parameters.get('mean_reversion_enabled', False)}")
    logger.info(f"  RSI Lower Bound: {strategy.parameters.get('rsi_lower', 'N/A')}")
    logger.info(f"  RSI Upper Bound: {strategy.parameters.get('rsi_upper', 'N/A')}")
    logger.info(f"  Short Signals Enabled: {strategy.parameters.get('allow_short', False)}")
    logger.info("")

    # Generate signals for all symbols
    logger.info("Generating signals...")
    all_signals = []
    all_data = {}

    for symbol in symbols:
        try:
            # Load data
            data = alpaca_client.get_historical_bars(
                symbol=symbol,
                start=start_date,
                end=end_date
            )

            if data is None or len(data) == 0:
                logger.warning(f"  ✗ {symbol}: No data")
                continue

            # Set symbol attribute
            data.attrs['symbol'] = symbol
            all_data[symbol] = data
            logger.info(f"  ✓ {symbol}: {len(data)} bars")

            # Generate signals
            signals = strategy.generate_signals(data)
            all_signals.extend(signals)
            logger.info(f"     Generated {len(signals)} signals for {symbol}")

        except Exception as e:
            logger.error(f"  Error processing {symbol}: {e}")

    logger.info(f"Total signals generated: {len(all_signals)}")
    logger.info("")

    # Calculate metrics
    results = calculate_metrics(all_signals, all_data)

    # Display results
    logger.info("=" * 80)
    logger.info("WEEK 3.5 VALIDATION RESULTS")
    logger.info("=" * 80)

    if results and results.get('total_signals', 0) > 0:
        total_return = results.get('total_return', 0)
        sharpe_ratio = results.get('sharpe_ratio', 0)
        max_drawdown = results.get('max_drawdown', 0)
        win_rate = results.get('win_rate', 0)
        total_trades = results.get('total_trades', 0)
        winning_trades = results.get('winning_trades', 0)
        losing_trades = results.get('losing_trades', 0)
        avg_win = results.get('avg_win', 0)
        avg_loss = results.get('avg_loss', 0)
        final_value = results.get('final_value', 0)

        logger.info(f"Total Return: {total_return:.2%}")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: {max_drawdown:.2%}")
        logger.info(f"Win Rate: {win_rate:.2%}")
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Winning Trades: {winning_trades}")
        logger.info(f"Losing Trades: {losing_trades}")
        logger.info(f"Average Win: {avg_win:.2%}")
        logger.info(f"Average Loss: {avg_loss:.2%}")
        logger.info(f"Final Portfolio Value: ${final_value:,.2f}")
        logger.info("")

        # Analyze trade breakdown from signals
        momentum_long_trades = 0
        mean_reversion_trades = 0
        short_trades = 0

        for signal in all_signals:
            if signal.signal_type == SignalType.LONG:
                signal_desc = str(signal.metadata.get('signal_description', '')).upper()
                if 'MEAN_REVERSION' in signal_desc or 'RSI_REVERSAL' in signal_desc:
                    mean_reversion_trades += 1
                else:
                    momentum_long_trades += 1
            elif signal.signal_type == SignalType.SHORT:
                short_trades += 1

        logger.info("TRADE BREAKDOWN BY TYPE:")
        logger.info(f"  Momentum LONG trades: {momentum_long_trades}")
        logger.info(f"  Mean Reversion trades: {mean_reversion_trades}")
        logger.info(f"  SHORT trades: {short_trades}")
        logger.info("")

        # Compare to Week 2 and Week 3
        logger.info("=" * 80)
        logger.info("COMPARISON TO PREVIOUS WEEKS")
        logger.info("=" * 80)

        week2_metrics = {
            'win_rate': 0.333,
            'sharpe': 0.015,
            'trades': 69,
            'return': 0.0421
        }

        week3_metrics = {
            'win_rate': 0.267,
            'sharpe': -0.378,
            'trades': 15,
            'return': -0.257
        }

        logger.info("                 Week 2    Week 3    Week 3.5   Target")
        logger.info("-" * 80)
        logger.info(f"Win Rate:        {week2_metrics['win_rate']:.1%}     {week3_metrics['win_rate']:.1%}     {win_rate:.1%}      38-42%")
        logger.info(f"Sharpe Ratio:    {week2_metrics['sharpe']:.3f}    {week3_metrics['sharpe']:.3f}    {sharpe_ratio:.3f}      >0.3")
        logger.info(f"Total Trades:    {week2_metrics['trades']}       {week3_metrics['trades']}        {total_trades}         35-50")
        logger.info(f"Total Return:    {week2_metrics['return']:.2%}    {week3_metrics['return']:.1%}    {total_return:.2%}     >+2%")
        logger.info("")

        # Target validation
        logger.info("=" * 80)
        logger.info("TARGET VALIDATION")
        logger.info("=" * 80)

        targets_met = 0
        total_targets = 0

        # Win rate
        total_targets += 1
        if 0.38 <= win_rate <= 0.42:
            logger.success(f"✓ Win Rate: {win_rate:.1%} - TARGET MET!")
            targets_met += 1
        elif win_rate >= 0.38:
            logger.info(f"✓ Win Rate: {win_rate:.1%} - Above target range")
            targets_met += 1
        else:
            logger.warning(f"✗ Win Rate: {win_rate:.1%} - Below target (need {0.38 - win_rate:.1%} more)")

        # Sharpe ratio
        total_targets += 1
        if sharpe_ratio >= 0.3:
            logger.success(f"✓ Sharpe Ratio: {sharpe_ratio:.2f} - TARGET MET!")
            targets_met += 1
        else:
            logger.warning(f"✗ Sharpe Ratio: {sharpe_ratio:.2f} - Below target (need {0.3 - sharpe_ratio:.2f} more)")

        # Total trades
        total_targets += 1
        if 35 <= total_trades <= 50:
            logger.success(f"✓ Total Trades: {total_trades} - TARGET MET!")
            targets_met += 1
        elif total_trades < 35:
            logger.warning(f"✗ Total Trades: {total_trades} - Below target (need {35 - total_trades} more)")
        else:
            logger.warning(f"✗ Total Trades: {total_trades} - Above target ({total_trades - 50} over)")

        # Total return
        total_targets += 1
        if total_return >= 0.02:
            logger.success(f"✓ Total Return: {total_return:.2%} - TARGET MET!")
            targets_met += 1
        else:
            logger.warning(f"✗ Total Return: {total_return:.2%} - Below target (need {0.02 - total_return:.2%} more)")

        # Configuration checks
        total_targets += 1
        if mean_reversion_trades > 0:
            logger.success(f"✓ Mean Reversion: {mean_reversion_trades} trades - ENABLED!")
            targets_met += 1
        else:
            logger.error(f"✗ Mean Reversion: {mean_reversion_trades} trades - NOT WORKING!")

        total_targets += 1
        if short_trades == 0:
            logger.success(f"✓ SHORT Signals: {short_trades} trades - CORRECTLY DISABLED!")
            targets_met += 1
        else:
            logger.error(f"✗ SHORT Signals: {short_trades} trades - SHOULD BE ZERO!")

        logger.info("")
        logger.info(f"Targets Met: {targets_met}/{total_targets} ({targets_met/total_targets:.0%})")
        logger.info("")

        # GO/NO-GO decision
        logger.info("=" * 80)
        logger.info("GO/NO-GO RECOMMENDATION FOR WEEK 4")
        logger.info("=" * 80)

        if win_rate >= 0.38 and sharpe_ratio >= 0.3 and total_return >= 0.02:
            logger.success("✅ GO TO WEEK 4 PAPER TRADING")
            logger.success("All critical targets met!")
            recommendation = "GO"
        elif win_rate >= 0.33 and sharpe_ratio >= 0.1 and total_return >= 0.0:
            logger.warning("⚠️ CONDITIONAL GO TO WEEK 4")
            logger.warning("Some targets met, monitor closely in paper trading")
            recommendation = "CONDITIONAL"
        else:
            logger.error("❌ NO-GO - DO NOT PROCEED TO WEEK 4")
            logger.error("Critical targets not met, additional fixes needed")
            recommendation = "NO-GO"

        logger.info("")

        # Save results
        output_dir = project_root / 'data' / 'backtest_results'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'week3.5_validation_{timestamp}.json'

        results_output = {
            'week': '3.5',
            'description': 'Validation after mean reversion re-enabled',
            'timestamp': timestamp,
            'metrics': {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'final_value': final_value,
                'total_signals': results.get('total_signals', 0),
                'entry_signals': results.get('entry_signals', 0),
                'exit_signals': results.get('exit_signals', 0)
            },
            'trade_breakdown': {
                'momentum_long': momentum_long_trades,
                'mean_reversion': mean_reversion_trades,
                'short': short_trades
            },
            'comparison': {
                'week2': week2_metrics,
                'week3': week3_metrics
            },
            'targets_met': f"{targets_met}/{total_targets}",
            'recommendation': recommendation,
            'signals': [
                {
                    'symbol': s.symbol,
                    'timestamp': s.timestamp.isoformat() if hasattr(s.timestamp, 'isoformat') else str(s.timestamp),
                    'signal_type': str(s.signal_type),
                    'price': float(s.price) if s.price else None,
                    'metadata': s.metadata
                } for s in all_signals
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(results_output, f, indent=2, default=str)

        logger.info(f"Results saved to: {output_file}")

        return results_output
    else:
        logger.error("Backtest failed to produce results")
        return None


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Also log to file
    output_dir = Path(__file__).parent.parent / 'data' / 'backtest_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f'week3.5_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logger.add(log_file, level="INFO")

    results = run_week35_validation()

    if results:
        sys.exit(0)
    else:
        sys.exit(1)
