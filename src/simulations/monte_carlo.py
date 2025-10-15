"""
Monte Carlo Simulation for risk analysis and strategy validation
"""

from typing import Dict, Any, List, Optional, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import matplotlib.pyplot as plt
import seaborn as sns

from src.strategies.base import Strategy
from src.backtesting.engine import BacktestEngine


class MonteCarloSimulator:
    """
    Monte Carlo simulation framework for risk analysis and strategy validation

    Uses random sampling to simulate multiple possible outcomes and assess
    strategy performance under different market conditions.
    """

    def __init__(
        self,
        num_simulations: int = 1000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None
    ):
        """
        Initialize Monte Carlo simulator

        Args:
            num_simulations: Number of simulation runs
            confidence_level: Confidence level for VaR/CVaR (default: 0.95)
            random_seed: Random seed for reproducibility
        """
        self.num_simulations = num_simulations
        self.confidence_level = confidence_level

        if random_seed is not None:
            np.random.seed(random_seed)

        self.simulation_results: List[Dict[str, Any]] = []

        logger.info(
            f"MonteCarloSimulator initialized: {num_simulations} simulations, "
            f"confidence={confidence_level}"
        )

    def simulate_price_paths(
        self,
        initial_price: float,
        num_days: int,
        mu: float,
        sigma: float,
        num_paths: Optional[int] = None
    ) -> np.ndarray:
        """
        Simulate price paths using Geometric Brownian Motion

        Args:
            initial_price: Starting price
            num_days: Number of days to simulate
            mu: Expected return (drift)
            sigma: Volatility (standard deviation)
            num_paths: Number of paths (defaults to num_simulations)

        Returns:
            Array of simulated price paths [num_paths, num_days]
        """
        if num_paths is None:
            num_paths = self.num_simulations

        dt = 1/252  # Daily time step

        # Generate random returns
        random_returns = np.random.normal(
            (mu - 0.5 * sigma**2) * dt,
            sigma * np.sqrt(dt),
            size=(num_paths, num_days)
        )

        # Calculate price paths
        price_paths = np.zeros((num_paths, num_days + 1))
        price_paths[:, 0] = initial_price

        for t in range(1, num_days + 1):
            price_paths[:, t] = price_paths[:, t-1] * np.exp(random_returns[:, t-1])

        logger.info(f"Generated {num_paths} price paths for {num_days} days")
        return price_paths

    def simulate_strategy(
        self,
        strategy: Strategy,
        base_data: pd.DataFrame,
        initial_capital: float = 100000.0,
        resample_method: str = 'bootstrap',
        block_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation on a trading strategy

        Args:
            strategy: Trading strategy to simulate
            base_data: Historical data for resampling
            initial_capital: Starting capital
            resample_method: Resampling method ('bootstrap', 'block_bootstrap', 'parametric')
            block_size: Block size for block bootstrap

        Returns:
            Dictionary with simulation results and statistics
        """
        logger.info(f"Starting Monte Carlo simulation for {strategy.name}")

        results = []

        for i in range(self.num_simulations):
            # Generate synthetic data
            if resample_method == 'bootstrap':
                synthetic_data = self._bootstrap_resample(base_data)
            elif resample_method == 'block_bootstrap':
                synthetic_data = self._block_bootstrap_resample(base_data, block_size)
            elif resample_method == 'parametric':
                synthetic_data = self._parametric_resample(base_data)
            else:
                raise ValueError(f"Unknown resample method: {resample_method}")

            # Run backtest on synthetic data
            engine = BacktestEngine(initial_capital=initial_capital)
            backtest_results = engine.run(strategy, synthetic_data)

            results.append({
                'simulation_id': i,
                'final_equity': backtest_results['final_equity'],
                'total_return': backtest_results['total_return'],
                'sharpe_ratio': backtest_results['sharpe_ratio'],
                'max_drawdown_pct': backtest_results['max_drawdown_pct'],
                'num_trades': backtest_results['total_trades'],
                'win_rate': backtest_results['win_rate'],
            })

            if (i + 1) % 100 == 0:
                logger.info(f"Completed {i + 1}/{self.num_simulations} simulations")

        self.simulation_results = results

        # Calculate statistics
        stats = self._calculate_statistics(results, initial_capital)

        logger.info(
            f"Simulation complete: Expected return={stats['expected_return']:.2%}, "
            f"VaR={stats['var_95']:.2%}, CVaR={stats['cvar_95']:.2%}"
        )

        return stats

    def _bootstrap_resample(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Resample data using bootstrap method (random sampling with replacement)

        Args:
            data: Original data

        Returns:
            Resampled data
        """
        indices = np.random.choice(len(data), size=len(data), replace=True)
        resampled = data.iloc[indices].copy()
        resampled.index = data.index  # Preserve original index
        return resampled

    def _block_bootstrap_resample(
        self,
        data: pd.DataFrame,
        block_size: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Resample data using block bootstrap to preserve time dependencies

        Args:
            data: Original data
            block_size: Size of blocks (default: sqrt(n))

        Returns:
            Resampled data
        """
        if block_size is None:
            block_size = int(np.sqrt(len(data)))

        n = len(data)
        num_blocks = int(np.ceil(n / block_size))

        resampled_indices = []
        for _ in range(num_blocks):
            start_idx = np.random.randint(0, n - block_size + 1)
            block_indices = list(range(start_idx, min(start_idx + block_size, n)))
            resampled_indices.extend(block_indices)

        resampled_indices = resampled_indices[:n]
        resampled = data.iloc[resampled_indices].copy()
        resampled.index = data.index
        return resampled

    def _parametric_resample(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Resample data using parametric approach (fit distribution and sample)

        Args:
            data: Original data

        Returns:
            Synthetic data
        """
        # Calculate returns
        returns = data['close'].pct_change().dropna()

        # Estimate parameters
        mu = returns.mean()
        sigma = returns.std()

        # Generate synthetic returns
        synthetic_returns = np.random.normal(mu, sigma, size=len(data))

        # Create synthetic prices
        synthetic_data = data.copy()
        synthetic_data['close'] = data['close'].iloc[0] * (1 + synthetic_returns).cumprod()

        # Adjust OHLV proportionally
        price_ratio = synthetic_data['close'] / data['close']
        synthetic_data['open'] = data['open'] * price_ratio
        synthetic_data['high'] = data['high'] * price_ratio
        synthetic_data['low'] = data['low'] * price_ratio

        return synthetic_data

    def _calculate_statistics(
        self,
        results: List[Dict[str, Any]],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Calculate statistical metrics from simulation results

        Args:
            results: List of simulation results
            initial_capital: Starting capital

        Returns:
            Dictionary with statistical metrics
        """
        returns = [r['total_return'] for r in results]
        final_equities = [r['final_equity'] for r in results]
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        max_drawdowns = [r['max_drawdown_pct'] for r in results]

        # Sort returns for percentile calculations
        sorted_returns = sorted(returns)
        sorted_equities = sorted(final_equities)

        # Calculate percentile indices
        alpha = 1 - self.confidence_level
        var_idx = int(alpha * len(sorted_returns))

        # Value at Risk (VaR) and Conditional Value at Risk (CVaR)
        var_95 = sorted_returns[var_idx]
        cvar_95 = np.mean(sorted_returns[:var_idx]) if var_idx > 0 else sorted_returns[0]

        # Probability of profit
        prob_profit = sum(1 for r in returns if r > 0) / len(returns)

        # Percentiles
        percentiles = {
            '5th': np.percentile(returns, 5),
            '25th': np.percentile(returns, 25),
            '50th': np.percentile(returns, 50),
            '75th': np.percentile(returns, 75),
            '95th': np.percentile(returns, 95),
        }

        return {
            'num_simulations': len(results),
            'initial_capital': initial_capital,

            # Return statistics
            'expected_return': np.mean(returns),
            'median_return': np.median(returns),
            'std_return': np.std(returns),
            'min_return': min(returns),
            'max_return': max(returns),

            # Risk metrics
            'var_95': var_95,
            'cvar_95': cvar_95,
            'prob_profit': prob_profit,

            # Final equity statistics
            'expected_final_equity': np.mean(final_equities),
            'median_final_equity': np.median(final_equities),
            'min_final_equity': min(final_equities),
            'max_final_equity': max(final_equities),

            # Performance metrics
            'avg_sharpe_ratio': np.mean(sharpe_ratios),
            'avg_max_drawdown': np.mean(max_drawdowns),

            # Percentiles
            'percentiles': percentiles,

            # Raw results
            'all_results': results,
        }

    def plot_results(
        self,
        save_path: Optional[str] = None,
        show_plot: bool = True
    ) -> None:
        """
        Plot Monte Carlo simulation results

        Args:
            save_path: Path to save plot (optional)
            show_plot: Whether to display plot
        """
        if not self.simulation_results:
            logger.warning("No simulation results to plot")
            return

        returns = [r['total_return'] for r in self.simulation_results]

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # 1. Histogram of returns
        axes[0, 0].hist(returns, bins=50, edgecolor='black', alpha=0.7)
        axes[0, 0].axvline(np.mean(returns), color='red', linestyle='--',
                          label=f'Mean: {np.mean(returns):.2%}')
        axes[0, 0].axvline(np.median(returns), color='green', linestyle='--',
                          label=f'Median: {np.median(returns):.2%}')
        axes[0, 0].set_xlabel('Total Return')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Distribution of Returns')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Box plot
        sharpe_ratios = [r['sharpe_ratio'] for r in self.simulation_results]
        axes[0, 1].boxplot([returns, sharpe_ratios], labels=['Returns', 'Sharpe Ratio'])
        axes[0, 1].set_ylabel('Value')
        axes[0, 1].set_title('Performance Metrics Distribution')
        axes[0, 1].grid(True, alpha=0.3)

        # 3. Scatter plot: Returns vs Sharpe
        axes[1, 0].scatter(returns, sharpe_ratios, alpha=0.5)
        axes[1, 0].set_xlabel('Total Return')
        axes[1, 0].set_ylabel('Sharpe Ratio')
        axes[1, 0].set_title('Return vs Sharpe Ratio')
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Cumulative distribution
        sorted_returns = sorted(returns)
        cumulative = np.arange(1, len(sorted_returns) + 1) / len(sorted_returns)
        axes[1, 1].plot(sorted_returns, cumulative)
        axes[1, 1].axhline(self.confidence_level, color='red', linestyle='--',
                          label=f'{self.confidence_level:.0%} Confidence')
        axes[1, 1].set_xlabel('Total Return')
        axes[1, 1].set_ylabel('Cumulative Probability')
        axes[1, 1].set_title('Cumulative Distribution Function')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Plot saved to {save_path}")

        if show_plot:
            plt.show()
        else:
            plt.close()

    def get_percentile_scenarios(
        self,
        percentiles: List[float] = [5, 25, 50, 75, 95]
    ) -> Dict[float, Dict[str, Any]]:
        """
        Get specific percentile scenarios

        Args:
            percentiles: List of percentile values

        Returns:
            Dictionary mapping percentiles to scenario details
        """
        if not self.simulation_results:
            return {}

        returns = [r['total_return'] for r in self.simulation_results]
        scenarios = {}

        for p in percentiles:
            percentile_return = np.percentile(returns, p)
            # Find closest scenario
            closest_idx = min(
                range(len(returns)),
                key=lambda i: abs(returns[i] - percentile_return)
            )
            scenarios[p] = self.simulation_results[closest_idx]

        return scenarios
