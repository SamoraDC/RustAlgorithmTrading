#!/usr/bin/env python3
"""
Example backtest script demonstrating the Python backtesting framework.
"""

from datetime import datetime
from pathlib import Path
from loguru import logger

from src.backtesting import (
    BacktestEngine,
    HistoricalDataHandler,
    SimulatedExecutionHandler,
    PortfolioHandler,
)
from src.backtesting.portfolio_handler import PercentageOfEquitySizer
from src.strategies.base import BaseStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy
from src.utils.visualization import (
    plot_equity_curve,
    plot_drawdown,
    plot_returns_distribution,
)
from src.utils.metrics import calculate_metrics, format_metrics_table


def main():
    """Run example backtest."""
    logger.info("Starting backtest example")

    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    initial_capital = 100_000.0
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    data_dir = Path('data/historical')

    # Initialize components
    logger.info("Initializing backtest components")

    # Data handler
    data_handler = HistoricalDataHandler(
        symbols=symbols,
        data_dir=data_dir,
        start_date=start_date,
        end_date=end_date,
    )

    # Execution handler with realistic costs
    execution_handler = SimulatedExecutionHandler(
        commission_rate=0.001,  # 10 bps
        slippage_bps=5.0,       # 5 bps average slippage
        market_impact_bps=2.0,  # 2 bps per $1M notional
    )

    # Portfolio handler with percentage-based sizing
    portfolio_handler = PortfolioHandler(
        initial_capital=initial_capital,
        position_sizer=PercentageOfEquitySizer(percentage=0.33),  # 33% per position
    )

    # Strategy - Mean Reversion
    strategy = MeanReversionStrategy(
        symbols=symbols,
        lookback_period=20,
        num_std=2.0,
        z_score_threshold=2.0,
    )

    # Alternative: Momentum Strategy
    # strategy = MomentumStrategy(
    #     symbols=symbols,
    #     short_window=10,
    #     long_window=30,
    #     rsi_period=14,
    # )

    # Create backtest engine
    engine = BacktestEngine(
        data_handler=data_handler,
        execution_handler=execution_handler,
        portfolio_handler=portfolio_handler,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
    )

    # Run backtest
    logger.info("Running backtest")
    results = engine.run()

    # Display results
    logger.info("Backtest completed, generating results")

    # Calculate summary metrics
    summary = calculate_metrics(results)

    # Print metrics table
    print(format_metrics_table(summary))

    # Plot results
    logger.info("Generating visualizations")

    plot_equity_curve(
        results['equity_curve'],
        title=f"{strategy.name} - Equity Curve",
        save_path=Path('outputs/equity_curve.png'),
    )

    plot_drawdown(
        results['equity_curve'],
        title=f"{strategy.name} - Drawdown",
        save_path=Path('outputs/drawdown.png'),
    )

    plot_returns_distribution(
        results['equity_curve'],
        title=f"{strategy.name} - Returns Distribution",
        save_path=Path('outputs/returns_dist.png'),
    )

    # Save results to CSV
    results['equity_curve'].to_csv('outputs/equity_curve.csv', index=False)
    results['holdings'].to_csv('outputs/holdings.csv', index=False)

    logger.success("Backtest complete! Results saved to outputs/ directory")


if __name__ == '__main__':
    # Create output directory
    Path('outputs').mkdir(exist_ok=True)

    # Run backtest
    main()
