"""
Example: Compare multiple trading strategies
"""

from datetime import datetime, timedelta
from alpaca.data.timeframe import TimeFrame
import pandas as pd

from src.api.alpaca_client import AlpacaClient
from src.data.fetcher import DataFetcher
from src.data.preprocessor import DataPreprocessor
from src.strategies.moving_average import MovingAverageCrossover
from src.strategies.mean_reversion import MeanReversion
from src.strategies.momentum import MomentumStrategy
from src.backtesting.engine import BacktestEngine
from src.utils.logger import setup_logger
from config.config import get_config


def main():
    """Compare multiple strategies"""

    # Setup logging
    setup_logger(log_level="INFO")

    # Load configuration
    config = get_config()

    print("=" * 60)
    print("STRATEGY COMPARISON")
    print("=" * 60)

    # Initialize Alpaca client
    client = AlpacaClient(
        api_key=config.get('alpaca.api_key'),
        secret_key=config.get('alpaca.secret_key'),
        base_url=config.get('alpaca.base_url')
    )

    # Fetch historical data
    print("\n1. Fetching historical data...")
    fetcher = DataFetcher(client)

    symbol = "TSLA"
    data = fetcher.fetch_last_n_days(symbol=symbol, days=365, timeframe=TimeFrame.Day)

    print(f"   Retrieved {len(data)} days of data for {symbol}")

    # Preprocess data
    print("\n2. Preprocessing data...")
    preprocessor = DataPreprocessor()
    data = preprocessor.add_technical_indicators(data)
    data.attrs['symbol'] = symbol

    # Define strategies to compare
    print("\n3. Initializing strategies...")
    strategies = [
        MovingAverageCrossover(fast_period=20, slow_period=50),
        MeanReversion(bb_period=20, rsi_period=14),
        MomentumStrategy(rsi_period=14, ema_fast=12, ema_slow=26),
    ]

    for strategy in strategies:
        print(f"   - {strategy.name}")

    # Run backtests
    print("\n4. Running backtests...")
    results_list = []

    for strategy in strategies:
        print(f"\n   Testing {strategy.name}...")

        engine = BacktestEngine(
            initial_capital=config.get('backtest.initial_capital'),
            commission_rate=config.get('backtest.commission_rate'),
            slippage=config.get('backtest.slippage')
        )

        results = engine.run(strategy, data, symbol=symbol)
        results_list.append(results)

        print(f"     Total Return: {results['total_return_pct']:.2f}%")
        print(f"     Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"     Max Drawdown: {results['max_drawdown_pct']:.2f}%")

    # Create comparison table
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    comparison_data = []
    for i, results in enumerate(results_list):
        comparison_data.append({
            'Strategy': strategies[i].name,
            'Total Return (%)': f"{results['total_return_pct']:.2f}",
            'Annual Return (%)': f"{results['annual_return']:.2f}",
            'Sharpe Ratio': f"{results['sharpe_ratio']:.2f}",
            'Sortino Ratio': f"{results['sortino_ratio']:.2f}",
            'Max Drawdown (%)': f"{results['max_drawdown_pct']:.2f}",
            'Win Rate (%)': f"{results['win_rate']:.2f}",
            'Profit Factor': f"{results['profit_factor']:.2f}",
            'Total Trades': results['num_trades'],
        })

    comparison_df = pd.DataFrame(comparison_data)
    print("\n" + comparison_df.to_string(index=False))

    # Determine best strategy by Sharpe ratio
    print("\n" + "=" * 60)
    print("RANKINGS")
    print("=" * 60)

    # Sort by Sharpe ratio
    sharpe_sorted = sorted(
        zip(strategies, results_list),
        key=lambda x: x[1]['sharpe_ratio'],
        reverse=True
    )

    print("\nBy Sharpe Ratio:")
    for i, (strategy, results) in enumerate(sharpe_sorted, 1):
        print(f"  {i}. {strategy.name}: {results['sharpe_ratio']:.2f}")

    # Sort by total return
    return_sorted = sorted(
        zip(strategies, results_list),
        key=lambda x: x[1]['total_return'],
        reverse=True
    )

    print("\nBy Total Return:")
    for i, (strategy, results) in enumerate(return_sorted, 1):
        print(f"  {i}. {strategy.name}: {results['total_return_pct']:.2f}%")

    # Sort by max drawdown (lower is better)
    drawdown_sorted = sorted(
        zip(strategies, results_list),
        key=lambda x: abs(x[1]['max_drawdown_pct'])
    )

    print("\nBy Max Drawdown (Lower is Better):")
    for i, (strategy, results) in enumerate(drawdown_sorted, 1):
        print(f"  {i}. {strategy.name}: {results['max_drawdown_pct']:.2f}%")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
