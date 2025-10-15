"""
Walk-Forward Analysis for robust strategy validation

Walk-forward analysis divides data into multiple training and testing periods
to evaluate how well a strategy generalizes to unseen data.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime, timedelta

from src.strategies.base import Strategy
from src.backtesting.engine import BacktestEngine


@dataclass
class WalkForwardWindow:
    """Represents a single walk-forward window"""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    window_id: int


class WalkForwardAnalyzer:
    """
    Walk-forward analysis implementation for strategy validation

    This approach tests strategy robustness by:
    1. Training on in-sample data
    2. Testing on out-of-sample data
    3. Rolling forward and repeating

    Attributes:
        train_period: Training period length in days
        test_period: Testing period length in days
        step_size: Days to move forward between windows
    """

    def __init__(
        self,
        train_period_days: int = 252,  # ~1 year
        test_period_days: int = 63,     # ~3 months
        step_size_days: int = 63,       # ~3 months
        optimization_metric: str = 'sharpe_ratio'
    ):
        """
        Initialize walk-forward analyzer

        Args:
            train_period_days: Number of days for training window
            test_period_days: Number of days for testing window
            step_size_days: Days to move forward between windows
            optimization_metric: Metric to optimize during training
        """
        self.train_period = train_period_days
        self.test_period = test_period_days
        self.step_size = step_size_days
        self.optimization_metric = optimization_metric

        logger.info(
            f"WalkForwardAnalyzer initialized: train={train_period_days}d, "
            f"test={test_period_days}d, step={step_size_days}d"
        )

    def create_windows(
        self,
        data: pd.DataFrame
    ) -> List[WalkForwardWindow]:
        """
        Create walk-forward windows from data

        Args:
            data: DataFrame with datetime index

        Returns:
            List of WalkForwardWindow objects
        """
        windows = []
        start_date = data.index[0]
        end_date = data.index[-1]

        window_id = 0
        current_date = start_date

        while True:
            train_start = current_date
            train_end = train_start + timedelta(days=self.train_period)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_period)

            # Check if we have enough data
            if test_end > end_date:
                break

            windows.append(WalkForwardWindow(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                window_id=window_id
            ))

            window_id += 1
            current_date += timedelta(days=self.step_size)

        logger.info(f"Created {len(windows)} walk-forward windows")
        return windows

    def run_analysis(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        parameter_grid: Dict[str, List[Any]],
        symbol: str = "UNKNOWN",
        initial_capital: float = 100000.0
    ) -> Dict[str, Any]:
        """
        Run complete walk-forward analysis

        Args:
            strategy_class: Strategy class to test
            data: Historical price data
            parameter_grid: Dictionary of parameters to optimize
            symbol: Stock symbol
            initial_capital: Starting capital

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting walk-forward analysis for {symbol}")

        windows = self.create_windows(data)
        window_results = []

        for window in windows:
            logger.info(
                f"Processing window {window.window_id}: "
                f"train={window.train_start.date()} to {window.train_end.date()}, "
                f"test={window.test_start.date()} to {window.test_end.date()}"
            )

            # Split data
            train_data = data[window.train_start:window.train_end]
            test_data = data[window.test_start:window.test_end]

            if len(train_data) < 30 or len(test_data) < 10:
                logger.warning(f"Insufficient data in window {window.window_id}, skipping")
                continue

            # Optimize on training data
            best_params = self._optimize_parameters(
                strategy_class=strategy_class,
                data=train_data,
                parameter_grid=parameter_grid,
                symbol=symbol,
                initial_capital=initial_capital
            )

            # Test on out-of-sample data
            test_strategy = strategy_class(
                name=f"{strategy_class.__name__}_window_{window.window_id}",
                parameters=best_params
            )

            engine = BacktestEngine(initial_capital=initial_capital)
            test_results = engine.run(test_strategy, test_data, symbol)

            window_results.append({
                'window_id': window.window_id,
                'train_start': window.train_start,
                'train_end': window.train_end,
                'test_start': window.test_start,
                'test_end': window.test_end,
                'best_params': best_params,
                'test_results': test_results,
                'sharpe_ratio': test_results.get('sharpe_ratio', 0.0),
                'total_return': test_results.get('total_return', 0.0),
                'max_drawdown': test_results.get('max_drawdown', 0.0)
            })

        # Aggregate results
        aggregated = self._aggregate_results(window_results, initial_capital)

        logger.info(
            f"Walk-forward analysis complete: "
            f"Avg Sharpe={aggregated['avg_sharpe']:.2f}, "
            f"Avg Return={aggregated['avg_return']:.2%}"
        )

        return {
            'windows': window_results,
            'aggregated': aggregated,
            'symbol': symbol
        }

    def _optimize_parameters(
        self,
        strategy_class: type,
        data: pd.DataFrame,
        parameter_grid: Dict[str, List[Any]],
        symbol: str,
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters on training data

        Args:
            strategy_class: Strategy class to optimize
            data: Training data
            parameter_grid: Parameters to test
            symbol: Stock symbol
            initial_capital: Starting capital

        Returns:
            Best parameters found
        """
        from itertools import product

        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        combinations = list(product(*param_values))

        best_score = -np.inf
        best_params = {}

        logger.info(f"Testing {len(combinations)} parameter combinations")

        for combo in combinations:
            params = dict(zip(param_names, combo))

            try:
                strategy = strategy_class(
                    name=f"{strategy_class.__name__}_opt",
                    parameters=params
                )

                engine = BacktestEngine(initial_capital=initial_capital)
                results = engine.run(strategy, data, symbol)

                score = results.get(self.optimization_metric, -np.inf)

                if score > best_score:
                    best_score = score
                    best_params = params.copy()

            except Exception as e:
                logger.warning(f"Error testing parameters {params}: {e}")
                continue

        logger.info(
            f"Best parameters: {best_params} "
            f"({self.optimization_metric}={best_score:.4f})"
        )

        return best_params

    def _aggregate_results(
        self,
        window_results: List[Dict[str, Any]],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Aggregate results across all windows

        Args:
            window_results: List of window results
            initial_capital: Starting capital

        Returns:
            Aggregated metrics
        """
        if not window_results:
            return {}

        sharpe_ratios = [w['sharpe_ratio'] for w in window_results]
        returns = [w['total_return'] for w in window_results]
        drawdowns = [w['max_drawdown'] for w in window_results]

        # Calculate compound return across windows
        compound_return = 1.0
        for ret in returns:
            compound_return *= (1 + ret)
        compound_return -= 1.0

        return {
            'num_windows': len(window_results),
            'avg_sharpe': np.mean(sharpe_ratios),
            'std_sharpe': np.std(sharpe_ratios),
            'avg_return': np.mean(returns),
            'std_return': np.std(returns),
            'compound_return': compound_return,
            'avg_drawdown': np.mean(drawdowns),
            'max_drawdown': np.max(drawdowns),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns)
        }
