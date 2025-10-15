"""
Price Prediction Model

Implements regression-based price forecasting using various ML algorithms.
"""

import numpy as np
from typing import Dict, Optional, Literal
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from .base_model import BaseMLModel


class PricePredictor(BaseMLModel):
    """
    Price prediction model using regression algorithms.

    Supports multiple regression models:
    - Random Forest
    - Gradient Boosting
    - Ridge Regression
    - Lasso Regression

    Example:
        >>> predictor = PricePredictor(model_type='random_forest')
        >>> metrics = predictor.train(X_train, y_train)
        >>> predictions = predictor.predict(X_test)
        >>> eval_metrics = predictor.evaluate(X_test, y_test)
    """

    def __init__(
        self,
        model_type: Literal['random_forest', 'gradient_boosting', 'ridge', 'lasso'] = 'random_forest',
        **model_params
    ):
        """
        Initialize price predictor.

        Args:
            model_type: Type of regression model to use
            **model_params: Additional parameters for the model
        """
        super().__init__(model_name=f'price_predictor_{model_type}')

        self.model_type = model_type
        self.model = self._create_model(model_type, model_params)

        # Add assumptions
        self.add_assumption("Market data is stationary or trend-stationary")
        self.add_assumption("Historical patterns are predictive of future prices")
        self.add_assumption("Features are independent and identically distributed")

        # Add limitations
        self.add_limitation("Cannot predict black swan events")
        self.add_limitation("Performance degrades during high volatility periods")
        self.add_limitation("Assumes continuous trading (no gaps)")

    def _create_model(self, model_type: str, params: dict):
        """Create the appropriate regression model."""
        if model_type == 'random_forest':
            return RandomForestRegressor(
                n_estimators=params.get('n_estimators', 100),
                max_depth=params.get('max_depth', 10),
                min_samples_split=params.get('min_samples_split', 5),
                random_state=params.get('random_state', 42),
                n_jobs=params.get('n_jobs', -1)
            )
        elif model_type == 'gradient_boosting':
            return GradientBoostingRegressor(
                n_estimators=params.get('n_estimators', 100),
                learning_rate=params.get('learning_rate', 0.1),
                max_depth=params.get('max_depth', 5),
                random_state=params.get('random_state', 42)
            )
        elif model_type == 'ridge':
            return Ridge(
                alpha=params.get('alpha', 1.0),
                random_state=params.get('random_state', 42)
            )
        elif model_type == 'lasso':
            return Lasso(
                alpha=params.get('alpha', 1.0),
                random_state=params.get('random_state', 42)
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """
        Train the price prediction model.

        Args:
            X: Training features (n_samples, n_features)
            y: Training targets (n_samples,)
            **kwargs: Additional training parameters

        Returns:
            Training metrics (MSE, MAE, R2)
        """
        # Train model
        self.model.fit(X, y)
        self.is_trained = True

        # Calculate training metrics
        y_pred = self.model.predict(X)
        metrics = {
            'train_mse': mean_squared_error(y, y_pred),
            'train_mae': mean_absolute_error(y, y_pred),
            'train_r2': r2_score(y, y_pred),
            'train_rmse': np.sqrt(mean_squared_error(y, y_pred))
        }

        # Store in metadata
        self.metadata['train_metrics'] = metrics
        self.metadata['n_samples'] = len(X)
        self.metadata['n_features'] = X.shape[1]

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict future prices.

        Args:
            X: Features to predict on (n_samples, n_features)

        Returns:
            Predicted prices (n_samples,)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")

        return self.model.predict(X)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model on test data.

        Args:
            X: Test features
            y: Test targets

        Returns:
            Evaluation metrics
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")

        y_pred = self.predict(X)

        metrics = {
            'test_mse': mean_squared_error(y, y_pred),
            'test_mae': mean_absolute_error(y, y_pred),
            'test_r2': r2_score(y, y_pred),
            'test_rmse': np.sqrt(mean_squared_error(y, y_pred)),
            'mape': np.mean(np.abs((y - y_pred) / y)) * 100  # Mean Absolute Percentage Error
        }

        # Store in metadata
        self.metadata['test_metrics'] = metrics

        return metrics

    def get_feature_importance(self) -> Optional[np.ndarray]:
        """
        Get feature importance scores.

        Returns:
            Feature importance array (only for tree-based models)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        else:
            return None

    def predict_with_confidence(
        self,
        X: np.ndarray,
        n_estimators: Optional[int] = None
    ) -> tuple:
        """
        Predict with confidence intervals (for ensemble models).

        Args:
            X: Features to predict on
            n_estimators: Number of estimators to use for variance calculation

        Returns:
            Tuple of (predictions, std_dev) for ensemble models
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")

        if self.model_type in ['random_forest', 'gradient_boosting']:
            # Get predictions from individual estimators
            predictions = np.array([
                tree.predict(X) for tree in self.model.estimators_
            ])

            mean_pred = predictions.mean(axis=0)
            std_pred = predictions.std(axis=0)

            return mean_pred, std_pred
        else:
            # For non-ensemble models, return predictions with zero std
            predictions = self.predict(X)
            return predictions, np.zeros_like(predictions)
