"""
Example: Basic backtesting with Moving Average Crossover strategy
"""

from datetime import datetime, timedelta
from alpaca.data.timeframe import TimeFrame

from src.api.alpaca_client import AlpacaClient
from src.data.fetcher import DataFetcher
from src.data.preprocessor import DataPreprocessor
from src.strategies.moving_average import MovingAverageCrossover
from src.backtesting.engine import BacktestEngine
from src.utils.logger import setup_logger
from config.config import get_config


def main():
    """Run basic backtest example"""

    # Setup logging
    setup_logger(log_level="INFO")

    # Load configuration
    config = get_config()

    print("=" * 60)
    print("BASIC BACKTEST EXAMPLE - Moving Average Crossover")
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

    symbol = "AAPL"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    data = fetcher.fetch_last_n_days(symbol=symbol, days=365, timeframe=TimeFrame.Day)

    print(f"   Retrieved {len(data)} days of data for {symbol}")

    # Preprocess data
    print("\n2. Preprocessing data...")
    preprocessor = DataPreprocessor()
    data = preprocessor.add_technical_indicators(data)
    data = preprocessor.calculate_returns(data)

    print(f"   Added technical indicators")

    # Create strategy
    print("\n3. Initializing strategy...")
    strategy = MovingAverageCrossover(
        fast_period=20,
        slow_period=50,
        position_size=0.95
    )

    print(f"   Strategy: {strategy.name}")
    print(f"   Parameters: {strategy.parameters}")

    # Run backtest
    print("\n4. Running backtest...")
    engine = BacktestEngine(
        initial_capital=config.get('backtest.initial_capital'),
        commission_rate=config.get('backtest.commission_rate'),
        slippage=config.get('backtest.slippage')
    )

    results = engine.run(strategy, data, symbol=symbol)

    # Display results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    print(f"\nSymbol: {results['symbol']}")
    print(f"Initial Capital: ${results['initial_capital']:,.2f}")
    print(f"Final Equity: ${results['final_equity']:,.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Annual Return: {results['annual_return']:.2f}%")

    print(f"\nTrade Statistics:")
    print(f"  Total Trades: {results['num_trades']}")
    print(f"  Winning Trades: {results['num_winning']}")
    print(f"  Losing Trades: {results['num_losing']}")
    print(f"  Win Rate: {results['win_rate']:.2f}%")

    print(f"\nProfit Metrics:")
    print(f"  Net Profit: ${results['net_profit']:,.2f}")
    print(f"  Profit Factor: {results['profit_factor']:.2f}")
    print(f"  Average Win: ${results['avg_win']:,.2f}")
    print(f"  Average Loss: ${results['avg_loss']:,.2f}")

    print(f"\nRisk Metrics:")
    print(f"  Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"  Sortino Ratio: {results['sortino_ratio']:.2f}")
    print(f"  Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"  Volatility: {results['volatility']:.2f}%")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
