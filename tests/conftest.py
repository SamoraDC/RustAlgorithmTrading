"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================================
# FIXTURES: Test Data Generation
# ============================================================================

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for backtesting."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='1h')
    np.random.seed(42)

    # Generate realistic price movements
    base_price = 100.0
    returns = np.random.normal(0.0001, 0.02, len(dates))
    prices = base_price * np.exp(np.cumsum(returns))

    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.001, 0.001, len(dates))),
        'high': prices * (1 + np.random.uniform(0, 0.005, len(dates))),
        'low': prices * (1 - np.random.uniform(0, 0.005, len(dates))),
        'close': prices,
        'volume': np.random.uniform(1000, 10000, len(dates))
    })

    return data


@pytest.fixture
def sample_orderbook_snapshot():
    """Generate sample order book snapshot."""
    return {
        'timestamp': datetime.now().isoformat(),
        'bids': [
            {'price': 100.0, 'size': 10.5},
            {'price': 99.9, 'size': 15.2},
            {'price': 99.8, 'size': 20.0},
            {'price': 99.7, 'size': 5.5},
            {'price': 99.6, 'size': 8.3}
        ],
        'asks': [
            {'price': 100.1, 'size': 12.0},
            {'price': 100.2, 'size': 18.5},
            {'price': 100.3, 'size': 25.0},
            {'price': 100.4, 'size': 7.2},
            {'price': 100.5, 'size': 10.0}
        ]
    }


@pytest.fixture
def sample_trades():
    """Generate sample trade history."""
    return pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=100, freq='1min'),
        'price': np.random.uniform(99, 101, 100),
        'size': np.random.uniform(0.1, 10, 100),
        'side': np.random.choice(['buy', 'sell'], 100)
    })


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


# ============================================================================
# FIXTURES: Strategy Components
# ============================================================================

@pytest.fixture
def simple_momentum_strategy():
    """Simple momentum strategy for testing."""
    class MomentumStrategy:
        def __init__(self, lookback=20):
            self.lookback = lookback

        def generate_signals(self, data):
            """Generate buy/sell signals based on momentum."""
            returns = data['close'].pct_change(self.lookback)
            signals = pd.DataFrame(index=data.index)
            signals['signal'] = 0
            signals.loc[returns > 0.05, 'signal'] = 1  # Buy
            signals.loc[returns < -0.05, 'signal'] = -1  # Sell
            return signals

    return MomentumStrategy()


@pytest.fixture
def simple_mean_reversion_strategy():
    """Simple mean reversion strategy for testing."""
    class MeanReversionStrategy:
        def __init__(self, window=20, num_std=2):
            self.window = window
            self.num_std = num_std

        def generate_signals(self, data):
            """Generate signals based on mean reversion."""
            rolling_mean = data['close'].rolling(window=self.window).mean()
            rolling_std = data['close'].rolling(window=self.window).std()

            upper_band = rolling_mean + (self.num_std * rolling_std)
            lower_band = rolling_mean - (self.num_std * rolling_std)

            signals = pd.DataFrame(index=data.index)
            signals['signal'] = 0
            signals.loc[data['close'] < lower_band, 'signal'] = 1  # Buy
            signals.loc[data['close'] > upper_band, 'signal'] = -1  # Sell

            return signals

    return MeanReversionStrategy()


# ============================================================================
# FIXTURES: Performance Metrics
# ============================================================================

@pytest.fixture
def sample_returns():
    """Generate sample return series."""
    np.random.seed(42)
    return pd.Series(
        np.random.normal(0.001, 0.02, 252),
        index=pd.date_range('2023-01-01', periods=252, freq='D')
    )


# ============================================================================
# MARKERS AND CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for full workflows"
    )
    config.addinivalue_line(
        "markers", "property: Property-based tests using hypothesis"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and benchmark tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time to run"
    )


# ============================================================================
# HOOKS
# ============================================================================

@pytest.fixture(autouse=True)
def reset_random_seeds():
    """Reset random seeds before each test for reproducibility."""
    np.random.seed(42)
    import random
    random.seed(42)
