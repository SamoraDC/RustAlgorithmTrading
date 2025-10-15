"""
Example: Monte Carlo simulation for risk analysis
"""

from datetime import datetime, timedelta
from alpaca.data.timeframe import TimeFrame

from src.api.alpaca_client import AlpacaClient
from src.data.fetcher import DataFetcher
from src.data.preprocessor import DataPreprocessor
from src.strategies.mean_reversion import MeanReversion
from src.simulations.monte_carlo import MonteCarloSimulator
from src.utils.logger import setup_logger
from config.config import get_config


def main():
    """Run Monte Carlo simulation example"""

    # Setup logging
    setup_logger(log_level="INFO")

    # Load configuration
    config = get_config()

    print("=" * 60)
    print("MONTE CARLO SIMULATION - Mean Reversion Strategy")
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

    symbol = "SPY"
    data = fetcher.fetch_last_n_days(symbol=symbol, days=500, timeframe=TimeFrame.Day)

    print(f"   Retrieved {len(data)} days of data for {symbol}")

    # Preprocess data
    print("\n2. Preprocessing data...")
    preprocessor = DataPreprocessor()
    data = preprocessor.add_technical_indicators(data)
    data.attrs['symbol'] = symbol

    # Create strategy
    print("\n3. Initializing strategy...")
    strategy = MeanReversion(
        bb_period=20,
        bb_std=2.0,
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70
    )

    print(f"   Strategy: {strategy.name}")
    print(f"   Parameters: {strategy.parameters}")

    # Initialize Monte Carlo simulator
    print("\n4. Setting up Monte Carlo simulation...")
    simulator = MonteCarloSimulator(
        num_simulations=config.get('monte_carlo.num_simulations'),
        confidence_level=config.get('monte_carlo.confidence_level'),
        random_seed=config.get('monte_carlo.random_seed')
    )

    print(f"   Number of simulations: {simulator.num_simulations}")
    print(f"   Confidence level: {simulator.confidence_level}")

    # Run simulation
    print("\n5. Running Monte Carlo simulation...")
    print("   (This may take a few minutes...)")

    results = simulator.simulate_strategy(
        strategy=strategy,
        base_data=data,
        initial_capital=config.get('backtest.initial_capital'),
        resample_method='block_bootstrap'
    )

    # Display results
    print("\n" + "=" * 60)
    print("MONTE CARLO SIMULATION RESULTS")
    print("=" * 60)

    print(f"\nSimulation Parameters:")
    print(f"  Number of Simulations: {results['num_simulations']}")
    print(f"  Initial Capital: ${results['initial_capital']:,.2f}")

    print(f"\nReturn Statistics:")
    print(f"  Expected Return: {results['expected_return']:.2%}")
    print(f"  Median Return: {results['median_return']:.2%}")
    print(f"  Standard Deviation: {results['std_return']:.2%}")
    print(f"  Min Return: {results['min_return']:.2%}")
    print(f"  Max Return: {results['max_return']:.2%}")

    print(f"\nRisk Metrics:")
    print(f"  Value at Risk (95%): {results['var_95']:.2%}")
    print(f"  Conditional VaR (95%): {results['cvar_95']:.2%}")
    print(f"  Probability of Profit: {results['prob_profit']:.2%}")

    print(f"\nFinal Equity Statistics:")
    print(f"  Expected Final Equity: ${results['expected_final_equity']:,.2f}")
    print(f"  Median Final Equity: ${results['median_final_equity']:,.2f}")
    print(f"  Min Final Equity: ${results['min_final_equity']:,.2f}")
    print(f"  Max Final Equity: ${results['max_final_equity']:,.2f}")

    print(f"\nPerformance Metrics:")
    print(f"  Average Sharpe Ratio: {results['avg_sharpe_ratio']:.2f}")
    print(f"  Average Max Drawdown: {results['avg_max_drawdown']:.2f}%")

    print(f"\nReturn Percentiles:")
    for percentile, value in results['percentiles'].items():
        print(f"  {percentile}: {value:.2%}")

    # Plot results
    print("\n6. Generating visualization...")
    simulator.plot_results(
        save_path="examples/monte_carlo_results.png",
        show_plot=False
    )
    print("   Plot saved to: examples/monte_carlo_results.png")

    # Get specific scenarios
    print("\n7. Analyzing specific scenarios...")
    scenarios = simulator.get_percentile_scenarios([5, 50, 95])

    print("\n   Pessimistic Scenario (5th percentile):")
    print(f"     Return: {scenarios[5]['total_return']:.2%}")
    print(f"     Final Equity: ${scenarios[5]['final_equity']:,.2f}")

    print("\n   Expected Scenario (50th percentile):")
    print(f"     Return: {scenarios[50]['total_return']:.2%}")
    print(f"     Final Equity: ${scenarios[50]['final_equity']:,.2f}")

    print("\n   Optimistic Scenario (95th percentile):")
    print(f"     Return: {scenarios[95]['total_return']:.2%}")
    print(f"     Final Equity: ${scenarios[95]['final_equity']:,.2f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
