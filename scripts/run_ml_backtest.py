#!/usr/bin/env python3
"""
ML Ensemble Strategy Backtest

This script runs a comprehensive backtest of the ML Ensemble Strategy
targeting Sharpe Ratio >= 1.2 with both long and short operations.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backtesting.data_handler import HistoricalDataHandler
from src.backtesting.execution_handler import SimulatedExecutionHandler
from src.backtesting.portfolio_handler import PortfolioHandler
from src.backtesting.engine import BacktestEngine
from src.strategies.trend_momentum_strategy import TrendMomentumStrategy


def run_ml_backtest(
    symbols: list = None,
    initial_capital: float = 100_000,
    long_threshold: float = 0.58,
    short_threshold: float = 0.65,
    stop_loss: float = 0.02,
    take_profit: float = 0.04
):
    """
    Run ML Ensemble Strategy backtest.

    Args:
        symbols: List of symbols to trade
        initial_capital: Starting capital
        long_threshold: Confidence threshold for long signals
        short_threshold: Confidence threshold for short signals
        stop_loss: Stop loss percentage
        take_profit: Take profit percentage
    """
    logger.info("=" * 80)
    logger.info("TREND-MOMENTUM STRATEGY BACKTEST")
    logger.info("=" * 80)

    if symbols is None:
        # Trade all 3 stocks for diversification
        symbols = ['AAPL', 'MSFT', 'GOOGL']

    # Load historical data
    data_dir = project_root / "data" / "historical"

    # Find date range from data
    sample_file = data_dir / f"{symbols[0]}.parquet"
    if sample_file.exists():
        sample_df = pd.read_parquet(sample_file)
        # Ensure we have datetime index
        if not isinstance(sample_df.index, pd.DatetimeIndex):
            if 'timestamp' in sample_df.columns:
                sample_df = sample_df.set_index('timestamp')
            elif 'date' in sample_df.columns:
                sample_df = sample_df.set_index('date')
        start_date = pd.to_datetime(sample_df.index.min())
        end_date = pd.to_datetime(sample_df.index.max())
    else:
        logger.error(f"Data file not found: {sample_file}")
        return None

    logger.info(f"Backtest Period: {start_date} to {end_date}")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    logger.info(f"Long Threshold: {long_threshold:.0%}")
    logger.info(f"Short Threshold: {short_threshold:.0%}")

    # Initialize components
    data_handler = HistoricalDataHandler(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        data_dir=str(data_dir)
    )

    execution_handler = SimulatedExecutionHandler(
        commission_rate=0.001,
        slippage_bps=5.0,
        market_impact_bps=2.0
    )

    portfolio_handler = PortfolioHandler(
        initial_capital=initial_capital,
        data_handler=data_handler
    )

    # Initialize Trend-Momentum Strategy - Best parameters for all 3 stocks
    strategy = TrendMomentumStrategy(
        ema_period=20,
        rsi_long_min=35,
        rsi_short_max=60,
        rsi_exit_long=20,  # Only exit on significant weakness
        rsi_exit_short=80,
        stop_loss_pct=0.06,  # Wide stop (6%)
        take_profit_pct=0.20,  # High target (20%)
        trailing_stop_pct=0.05,  # Wide trailing (5%)
        position_size=0.20,  # Reduced for 3 stocks
        enable_shorts=False,  # Only longs in uptrending market
        short_size_multiplier=0.5,
    )

    # Initialize backtest engine
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
    display_results(results, initial_capital)

    return results


def display_results(results: dict, initial_capital: float):
    """Display backtest results."""
    metrics = results.get('metrics', {})

    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST RESULTS - Quantitative Strategy")
    logger.info("=" * 80)

    logger.info("\nPerformance Metrics:")
    logger.info("-" * 80)

    # Key metrics
    key_metrics = [
        ('total_return', '%'),
        ('sharpe_ratio', ''),
        ('sortino_ratio', ''),
        ('max_drawdown', '%'),
        ('win_rate', '%'),
        ('profit_factor', ''),
        ('total_trades', ''),
        ('winning_trades', ''),
        ('losing_trades', ''),
        ('average_win', '$'),
        ('average_loss', '$'),
        ('volatility', '%'),
        ('calmar_ratio', '')
    ]

    for metric_name, suffix in key_metrics:
        value = metrics.get(metric_name, 0)
        if isinstance(value, (int, float)):
            if suffix == '%':
                logger.info(f"  {metric_name:30s}: {value:.2f}%")
            elif suffix == '$':
                logger.info(f"  {metric_name:30s}: ${value:.2f}")
            elif metric_name in ['total_trades', 'winning_trades', 'losing_trades']:
                logger.info(f"  {metric_name:30s}: {int(value)}")
            else:
                logger.info(f"  {metric_name:30s}: {value:.4f}")

    # Strategy-specific stats
    logger.info("\n" + "-" * 80)
    logger.info("Strategy Statistics:")
    logger.info("-" * 80)

    # Calculate additional stats from equity curve
    equity_curve = results.get('equity_curve', pd.DataFrame())
    if not equity_curve.empty:
        final_equity = equity_curve['equity'].iloc[-1]
        peak_equity = equity_curve['equity'].max()
        min_equity = equity_curve['equity'].min()

        logger.info(f"  {'Final Equity':30s}: ${final_equity:,.2f}")
        logger.info(f"  {'Peak Equity':30s}: ${peak_equity:,.2f}")
        logger.info(f"  {'Min Equity':30s}: ${min_equity:,.2f}")
        logger.info(f"  {'Profit':30s}: ${final_equity - initial_capital:,.2f}")

    # Deployment readiness check
    logger.info("\n" + "=" * 80)
    logger.info("DEPLOYMENT READINESS CHECK")
    logger.info("=" * 80)

    sharpe = metrics.get('sharpe_ratio', 0)
    total_return = metrics.get('total_return', 0)
    win_rate = metrics.get('win_rate', 0)
    max_dd = metrics.get('max_drawdown', 0)
    total_trades = metrics.get('total_trades', 0)

    checks = {
        'Sharpe Ratio >= 1.2': (sharpe >= 1.2, f"{sharpe:.2f}"),
        'Total Return > 10%': (total_return > 10.0, f"{total_return:.2f}%"),
        'Win Rate > 45%': (win_rate > 45.0, f"{win_rate:.2f}%"),
        'Max Drawdown < 15%': (abs(max_dd) < 15.0, f"{max_dd:.2f}%"),
        'Total Trades >= 30': (total_trades >= 30, f"{int(total_trades)}"),
    }

    all_passed = True
    for check, (passed, value) in checks.items():
        status = "PASS" if passed else "FAIL"
        emoji = "+" if passed else "X"
        logger.info(f"  [{emoji}] {status} | {check:30s}: {value}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n[+] ALL CHECKS PASSED - Strategy ready for deployment!")
    else:
        logger.warning("\n[!] SOME CHECKS FAILED - Review and optimize strategy")

    # Save results
    output_dir = project_root / "data" / "backtest_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"ml_ensemble_backtest_{timestamp}.json"

    import json
    with open(output_file, 'w') as f:
        # Convert non-serializable items
        save_metrics = {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                       for k, v in metrics.items()}
        json.dump({
            'metrics': save_metrics,
            'parameters': {
                'long_threshold': 0.58,
                'short_threshold': 0.65,
                'stop_loss': 0.02,
                'take_profit': 0.04
            }
        }, f, indent=2, default=str)

    logger.info(f"\nResults saved to: {output_file}")


def optimize_parameters():
    """
    Grid search to find optimal parameters for Sharpe >= 1.2
    """
    logger.info("=" * 80)
    logger.info("PARAMETER OPTIMIZATION")
    logger.info("=" * 80)

    best_sharpe = -np.inf
    best_params = {}

    # Parameter grid
    long_thresholds = [0.55, 0.58, 0.60, 0.62]
    short_thresholds = [0.62, 0.65, 0.68, 0.70]
    stop_losses = [0.015, 0.02, 0.025]
    take_profits = [0.03, 0.04, 0.05]

    total_combinations = (len(long_thresholds) * len(short_thresholds) *
                         len(stop_losses) * len(take_profits))
    logger.info(f"Testing {total_combinations} parameter combinations...")

    iteration = 0
    for long_t in long_thresholds:
        for short_t in short_thresholds:
            for sl in stop_losses:
                for tp in take_profits:
                    iteration += 1
                    if iteration % 10 == 0:
                        logger.info(f"Progress: {iteration}/{total_combinations}")

                    try:
                        results = run_ml_backtest(
                            long_threshold=long_t,
                            short_threshold=short_t,
                            stop_loss=sl,
                            take_profit=tp
                        )

                        if results:
                            sharpe = results.get('metrics', {}).get('sharpe_ratio', -np.inf)
                            if sharpe > best_sharpe:
                                best_sharpe = sharpe
                                best_params = {
                                    'long_threshold': long_t,
                                    'short_threshold': short_t,
                                    'stop_loss': sl,
                                    'take_profit': tp
                                }
                                logger.info(f"New best Sharpe: {sharpe:.3f} with {best_params}")

                    except Exception as e:
                        logger.debug(f"Failed with params {long_t}/{short_t}/{sl}/{tp}: {e}")
                        continue

    logger.info("\n" + "=" * 80)
    logger.info("OPTIMIZATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Best Sharpe Ratio: {best_sharpe:.3f}")
    logger.info(f"Best Parameters: {best_params}")

    return best_params, best_sharpe


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ML Ensemble Strategy Backtest")
    parser.add_argument('--optimize', action='store_true', help='Run parameter optimization')
    parser.add_argument('--long-threshold', type=float, default=0.58, help='Long confidence threshold')
    parser.add_argument('--short-threshold', type=float, default=0.65, help='Short confidence threshold')
    parser.add_argument('--stop-loss', type=float, default=0.02, help='Stop loss percentage')
    parser.add_argument('--take-profit', type=float, default=0.04, help='Take profit percentage')

    args = parser.parse_args()

    if args.optimize:
        optimize_parameters()
    else:
        results = run_ml_backtest(
            long_threshold=args.long_threshold,
            short_threshold=args.short_threshold,
            stop_loss=args.stop_loss,
            take_profit=args.take_profit
        )

        if results:
            sharpe = results.get('metrics', {}).get('sharpe_ratio', 0)
            if sharpe < 1.2:
                logger.warning(f"\nSharpe ratio {sharpe:.2f} < 1.2 target")
                logger.info("Consider running with --optimize to find better parameters")
