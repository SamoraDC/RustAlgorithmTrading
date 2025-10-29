#!/usr/bin/env python3
"""
Run backtest with optimized momentum strategy

Compares original vs optimized parameters:
- Stop-loss: 2% → 3%
- Take-profit: 3% → 5%
- RSI thresholds: 50 → 45/55
- MACD histogram: 0.0005 → 0.0003
- Minimum holding: 10 → 5 bars
- Volume filter: DISABLED
- SMA filter: DISABLED temporarily
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

from src.strategies.momentum_optimized import MomentumOptimizedStrategy
from src.backtesting.engine import BacktestEngine
from src.backtesting.portfolio_handler import PortfolioHandler
from src.data.data_handler import DataHandler


def run_optimized_backtest():
    """Run backtest with optimized strategy parameters"""

    logger.info("=" * 80)
    logger.info("OPTIMIZED MOMENTUM STRATEGY BACKTEST")
    logger.info("=" * 80)

    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    initial_capital = 100000.0
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months

    logger.info(f"Testing period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Initial capital: ${initial_capital:,.2f}")
    logger.info("")

    # Initialize components
    logger.info("Initializing optimized strategy with relaxed parameters...")
    strategy = MomentumOptimizedStrategy()

    logger.info("Strategy parameters:")
    for key, value in strategy.parameters.items():
        logger.info(f"  {key}: {value}")
    logger.info("")

    portfolio = PortfolioHandler(initial_capital=initial_capital)
    data_handler = DataHandler()

    # Load data
    logger.info("Loading market data...")
    all_data = {}
    for symbol in symbols:
        try:
            data = data_handler.fetch_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe='1Day'
            )
            if data is not None and not data.empty:
                all_data[symbol] = data
                logger.info(f"  {symbol}: {len(data)} bars loaded")
            else:
                logger.warning(f"  {symbol}: No data available")
        except Exception as e:
            logger.error(f"  {symbol}: Failed to load data - {e}")

    if not all_data:
        logger.error("No data loaded for any symbols!")
        return None

    logger.info(f"Successfully loaded data for {len(all_data)} symbols")
    logger.info("")

    # Run backtest
    logger.info("Running backtest...")
    engine = BacktestEngine(
        strategy=strategy,
        portfolio=portfolio,
        initial_capital=initial_capital
    )

    results = engine.run(all_data)

    # Display results
    logger.info("=" * 80)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 80)

    if results:
        logger.info(f"Total Return: {results.get('total_return', 0):.2%}")
        logger.info(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        logger.info(f"Max Drawdown: {results.get('max_drawdown', 0):.2%}")
        logger.info(f"Win Rate: {results.get('win_rate', 0):.2%}")
        logger.info(f"Total Trades: {results.get('total_trades', 0)}")
        logger.info(f"Winning Trades: {results.get('winning_trades', 0)}")
        logger.info(f"Losing Trades: {results.get('losing_trades', 0)}")
        logger.info(f"Average Win: {results.get('avg_win', 0):.2%}")
        logger.info(f"Average Loss: {results.get('avg_loss', 0):.2%}")
        logger.info(f"Final Portfolio Value: ${results.get('final_value', 0):,.2f}")

        # Save results
        output_dir = project_root / 'data' / 'backtest_results'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'optimized_strategy_{timestamp}.json'

        with open(output_file, 'w') as f:
            # Convert numpy types to native Python types for JSON serialization
            json_results = {}
            for key, value in results.items():
                if hasattr(value, 'item'):  # numpy type
                    json_results[key] = value.item()
                elif isinstance(value, (list, dict)):
                    json_results[key] = value
                else:
                    json_results[key] = value

            json.dump(json_results, f, indent=2, default=str)

        logger.info(f"Results saved to: {output_file}")

        # Performance comparison
        logger.info("")
        logger.info("=" * 80)
        logger.info("TARGET METRICS COMPARISON")
        logger.info("=" * 80)

        win_rate = results.get('win_rate', 0)
        total_trades = results.get('total_trades', 0)
        total_return = results.get('total_return', 0)

        logger.info(f"Win Rate: {win_rate:.1%} (Target: >35%)")
        if win_rate > 0.35:
            logger.success("✓ Win rate target MET!")
        else:
            logger.warning(f"✗ Win rate below target (need {0.35 - win_rate:.1%} more)")

        logger.info(f"Total Trades: {total_trades} (Target: 15-30)")
        if 15 <= total_trades <= 30:
            logger.success("✓ Trade count target MET!")
        elif total_trades < 15:
            logger.warning(f"✗ Too few trades (need {15 - total_trades} more)")
        else:
            logger.warning(f"✗ Too many trades ({total_trades - 30} over target)")

        logger.info(f"Total Return: {total_return:.2%} (Target: >0%)")
        if total_return > 0:
            logger.success("✓ Return target MET!")
        else:
            logger.warning(f"✗ Negative return ({total_return:.2%})")

        return results
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

    results = run_optimized_backtest()

    if results:
        sys.exit(0)
    else:
        sys.exit(1)
