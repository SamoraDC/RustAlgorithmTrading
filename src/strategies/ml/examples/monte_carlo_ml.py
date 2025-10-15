"""
Monte Carlo Simulation for ML Trading Strategies

Implements Monte Carlo methods specifically designed for ML strategies:
1. Model prediction uncertainty
2. Feature perturbation analysis
3. Strategy robustness testing
4. Risk assessment
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulations."""
    n_simulations: int = 1000
    confidence_level: float = 0.95
    random_seed: int = 42


class MLMonteCarloSimulator:
    """
    Monte Carlo simulator for ML trading strategies.

    Provides:
    - Prediction uncertainty quantification
    - Feature importance via permutation
    - Strategy robustness testing
    - Risk metrics (VaR, CVaR)

    Example:
        >>> simulator = MLMonteCarloSimulator()
        >>> results = simulator.simulate_strategy_returns(model, X, y)
        >>> var_95 = results['var_95']
    """

    def __init__(self, config: Optional[MonteCarloConfig] = None):
        """
        Initialize Monte Carlo simulator.

        Args:
            config: Simulation configuration
        """
        self.config = config or MonteCarloConfig()
        np.random.seed(self.config.random_seed)

    def simulate_prediction_uncertainty(
        self,
        model,
        X: np.ndarray,
        n_simulations: Optional[int] = None
    ) -> Dict:
        """
        Simulate prediction uncertainty using bootstrap.

        Args:
            model: Trained ML model
            X: Features to predict on
            n_simulations: Number of bootstrap samples

        Returns:
            Dictionary with prediction statistics
        """
        n_simulations = n_simulations or self.config.n_simulations
        n_samples = len(X)

        predictions = []

        for _ in range(n_simulations):
            # Bootstrap sample
            indices = np.random.choice(n_samples, size=n_samples, replace=True)
            X_bootstrap = X[indices]

            # Predict
            pred = model.predict(X_bootstrap)
            predictions.append(pred)

        predictions = np.array(predictions)

        # Calculate statistics
        mean_pred = predictions.mean(axis=0)
        std_pred = predictions.std(axis=0)
        lower_bound = np.percentile(predictions, 2.5, axis=0)
        upper_bound = np.percentile(predictions, 97.5, axis=0)

        return {
            'mean': mean_pred,
            'std': std_pred,
            'lower_95': lower_bound,
            'upper_95': upper_bound,
            'predictions': predictions
        }

    def feature_permutation_importance(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        n_repeats: int = 10
    ) -> pd.DataFrame:
        """
        Calculate feature importance via permutation.

        Args:
            model: Trained model
            X: Test features
            y: Test targets
            feature_names: Names of features
            n_repeats: Number of permutations per feature

        Returns:
            DataFrame with feature importance scores
        """
        # Baseline score
        baseline_score = model.evaluate(X, y)
        baseline_metric = list(baseline_score.values())[0]

        importances = []

        for i, feature_name in enumerate(feature_names):
            scores = []

            for _ in range(n_repeats):
                # Permute feature
                X_permuted = X.copy()
                X_permuted[:, i] = np.random.permutation(X_permuted[:, i])

                # Evaluate with permuted feature
                score = model.evaluate(X_permuted, y)
                metric = list(score.values())[0]
                scores.append(baseline_metric - metric)

            importances.append({
                'feature': feature_name,
                'importance_mean': np.mean(scores),
                'importance_std': np.std(scores)
            })

        return pd.DataFrame(importances).sort_values('importance_mean', ascending=False)

    def simulate_strategy_returns(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        initial_capital: float = 100000,
        n_simulations: Optional[int] = None
    ) -> Dict:
        """
        Monte Carlo simulation of strategy returns.

        Args:
            model: Trained trading model
            X: Features
            y: Actual returns
            initial_capital: Starting capital
            n_simulations: Number of simulations

        Returns:
            Dictionary with simulation results and risk metrics
        """
        n_simulations = n_simulations or self.config.n_simulations

        # Get predictions
        predictions = model.predict(X)

        # Generate signals (simple threshold)
        signals = np.zeros_like(predictions)
        signals[predictions > 0] = 1
        signals[predictions < 0] = -1

        final_values = []
        max_drawdowns = []
        sharpe_ratios = []

        for _ in range(n_simulations):
            # Add noise to returns (simulate market uncertainty)
            noise_std = np.std(y) * 0.1  # 10% noise
            noisy_returns = y + np.random.normal(0, noise_std, len(y))

            # Calculate strategy returns
            strategy_returns = signals * noisy_returns

            # Calculate cumulative wealth
            cumulative = initial_capital * (1 + strategy_returns).cumprod()

            # Final value
            final_values.append(cumulative.iloc[-1] if isinstance(cumulative, pd.Series) else cumulative[-1])

            # Max drawdown
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdowns.append(drawdown.min() if isinstance(drawdown, pd.Series) else np.min(drawdown))

            # Sharpe ratio
            mean_return = strategy_returns.mean()
            std_return = strategy_returns.std()
            sharpe = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
            sharpe_ratios.append(sharpe)

        # Calculate risk metrics
        final_values = np.array(final_values)
        returns = (final_values - initial_capital) / initial_capital

        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()

        return {
            'mean_return': returns.mean(),
            'std_return': returns.std(),
            'median_return': np.median(returns),
            'var_95': var_95,  # Value at Risk (95% confidence)
            'cvar_95': cvar_95,  # Conditional VaR
            'mean_sharpe': np.mean(sharpe_ratios),
            'mean_max_drawdown': np.mean(max_drawdowns),
            'prob_profit': (returns > 0).sum() / len(returns),
            'percentile_5': np.percentile(returns, 5),
            'percentile_95': np.percentile(returns, 95),
            'all_returns': returns,
            'all_sharpe': sharpe_ratios,
            'all_drawdowns': max_drawdowns
        }

    def stress_test_features(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        stress_factor: float = 2.0,
        n_simulations: int = 100
    ) -> Dict:
        """
        Stress test model by perturbing features.

        Args:
            model: Trained model
            X: Features
            y: Targets
            stress_factor: Multiplier for feature perturbation
            n_simulations: Number of stress scenarios

        Returns:
            Dictionary with stress test results
        """
        baseline_metrics = model.evaluate(X, y)
        stressed_metrics = []

        for _ in range(n_simulations):
            # Random stress scenario
            perturbation = np.random.normal(1.0, stress_factor * 0.1, X.shape)
            X_stressed = X * perturbation

            # Evaluate under stress
            metrics = model.evaluate(X_stressed, y)
            stressed_metrics.append(metrics)

        # Aggregate results
        metric_names = list(baseline_metrics.keys())
        results = {'baseline': baseline_metrics}

        for metric in metric_names:
            values = [m[metric] for m in stressed_metrics]
            results[f'{metric}_mean_stressed'] = np.mean(values)
            results[f'{metric}_std_stressed'] = np.std(values)
            results[f'{metric}_worst'] = np.min(values) if 'r2' in metric else np.max(values)

        return results

    def bootstrap_confidence_intervals(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        n_bootstrap: int = 1000,
        confidence: float = 0.95
    ) -> Dict:
        """
        Calculate confidence intervals via bootstrap.

        Args:
            model: Trained model
            X: Features
            y: Targets
            n_bootstrap: Number of bootstrap samples
            confidence: Confidence level

        Returns:
            Dictionary with confidence intervals for each metric
        """
        alpha = 1 - confidence
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100

        all_metrics = []

        for _ in range(n_bootstrap):
            # Bootstrap sample
            indices = np.random.choice(len(X), size=len(X), replace=True)
            X_boot = X[indices]
            y_boot = y[indices]

            # Evaluate
            metrics = model.evaluate(X_boot, y_boot)
            all_metrics.append(metrics)

        # Calculate confidence intervals
        results = {}
        metric_names = list(all_metrics[0].keys())

        for metric in metric_names:
            values = [m[metric] for m in all_metrics]
            results[f'{metric}_mean'] = np.mean(values)
            results[f'{metric}_lower'] = np.percentile(values, lower_percentile)
            results[f'{metric}_upper'] = np.percentile(values, upper_percentile)

        return results

    def generate_simulation_report(
        self,
        strategy_results: Dict,
        feature_importance: pd.DataFrame = None
    ) -> str:
        """
        Generate comprehensive simulation report.

        Args:
            strategy_results: Results from simulate_strategy_returns
            feature_importance: Feature importance DataFrame

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 70)
        report.append("MONTE CARLO SIMULATION REPORT - ML TRADING STRATEGY")
        report.append("=" * 70)
        report.append("")

        # Strategy performance
        report.append("STRATEGY PERFORMANCE METRICS:")
        report.append(f"  Mean Return:           {strategy_results['mean_return']*100:.2f}%")
        report.append(f"  Median Return:         {strategy_results['median_return']*100:.2f}%")
        report.append(f"  Std Return:            {strategy_results['std_return']*100:.2f}%")
        report.append(f"  Mean Sharpe Ratio:     {strategy_results['mean_sharpe']:.2f}")
        report.append("")

        # Risk metrics
        report.append("RISK METRICS:")
        report.append(f"  VaR (95%):             {strategy_results['var_95']*100:.2f}%")
        report.append(f"  CVaR (95%):            {strategy_results['cvar_95']*100:.2f}%")
        report.append(f"  Mean Max Drawdown:     {strategy_results['mean_max_drawdown']*100:.2f}%")
        report.append(f"  Probability of Profit: {strategy_results['prob_profit']*100:.2f}%")
        report.append("")

        # Confidence intervals
        report.append("CONFIDENCE INTERVALS (95%):")
        report.append(f"  5th Percentile:        {strategy_results['percentile_5']*100:.2f}%")
        report.append(f"  95th Percentile:       {strategy_results['percentile_95']*100:.2f}%")
        report.append("")

        # Feature importance
        if feature_importance is not None:
            report.append("TOP 10 IMPORTANT FEATURES:")
            for idx, row in feature_importance.head(10).iterrows():
                report.append(f"  {row['feature']:30s} {row['importance_mean']:8.4f} "
                            f"(±{row['importance_std']:.4f})")
            report.append("")

        report.append("=" * 70)

        return "\n".join(report)


def main():
    """Example usage of ML Monte Carlo simulator."""
    print("Monte Carlo Simulation for ML Trading Strategies\n")

    # Generate synthetic data
    np.random.seed(42)
    n_samples = 1000
    n_features = 10

    X = np.random.randn(n_samples, n_features)
    y = X[:, 0] * 0.01 + np.random.randn(n_samples) * 0.02  # Noisy linear relationship

    # Create and train simple model
    from sklearn.ensemble import RandomForestRegressor
    from src.strategies.ml.models import PricePredictor

    model = PricePredictor(model_type='random_forest', n_estimators=50)
    model.train(X[:800], y[:800])

    # Initialize simulator
    simulator = MLMonteCarloSimulator(MonteCarloConfig(n_simulations=500))

    print("1. Simulating prediction uncertainty...")
    uncertainty = simulator.simulate_prediction_uncertainty(model, X[800:])
    print(f"   Mean prediction std: {uncertainty['std'].mean():.4f}\n")

    print("2. Calculating feature importance...")
    feature_names = [f"feature_{i}" for i in range(n_features)]
    importance = simulator.feature_permutation_importance(
        model, X[800:], y[800:], feature_names
    )
    print(f"   Top 3 features: {importance['feature'].head(3).tolist()}\n")

    print("3. Simulating strategy returns...")
    results = simulator.simulate_strategy_returns(model, X[800:], y[800:])

    print("\n" + simulator.generate_simulation_report(results, importance))


if __name__ == '__main__':
    main()
