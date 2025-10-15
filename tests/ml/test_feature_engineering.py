"""
Unit tests for feature engineering module.
"""

import pytest
import numpy as np
import pandas as pd
from src.strategies.ml.features import FeatureEngineer, FeatureConfig


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    n = 200

    dates = pd.date_range('2024-01-01', periods=n, freq='1H')
    close = 100 + np.random.randn(n).cumsum()
    high = close + np.random.uniform(0, 2, n)
    low = close - np.random.uniform(0, 2, n)
    open_price = close + np.random.randn(n) * 0.5
    volume = np.random.uniform(100000, 1000000, n)

    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return df


def test_feature_engineer_initialization():
    """Test FeatureEngineer initialization."""
    fe = FeatureEngineer()
    assert fe.config is not None
    assert fe.scaler is not None


def test_engineer_features(sample_data):
    """Test feature engineering on sample data."""
    fe = FeatureEngineer()
    features = fe.engineer_features(sample_data)

    # Check that features were created
    assert len(features) > 0
    assert len(fe.feature_names) > 0

    # Check for expected feature columns
    assert any('sma' in col for col in features.columns)
    assert any('rsi' in col for col in features.columns)
    assert any('returns' in col for col in features.columns)


def test_sma_features(sample_data):
    """Test SMA feature generation."""
    config = FeatureConfig(
        lookback_periods=[5, 10],
        technical_indicators=['sma'],
        statistical_features=[]
    )
    fe = FeatureEngineer(config)
    features = fe.engineer_features(sample_data)

    assert 'sma_5' in features.columns
    assert 'sma_10' in features.columns
    assert 'close_sma_5_ratio' in features.columns


def test_prepare_ml_dataset(sample_data):
    """Test ML dataset preparation."""
    fe = FeatureEngineer()
    features = fe.engineer_features(sample_data)
    X, y = fe.prepare_ml_dataset(features, target_col='next_return')

    assert X.shape[0] == y.shape[0]
    assert X.shape[1] == len(fe.feature_names)
    assert not np.isnan(X).any()
    assert not np.isnan(y).any()


def test_feature_scaling(sample_data):
    """Test feature scaling."""
    fe = FeatureEngineer()
    features = fe.engineer_features(sample_data)
    X, y = fe.prepare_ml_dataset(features, scale_features=True)

    # Check that features are scaled (approximately zero mean, unit variance)
    assert np.abs(X.mean()) < 0.5
    assert 0.5 < X.std() < 1.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
