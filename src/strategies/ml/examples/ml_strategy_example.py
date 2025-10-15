"""
ML-Based Trading Strategy Example

Demonstrates complete ML strategy workflow:
1. Load and prepare market data
2. Engineer features
3. Train prediction model
4. Validate model
5. Generate trading signals
6. Backtest strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.strategies.ml.features.feature_engineering import FeatureEngineer, FeatureConfig
from src.strategies.ml.models.price_predictor import PricePredictor
from src.strategies.ml.models.trend_classifier import TrendClassifier
from src.strategies.ml.validation.model_validator import ModelValidator
from src.strategies.ml.validation.cross_validator import CrossValidator


class MLTradingStrategy:
    """
    Complete ML-based trading strategy example.

    This strategy combines:
    - Feature engineering
    - Price prediction (regression)
    - Trend classification
    - Risk management
    - Backtesting

    Example:
        >>> strategy = MLTradingStrategy('AAPL')
        >>> strategy.load_data('data/aapl_1h.csv')
        >>> strategy.train_models()
        >>> signals = strategy.generate_signals()
        >>> results = strategy.backtest()
    """

    def __init__(
        self,
        symbol: str,
        model_type: str = 'random_forest',
        lookback_periods: list = None
    ):
        """
        Initialize ML trading strategy.

        Args:
            symbol: Trading symbol
            model_type: Type of ML model ('random_forest', 'gradient_boosting')
            lookback_periods: Periods for feature engineering
        """
        self.symbol = symbol
        self.model_type = model_type

        # Initialize feature engineer
        config = FeatureConfig(
            lookback_periods=lookback_periods or [5, 10, 20, 50],
            technical_indicators=['sma', 'ema', 'rsi', 'macd', 'bbands'],
            statistical_features=['returns', 'volatility', 'volume_ratio']
        )
        self.feature_engineer = FeatureEngineer(config)

        # Initialize models
        self.price_model = PricePredictor(model_type=model_type)
        self.trend_model = TrendClassifier(model_type=model_type)

        # Initialize validators
        self.validator = ModelValidator()
        self.cv = CrossValidator(n_splits=5)

        # Data storage
        self.raw_data: pd.DataFrame = None
        self.features: pd.DataFrame = None
        self.X: np.ndarray = None
        self.y_price: np.ndarray = None
        self.y_trend: np.ndarray = None

    def load_data(self, data_path: str = None, df: pd.DataFrame = None) -> None:
        """
        Load market data.

        Args:
            data_path: Path to CSV file with OHLCV data
            df: Or pass DataFrame directly
        """
        if data_path:
            self.raw_data = pd.read_csv(data_path, index_col=0, parse_dates=True)
        elif df is not None:
            self.raw_data = df
        else:
            # Generate synthetic data for demonstration
            self.raw_data = self._generate_synthetic_data()

        print(f"Loaded {len(self.raw_data)} bars of {self.symbol} data")

    def _generate_synthetic_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """Generate synthetic OHLCV data for testing."""
        np.random.seed(42)

        # Generate price with trend and noise
        trend = np.linspace(100, 150, n_samples)
        noise = np.random.normal(0, 2, n_samples)
        close = trend + noise.cumsum() * 0.1

        # Generate OHLC
        high = close + np.random.uniform(0, 2, n_samples)
        low = close - np.random.uniform(0, 2, n_samples)
        open_price = close + np.random.normal(0, 1, n_samples)

        # Generate volume
        volume = np.random.uniform(100000, 1000000, n_samples)

        # Create DataFrame
        dates = pd.date_range('2024-01-01', periods=n_samples, freq='1H')
        df = pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }, index=dates)

        return df

    def engineer_features(self) -> None:
        """Engineer features from raw data."""
        print("Engineering features...")
        self.features = self.feature_engineer.engineer_features(self.raw_data)
        print(f"Created {len(self.feature_engineer.feature_names)} features")

    def prepare_datasets(self) -> None:
        """Prepare datasets for training."""
        print("Preparing datasets...")

        # For price prediction
        self.X, self.y_price = self.feature_engineer.prepare_ml_dataset(
            self.features,
            target_col='next_return',
            scale_features=True
        )

        # For trend classification
        _, self.y_trend = self.feature_engineer.prepare_ml_dataset(
            self.features,
            target_col='next_return',
            scale_features=False
        )

        print(f"Dataset shape: {self.X.shape}")
        print(f"Samples: {len(self.X)}")

    def train_models(self, validation_method: str = 'walk_forward') -> Dict:
        """
        Train both price and trend models.

        Args:
            validation_method: Validation method to use

        Returns:
            Dictionary with validation results
        """
        print("\n" + "="*60)
        print("TRAINING MODELS")
        print("="*60)

        results = {}

        # Train price prediction model
        print("\n1. Training Price Prediction Model...")
        price_results = self.validator.validate_model(
            self.price_model,
            self.X,
            self.y_price,
            method=validation_method,
            n_splits=5
        )
        results['price_model'] = price_results
        print(self.validator.get_validation_report())

        # Train trend classification model
        print("\n2. Training Trend Classification Model...")
        trend_results = self.validator.validate_model(
            self.trend_model,
            self.X,
            self.y_trend,
            method=validation_method,
            n_splits=5
        )
        results['trend_model'] = trend_results
        print(self.validator.get_validation_report())

        return results

    def cross_validate_models(self) -> Dict:
        """
        Perform cross-validation on models.

        Returns:
            CV results for both models
        """
        print("\n" + "="*60)
        print("CROSS-VALIDATION")
        print("="*60)

        results = {}

        # CV for price model
        print("\n1. Price Model Cross-Validation...")
        price_cv = self.cv.cross_validate(
            self.price_model,
            self.X,
            self.y_price,
            method='time_series'
        )
        results['price_cv'] = price_cv
        print(self.cv.get_cv_report())

        # CV for trend model
        print("\n2. Trend Model Cross-Validation...")
        trend_cv = self.cv.cross_validate(
            self.trend_model,
            self.X,
            self.y_trend,
            method='time_series'
        )
        results['trend_cv'] = trend_cv
        print(self.cv.get_cv_report())

        return results

    def generate_signals(self, confidence_threshold: float = 0.6) -> pd.DataFrame:
        """
        Generate trading signals using trained models.

        Args:
            confidence_threshold: Minimum confidence for signals

        Returns:
            DataFrame with signals
        """
        print("\nGenerating trading signals...")

        # Get predictions
        price_pred = self.price_model.predict(self.X)
        trend_pred, trend_conf = self.trend_model.predict_with_confidence(
            self.X, threshold=confidence_threshold
        )

        # Create signals DataFrame
        signals = pd.DataFrame({
            'predicted_return': price_pred,
            'trend': trend_pred,
            'confidence': trend_conf
        })

        # Generate trading signal
        # Buy: uptrend (2) with high confidence
        # Sell: downtrend (0) with high confidence
        # Hold: neutral (1) or low confidence
        signals['signal'] = 0  # Hold
        signals.loc[(signals['trend'] == 2) & signals['confidence'], 'signal'] = 1  # Buy
        signals.loc[(signals['trend'] == 0) & signals['confidence'], 'signal'] = -1  # Sell

        return signals

    def backtest(self, signals: pd.DataFrame = None, initial_capital: float = 100000) -> Dict:
        """
        Simple backtest of ML strategy.

        Args:
            signals: Trading signals DataFrame
            initial_capital: Starting capital

        Returns:
            Backtest results
        """
        if signals is None:
            signals = self.generate_signals()

        print("\n" + "="*60)
        print("BACKTESTING")
        print("="*60)

        # Align signals with price data
        returns = self.features['returns'].iloc[:len(signals)]

        # Calculate strategy returns
        strategy_returns = signals['signal'].shift(1) * returns

        # Calculate cumulative returns
        cumulative_returns = (1 + strategy_returns).cumprod()
        final_value = initial_capital * cumulative_returns.iloc[-1]

        # Calculate metrics
        total_return = (final_value - initial_capital) / initial_capital
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()

        # Count trades
        n_trades = (signals['signal'].diff() != 0).sum()

        results = {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'n_trades': n_trades,
            'win_rate': (strategy_returns > 0).sum() / len(strategy_returns)
        }

        # Print results
        print(f"\nInitial Capital: ${initial_capital:,.2f}")
        print(f"Final Value:     ${final_value:,.2f}")
        print(f"Total Return:    {total_return*100:.2f}%")
        print(f"Annual Return:   {annual_return*100:.2f}%")
        print(f"Sharpe Ratio:    {sharpe_ratio:.2f}")
        print(f"Max Drawdown:    {max_drawdown*100:.2f}%")
        print(f"Number of Trades: {n_trades}")
        print(f"Win Rate:        {results['win_rate']*100:.2f}%")

        return results

    def save_models(self, output_dir: str = 'models') -> None:
        """Save trained models."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.price_model.save_model(f"{output_dir}/{self.symbol}_price_model")
        self.trend_model.save_model(f"{output_dir}/{self.symbol}_trend_model")

        print(f"\nModels saved to {output_dir}/")


def main():
    """Run complete ML strategy example."""
    print("="*60)
    print("ML TRADING STRATEGY EXAMPLE")
    print("="*60)

    # Initialize strategy
    strategy = MLTradingStrategy('AAPL', model_type='random_forest')

    # Load data (using synthetic data for demo)
    strategy.load_data()

    # Engineer features
    strategy.engineer_features()

    # Prepare datasets
    strategy.prepare_datasets()

    # Train models with validation
    train_results = strategy.train_models(validation_method='walk_forward')

    # Cross-validate
    cv_results = strategy.cross_validate_models()

    # Generate signals and backtest
    signals = strategy.generate_signals(confidence_threshold=0.6)
    backtest_results = strategy.backtest(signals)

    # Save models
    strategy.save_models('models')

    print("\n" + "="*60)
    print("STRATEGY EXECUTION COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()
