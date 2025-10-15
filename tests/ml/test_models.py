"""
Unit tests for ML models.
"""

import pytest
import numpy as np
from src.strategies.ml.models import PricePredictor, TrendClassifier


@pytest.fixture
def sample_data():
    """Generate sample data for testing."""
    np.random.seed(42)
    n_samples = 200
    n_features = 10

    X = np.random.randn(n_samples, n_features)
    y = X[:, 0] * 0.1 + np.random.randn(n_samples) * 0.05

    return X, y


def test_price_predictor_train(sample_data):
    """Test price predictor training."""
    X, y = sample_data
    model = PricePredictor(model_type='random_forest')

    metrics = model.train(X, y)

    assert model.is_trained
    assert 'train_mse' in metrics
    assert 'train_r2' in metrics


def test_price_predictor_predict(sample_data):
    """Test price predictor prediction."""
    X, y = sample_data
    model = PricePredictor(model_type='random_forest')

    model.train(X[:150], y[:150])
    predictions = model.predict(X[150:])

    assert len(predictions) == len(X[150:])
    assert not np.isnan(predictions).any()


def test_price_predictor_evaluate(sample_data):
    """Test price predictor evaluation."""
    X, y = sample_data
    model = PricePredictor(model_type='random_forest')

    model.train(X[:150], y[:150])
    metrics = model.evaluate(X[150:], y[150:])

    assert 'test_mse' in metrics
    assert 'test_r2' in metrics
    assert metrics['test_mse'] >= 0


def test_trend_classifier_train(sample_data):
    """Test trend classifier training."""
    X, y = sample_data
    model = TrendClassifier(model_type='random_forest')

    metrics = model.train(X, y)

    assert model.is_trained
    assert 'train_accuracy' in metrics
    assert 0 <= metrics['train_accuracy'] <= 1


def test_trend_classifier_predict(sample_data):
    """Test trend classifier prediction."""
    X, y = sample_data
    model = TrendClassifier(model_type='random_forest')

    model.train(X[:150], y[:150])
    predictions = model.predict(X[150:])

    assert len(predictions) == len(X[150:])
    assert all(p in [0, 1, 2] for p in predictions)


def test_trend_classifier_proba(sample_data):
    """Test trend classifier probability prediction."""
    X, y = sample_data
    model = TrendClassifier(model_type='random_forest')

    model.train(X[:150], y[:150])
    probas = model.predict_proba(X[150:])

    assert probas.shape == (len(X[150:]), 3)
    assert np.allclose(probas.sum(axis=1), 1.0)


def test_model_save_load(sample_data, tmp_path):
    """Test model save and load."""
    X, y = sample_data
    model = PricePredictor(model_type='random_forest')

    model.train(X, y)
    model.save_model(str(tmp_path / 'test_model'))

    # Load model
    new_model = PricePredictor(model_type='random_forest')
    new_model.load_model(str(tmp_path / 'test_model'))

    assert new_model.is_trained
    assert np.allclose(model.predict(X[:10]), new_model.predict(X[:10]))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
