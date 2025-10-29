#!/usr/bin/env python3
"""
Week 2 Validation Backtest
Tests all three strategies after Week 2 fixes and compares to baseline
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
from src.strategies.momentum_simplified import SimplifiedMomentumStrategy
from src.strategies.mean_reversion import MeanReversion
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


def run_strategy_backtest(strategy, strategy_name, symbols, start_date, end_date, initial_capital=100000.0):
    """Run backtest for a single strategy"""

    logger.info("=" * 80)
    logger.info(f"TESTING: {strategy_name}")
    logger.info("=" * 80)

    # Initialize Alpaca client
    alpaca_client = AlpacaClient()

    # Load data
    logger.info(f"Loading market data for {len(symbols)} symbols...")
    all_data = {}
    all_signals = []

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
            logger.error(f"  ✗ {symbol}: {e}")

    if not all_data:
        logger.error("No data loaded!")
        return None

    # Calculate metrics
    logger.info(f"\nCalculating metrics from {len(all_signals)} total signals...")
    results = calculate_metrics(all_signals, all_data)

    # Display results
    if results:
        logger.info("")
        logger.info("RESULTS:")
        logger.info(f"  Total Return: {results.get('total_return', 0):.2%}")
        logger.info(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        logger.info(f"  Max Drawdown: {results.get('max_drawdown', 0):.2%}")
        logger.info(f"  Win Rate: {results.get('win_rate', 0):.1%}")
        logger.info(f"  Total Trades: {results.get('total_trades', 0)}")
        logger.info(f"  Winning: {results.get('winning_trades', 0)} | Losing: {results.get('losing_trades', 0)}")
        logger.info(f"  Avg Win: {results.get('avg_win', 0):.2%} | Avg Loss: {results.get('avg_loss', 0):.2%}")
        logger.info(f"  Profit Factor: {results.get('profit_factor', 0):.2f}")

        # Validate against Week 2 success criteria
        logger.info("")
        logger.info("WEEK 2 SUCCESS CRITERIA:")

        win_rate = results.get('win_rate', 0)
        sharpe = results.get('sharpe_ratio', 0)
        total_trades = results.get('total_trades', 0)
        total_return = results.get('total_return', 0)
        max_dd = results.get('max_drawdown', 0)

        criteria_met = []

        if win_rate > 0.40:
            logger.success(f"  ✓ Win Rate: {win_rate:.1%} > 40%")
            criteria_met.append(True)
        else:
            logger.warning(f"  ✗ Win Rate: {win_rate:.1%} < 40% (FAIL)")
            criteria_met.append(False)

        if sharpe > 0.5:
            logger.success(f"  ✓ Sharpe Ratio: {sharpe:.2f} > 0.5")
            criteria_met.append(True)
        else:
            logger.warning(f"  ✗ Sharpe Ratio: {sharpe:.2f} < 0.5 (FAIL)")
            criteria_met.append(False)

        if 30 <= total_trades <= 40:
            logger.success(f"  ✓ Total Trades: {total_trades} (30-40)")
            criteria_met.append(True)
        elif total_trades < 30:
            logger.warning(f"  ✗ Total Trades: {total_trades} < 30 (LOW)")
            criteria_met.append(False)
        else:
            logger.warning(f"  ✗ Total Trades: {total_trades} > 40 (HIGH)")
            criteria_met.append(False)

        if total_return > 0:
            logger.success(f"  ✓ Total Return: {total_return:.2%} > 0%")
            criteria_met.append(True)
        else:
            logger.warning(f"  ✗ Total Return: {total_return:.2%} < 0% (FAIL)")
            criteria_met.append(False)

        if max_dd < 0.15:
            logger.success(f"  ✓ Max Drawdown: {max_dd:.1%} < 15%")
            criteria_met.append(True)
        else:
            logger.warning(f"  ✗ Max Drawdown: {max_dd:.1%} > 15% (HIGH)")
            criteria_met.append(False)

        results['criteria_met'] = sum(criteria_met)
        results['criteria_total'] = len(criteria_met)
        results['pass_rate'] = sum(criteria_met) / len(criteria_met)

        logger.info("")
        logger.info(f"CRITERIA MET: {sum(criteria_met)}/{len(criteria_met)} ({results['pass_rate']:.0%})")

    return results


def main():
    """Run Week 2 validation on all three strategies"""

    logger.info("=" * 80)
    logger.info("WEEK 2 VALIDATION - COMPREHENSIVE BACKTEST")
    logger.info("=" * 80)
    logger.info("")

    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    initial_capital = 100000.0
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months

    logger.info(f"Test Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    logger.info("")

    # Test all strategies
    all_results = {}

    # Strategy 1: Full Momentum (with all Week 2 fixes)
    strategy1 = MomentumStrategy(
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
        ema_fast=12,
        ema_slow=26,
        macd_signal=9,
        position_size=0.15,
        stop_loss_pct=0.02,
        take_profit_pct=0.03,
        macd_histogram_threshold=0.0005,
        volume_confirmation=True,
        volume_multiplier=1.05,  # Week 2 fix: reduced from 1.2
        use_trailing_stop=True,
        trailing_stop_pct=0.015,
    )
    results1 = run_strategy_backtest(
        strategy1,
        "Strategy 1: Full Momentum (Week 2 Fixes)",
        symbols,
        start_date,
        end_date,
        initial_capital
    )
    if results1:
        all_results['strategy1_momentum'] = results1

    logger.info("\n" + "=" * 80 + "\n")

    # Strategy 2: Simplified Momentum (Week 2 fixes applied)
    strategy2 = SimplifiedMomentumStrategy(
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
    results2 = run_strategy_backtest(
        strategy2,
        "Strategy 2: Simplified Momentum (Week 2 Fixes)",
        symbols,
        start_date,
        end_date,
        initial_capital
    )
    if results2:
        all_results['strategy2_simplified'] = results2

    logger.info("\n" + "=" * 80 + "\n")

    # Strategy 3: Mean Reversion (needs investigation)
    strategy3 = MeanReversion(
        bb_period=20,
        bb_std=2.0,
        position_size=0.15,
        stop_loss_pct=0.02,
        take_profit_pct=0.03,
        touch_threshold=1.001,
    )
    results3 = run_strategy_backtest(
        strategy3,
        "Strategy 3: Mean Reversion (Bollinger Bands)",
        symbols,
        start_date,
        end_date,
        initial_capital
    )
    if results3:
        all_results['strategy3_mean_reversion'] = results3

    # Summary comparison
    logger.info("")
    logger.info("=" * 80)
    logger.info("WEEK 2 VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info("")

    summary_data = []
    for name, results in all_results.items():
        summary_data.append({
            'Strategy': name,
            'Return': f"{results.get('total_return', 0):.2%}",
            'Sharpe': f"{results.get('sharpe_ratio', 0):.2f}",
            'Win Rate': f"{results.get('win_rate', 0):.1%}",
            'Trades': results.get('total_trades', 0),
            'Max DD': f"{results.get('max_drawdown', 0):.1%}",
            'Criteria': f"{results.get('criteria_met', 0)}/{results.get('criteria_total', 5)}",
            'Pass': f"{results.get('pass_rate', 0):.0%}"
        })

    df = pd.DataFrame(summary_data)
    logger.info("\n" + df.to_string(index=False))

    # Save results
    output_dir = project_root / 'data' / 'backtest_results'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'week2_validation_{timestamp}.json'

    # Prepare JSON-serializable results
    json_results = {
        'timestamp': timestamp,
        'test_period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'symbols': symbols,
        'initial_capital': initial_capital,
        'strategies': {}
    }

    for name, results in all_results.items():
        json_results['strategies'][name] = {
            k: float(v) if hasattr(v, 'item') else v
            for k, v in results.items()
            if not isinstance(v, (list, dict)) or k == 'criteria_met'
        }

    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)

    logger.info("")
    logger.info(f"Results saved to: {output_file}")

    # Week 3 recommendation
    logger.info("")
    logger.info("=" * 80)
    logger.info("WEEK 3 GO/NO-GO RECOMMENDATION")
    logger.info("=" * 80)

    best_strategy = max(all_results.items(), key=lambda x: x[1].get('pass_rate', 0))
    best_name = best_strategy[0]
    best_results = best_strategy[1]

    if best_results.get('pass_rate', 0) >= 0.60:  # 3/5 criteria
        logger.success(f"✓ GO: Best strategy ({best_name}) meets {best_results.get('criteria_met')}/5 criteria")
        logger.success(f"  Recommendation: Proceed to Week 3 with {best_name}")
        return 0
    else:
        logger.warning(f"✗ NO-GO: Best strategy ({best_name}) only meets {best_results.get('criteria_met')}/5 criteria")
        logger.warning("  Recommendation: More optimization needed before Week 3")
        return 1


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Also log to file
    log_file = project_root / 'data' / 'backtest_results' / 'week2_validation.log'
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG"
    )

    exit_code = main()
    sys.exit(exit_code)
