"""
Unit tests for ML models.

Tests cover:
- Model training and prediction
- Feature importance
- Model persistence
- Prediction accuracy
"""
import pytest
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier


@pytest.mark.unit
class TestMLModels:
    """Test suite for machine learning models."""

    def test_model_training(self, sample_ohlcv_data):
        """Test model can be trained without errors."""
        # Prepare simple features
        features = pd.DataFrame({
            'returns': sample_ohlcv_data['close'].pct_change(),
            'volume': sample_ohlcv_data['volume']
        }).fillna(0)

        # Simple binary labels (up/down)
        labels = (sample_ohlcv_data['close'].shift(-1) > sample_ohlcv_data['close']).astype(int)

        # Drop last row (no future price)
        X = features[:-1]
        y = labels[:-1]

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)

        assert model.n_estimators == 10
        assert hasattr(model, 'feature_importances_')

    def test_model_prediction(self):
        """Test model makes valid predictions."""
        X_train = np.random.randn(100, 5)
        y_train = np.random.randint(0, 2, 100)

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)

        X_test = np.random.randn(20, 5)
        predictions = model.predict(X_test)

        # Predictions should be 0 or 1
        assert all(p in [0, 1] for p in predictions)
        assert len(predictions) == len(X_test)

    def test_prediction_probabilities(self):
        """Test model outputs valid probabilities."""
        X_train = np.random.randn(100, 5)
        y_train = np.random.randint(0, 2, 100)

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)

        X_test = np.random.randn(20, 5)
        probabilities = model.predict_proba(X_test)

        # Should have 2 columns (binary classification)
        assert probabilities.shape == (20, 2)

        # Probabilities should sum to 1
        assert np.allclose(probabilities.sum(axis=1), 1.0)

        # Probabilities should be between 0 and 1
        assert (probabilities >= 0).all() and (probabilities <= 1).all()

    def test_feature_importance(self):
        """Test feature importance extraction."""
        X_train = np.random.randn(100, 5)
        y_train = np.random.randint(0, 2, 100)

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)

        importances = model.feature_importances_

        # Should have importance for each feature
        assert len(importances) == 5

        # Importances should sum to 1
        assert abs(importances.sum() - 1.0) < 1e-6

        # All importances should be non-negative
        assert (importances >= 0).all()


@pytest.mark.unit
class TestModelValidation:
    """Test suite for model validation and evaluation."""

    def test_train_test_split(self, sample_ohlcv_data):
        """Test proper train/test splitting."""
        # Time series should use temporal split, not random
        split_idx = int(len(sample_ohlcv_data) * 0.8)

        train_data = sample_ohlcv_data[:split_idx]
        test_data = sample_ohlcv_data[split_idx:]

        # Train data should be before test data
        assert train_data['timestamp'].max() < test_data['timestamp'].min()

        # No data leakage
        assert len(set(train_data.index) & set(test_data.index)) == 0

    def test_cross_validation_strategy(self):
        """Test time series cross-validation."""
        # Should use forward-chaining, not random K-fold
        # This prevents future data leakage

        # Example: TimeSeriesSplit from sklearn
        from sklearn.model_selection import TimeSeriesSplit

        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)

        tscv = TimeSeriesSplit(n_splits=5)

        for train_idx, test_idx in tscv.split(X):
            # Train indices should always be before test indices
            assert train_idx.max() < test_idx.min()

    def test_no_data_leakage(self):
        """Critical: Test for data leakage in feature engineering."""
        # When calculating features like mean, std, etc.
        # Should only use past data (expanding window, not rolling)

        prices = pd.Series([100, 102, 101, 103, 105, 104, 106])

        # Correct: Expanding mean (only past data)
        expanding_mean = prices.expanding().mean()

        # At each point, mean should only include prior data
        for i in range(1, len(prices)):
            expected_mean = prices[:i+1].mean()
            assert abs(expanding_mean.iloc[i] - expected_mean) < 1e-10


@pytest.mark.unit
class TestModelPersistence:
    """Test model saving and loading."""

    def test_save_and_load_model(self, tmp_path):
        """Test model can be saved and loaded."""
        import pickle

        # Train a simple model
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)

        # Save model
        model_path = tmp_path / "model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        # Load model
        with open(model_path, 'rb') as f:
            loaded_model = pickle.load(f)

        # Make predictions with both models
        X_test = np.random.randn(10, 5)
        original_pred = model.predict(X_test)
        loaded_pred = loaded_model.predict(X_test)

        # Predictions should be identical
        assert np.array_equal(original_pred, loaded_pred)
