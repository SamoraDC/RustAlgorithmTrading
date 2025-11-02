#!/usr/bin/env python3
"""
Individual Strategy Testing Script

Tests each strategy independently with comprehensive logging and metrics.
This helps identify issues with specific strategies before running the full router.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strategies.momentum_simplified import SimplifiedMomentumStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.mean_reversion import MeanReversion
from src.backtesting.engine import BacktestEngine


def setup_logging():
    """Configure comprehensive logging"""
    logger.remove()  # Remove default handler

    # Console logging with colors
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )

    # File logging
    log_file = Path("logs/strategy_testing.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:8} | {name}:{function} - {message}",
        level="DEBUG",
        rotation="10 MB"
    )


def load_historical_data(symbol: str) -> pd.DataFrame:
    """Load historical data for a symbol"""
    data_dir = Path("data/historical")

    # Try parquet first, then CSV
    parquet_file = data_dir / f"{symbol}.parquet"
    csv_file = data_dir / f"{symbol}.csv"

    if parquet_file.exists():
        logger.info(f"Loading {symbol} from parquet: {parquet_file}")
        df = pd.read_parquet(parquet_file)
    elif csv_file.exists():
        logger.info(f"Loading {symbol} from CSV: {csv_file}")
        df = pd.read_csv(csv_file, parse_dates=['timestamp'])
    else:
        raise FileNotFoundError(f"No data file found for {symbol}")

    # Ensure proper datetime index
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

    # Set symbol attribute
    df.attrs['symbol'] = symbol

    logger.info(f"Loaded {len(df)} bars for {symbol} from {df.index[0]} to {df.index[-1]}")
    return df


def test_strategy(
    strategy_name: str,
    strategy,
    symbol: str,
    data: pd.DataFrame,
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    Test a single strategy with comprehensive logging

    Returns:
        Dictionary with test results and metrics
    """
    logger.info("=" * 100)
    logger.info(f"TESTING STRATEGY: {strategy_name} on {symbol}")
    logger.info("=" * 100)

    try:
        # Generate signals
        logger.info(f"[{strategy_name}] Generating signals...")
        signals = strategy.generate_signals(data)

        logger.info(f"[{strategy_name}] Generated {len(signals)} total signals")

        # Count signal types
        long_signals = sum(1 for s in signals if str(s.signal_type) == 'SignalType.LONG')
        short_signals = sum(1 for s in signals if str(s.signal_type) == 'SignalType.SHORT')
        exit_signals = sum(1 for s in signals if str(s.signal_type) == 'SignalType.EXIT')

        logger.info(f"[{strategy_name}] Signal breakdown:")
        logger.info(f"  - LONG:  {long_signals}")
        logger.info(f"  - SHORT: {short_signals}")
        logger.info(f"  - EXIT:  {exit_signals}")

        if len(signals) == 0:
            logger.warning(f"[{strategy_name}] ⚠️  NO SIGNALS GENERATED - Strategy may be too restrictive")
            return {
                'strategy': strategy_name,
                'symbol': symbol,
                'status': 'NO_SIGNALS',
                'total_signals': 0,
                'long_signals': 0,
                'short_signals': 0,
                'exit_signals': 0,
                'error': None
            }

        # Run backtest using event-driven engine
        logger.info(f"[{strategy_name}] Running backtest...")

        from src.backtesting.data_handler import HistoricalDataHandler
        from src.backtesting.execution_handler import SimulatedExecutionHandler
        from src.backtesting.portfolio_handler import PortfolioHandler, PercentageOfEquitySizer

        # Get date range from data
        start_date = data.index.min()
        end_date = data.index.max()

        # Save data to temporary directory for data handler
        temp_dir = Path("data/temp_backtest")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"{symbol}.parquet"
        data.to_parquet(temp_file)

        # Initialize backtest components
        data_handler = HistoricalDataHandler(
            symbols=[symbol],
            data_dir=temp_dir,
            start_date=start_date,
            end_date=end_date
        )

        execution_handler = SimulatedExecutionHandler()

        position_sizer = PercentageOfEquitySizer(percent=0.15)
        portfolio_handler = PortfolioHandler(
            symbols=[symbol],
            initial_capital=initial_capital,
            position_sizer=position_sizer
        )

        # Run backtest
        backtest_engine = BacktestEngine(
            data_handler=data_handler,
            execution_handler=execution_handler,
            portfolio_handler=portfolio_handler,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date
        )

        results = backtest_engine.run()

        # Cleanup temp file
        temp_file.unlink(missing_ok=True)

        # Extract metrics
        metrics = results.get('performance_metrics', {})

        logger.info(f"[{strategy_name}] Backtest Results:")
        logger.info(f"  Total Return:    {metrics.get('total_return', 0):.2%}")
        logger.info(f"  Sharpe Ratio:    {metrics.get('sharpe_ratio', 0):.2f}")
        logger.info(f"  Max Drawdown:    {metrics.get('max_drawdown', 0):.2%}")
        logger.info(f"  Win Rate:        {metrics.get('win_rate', 0):.2%}")
        logger.info(f"  Total Trades:    {metrics.get('total_trades', 0)}")
        logger.info(f"  Winning Trades:  {metrics.get('winning_trades', 0)}")
        logger.info(f"  Losing Trades:   {metrics.get('losing_trades', 0)}")
        logger.info(f"  Profit Factor:   {metrics.get('profit_factor', 0):.2f}")

        # Validation checks
        validations = []

        if metrics.get('sharpe_ratio', 0) < 1.0:
            validations.append(f"⚠️  Low Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f} < 1.0")
        else:
            validations.append(f"✅ Good Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f} >= 1.0")

        if metrics.get('win_rate', 0) < 0.50:
            validations.append(f"⚠️  Low Win Rate: {metrics.get('win_rate', 0):.2%} < 50%")
        else:
            validations.append(f"✅ Good Win Rate: {metrics.get('win_rate', 0):.2%} >= 50%")

        if metrics.get('max_drawdown', 0) > 0.20:
            validations.append(f"⚠️  High Drawdown: {metrics.get('max_drawdown', 0):.2%} > 20%")
        else:
            validations.append(f"✅ Acceptable Drawdown: {metrics.get('max_drawdown', 0):.2%} <= 20%")

        if metrics.get('total_trades', 0) < 10:
            validations.append(f"⚠️  Few Trades: {metrics.get('total_trades', 0)} < 10")
        else:
            validations.append(f"✅ Good Trade Count: {metrics.get('total_trades', 0)} >= 10")

        logger.info(f"\n[{strategy_name}] Validation Results:")
        for validation in validations:
            logger.info(f"  {validation}")

        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'status': 'SUCCESS',
            'total_signals': len(signals),
            'long_signals': long_signals,
            'short_signals': short_signals,
            'exit_signals': exit_signals,
            'metrics': metrics,
            'validations': validations,
            'error': None
        }

    except Exception as e:
        logger.error(f"[{strategy_name}] ❌ TEST FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            'strategy': strategy_name,
            'symbol': symbol,
            'status': 'ERROR',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def main():
    """Main testing workflow"""
    setup_logging()

    logger.info("=" * 100)
    logger.info("INDIVIDUAL STRATEGY TESTING")
    logger.info("=" * 100)

    # Test configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    strategies = {
        'SimplifiedMomentum': SimplifiedMomentumStrategy(),
        'TrendFollowing': TrendFollowingStrategy(),
        'MeanReversion': MeanReversion(),
    }

    # Results storage
    all_results = []

    # Test each strategy on each symbol
    for symbol in symbols:
        logger.info(f"\n{'='*100}")
        logger.info(f"LOADING DATA FOR {symbol}")
        logger.info(f"{'='*100}")

        try:
            data = load_historical_data(symbol)

            for strategy_name, strategy in strategies.items():
                result = test_strategy(strategy_name, strategy, symbol, data)
                all_results.append(result)

                logger.info("")  # Blank line for readability

        except Exception as e:
            logger.error(f"Failed to load data for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Generate summary report
    logger.info("\n" + "=" * 100)
    logger.info("SUMMARY REPORT")
    logger.info("=" * 100)

    # Count successes and failures
    successful = sum(1 for r in all_results if r['status'] == 'SUCCESS')
    no_signals = sum(1 for r in all_results if r['status'] == 'NO_SIGNALS')
    errors = sum(1 for r in all_results if r['status'] == 'ERROR')

    logger.info(f"\nTest Results:")
    logger.info(f"  ✅ Successful: {successful}/{len(all_results)}")
    logger.info(f"  ⚠️  No Signals: {no_signals}/{len(all_results)}")
    logger.info(f"  ❌ Errors:     {errors}/{len(all_results)}")

    # Strategy-level summary
    logger.info(f"\nPer-Strategy Performance:")
    for strategy_name in strategies.keys():
        strategy_results = [r for r in all_results if r['strategy'] == strategy_name and r['status'] == 'SUCCESS']

        if strategy_results:
            avg_sharpe = sum(r['metrics'].get('sharpe_ratio', 0) for r in strategy_results) / len(strategy_results)
            avg_win_rate = sum(r['metrics'].get('win_rate', 0) for r in strategy_results) / len(strategy_results)
            avg_trades = sum(r['metrics'].get('total_trades', 0) for r in strategy_results) / len(strategy_results)

            logger.info(f"\n  {strategy_name}:")
            logger.info(f"    Avg Sharpe Ratio: {avg_sharpe:.2f}")
            logger.info(f"    Avg Win Rate:     {avg_win_rate:.2%}")
            logger.info(f"    Avg Trades:       {avg_trades:.1f}")

    # Save results
    output_dir = Path("data/strategy_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"strategy_test_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'summary': {
                'successful': successful,
                'no_signals': no_signals,
                'errors': errors,
                'total': len(all_results)
            },
            'results': all_results
        }, f, indent=2, default=str)

    logger.info(f"\n✅ Results saved to: {output_file}")

    # Exit code
    if errors > 0:
        logger.error(f"\n❌ TESTING FAILED: {errors} strategies had errors")
        sys.exit(1)
    elif no_signals > len(all_results) // 2:
        logger.warning(f"\n⚠️  WARNING: {no_signals} strategies generated no signals")
        sys.exit(1)
    else:
        logger.success(f"\n✅ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
