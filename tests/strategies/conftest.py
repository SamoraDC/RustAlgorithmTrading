"""
Shared fixtures and configuration for strategy tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_ohlcv_data():
    """Basic OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')

    close_prices = 100 + np.cumsum(np.random.normal(0, 1, 100))

    data = pd.DataFrame({
        'open': close_prices * 0.99,
        'high': close_prices * 1.01,
        'low': close_prices * 0.98,
        'close': close_prices,
        'volume': np.random.randint(100000, 500000, 100)
    }, index=dates)

    data.attrs['symbol'] = 'TEST'
    return data


@pytest.fixture
def realistic_market_data():
    """Realistic market data with multiple patterns"""
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='1h')
    n = len(dates)

    # Combine multiple patterns
    base = 150.0
    trend = np.linspace(0, 30, n)
    seasonal = 10 * np.sin(np.linspace(0, 4 * np.pi, n))
    noise = np.random.normal(0, 2, n)

    close = base + trend + seasonal + noise

    data = pd.DataFrame({
        'open': close * (1 + np.random.uniform(-0.005, 0.005, n)),
        'high': close * (1 + np.random.uniform(0, 0.015, n)),
        'low': close * (1 - np.random.uniform(0, 0.015, n)),
        'close': close,
        'volume': np.random.randint(500000, 2000000, n)
    }, index=dates)

    data.attrs['symbol'] = 'AAPL'
    return data


@pytest.fixture
def default_strategy_params():
    """Default momentum strategy parameters"""
    return {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'ema_fast': 12,
        'ema_slow': 26,
        'macd_signal': 9,
        'position_size': 0.15,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.03,
        'min_holding_period': 10,
        'sma_period': 50,
    }


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "parametric: marks parametric optimization tests"
    )
