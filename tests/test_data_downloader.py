"""
Comprehensive test suite for data download and loading process.

Tests cover:
- Alpaca API connection and authentication
- Data format validation (OHLCV)
- CSV and Parquet file creation
- Data integrity checks
- Edge cases and error handling
- Mock tests for offline testing
"""

import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from alpaca.data.timeframe import TimeFrame

# Import modules to test
from src.api.alpaca_client import AlpacaClient
from src.data.fetcher import DataFetcher
from src.data.loader import DataLoader
from src.backtesting.data_handler import HistoricalDataHandler


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("ALPACA_API_KEY", "test_api_key_123")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test_secret_key_456")
    monkeypatch.setenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')

    # Generate realistic OHLCV data
    np.random.seed(42)
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)

    data = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.uniform(-1, 1, 100),
        'high': close_prices + np.random.uniform(0, 3, 100),
        'low': close_prices - np.random.uniform(0, 3, 100),
        'close': close_prices,
        'volume': np.random.randint(1000000, 10000000, 100),
        'vwap': close_prices + np.random.uniform(-0.5, 0.5, 100),
        'trade_count': np.random.randint(1000, 5000, 100)
    })

    # Ensure OHLC relationships are valid
    data['high'] = data[['open', 'high', 'low', 'close']].max(axis=1)
    data['low'] = data[['open', 'high', 'low', 'close']].min(axis=1)

    return data


@pytest.fixture
def invalid_ohlcv_data():
    """Generate invalid OHLCV data for testing error handling."""
    dates = pd.date_range(start='2024-01-01', periods=10, freq='D')

    return pd.DataFrame({
        'timestamp': dates,
        'open': [100, 101, -5, 103, 104, 105, 106, 107, 108, 109],  # Negative price
        'high': [102, 99, 107, 109, 110, 111, 112, 113, 114, 115],  # High < Open
        'low': [98, 97, 96, 95, 94, 93, 92, 91, 90, 89],
        'close': [101, 100, 105, 108, 109, 110, 111, 112, 113, 114],
        'volume': [1000000, 1100000, -500000, 1300000, 1400000, 1500000, 1600000, 1700000, 1800000, 1900000],  # Negative volume
    })


# ============================================================================
# ALPACA CLIENT TESTS
# ============================================================================

class TestAlpacaClient:
    """Test suite for AlpacaClient connection and authentication."""

    def test_client_initialization_with_env_vars(self, mock_env_vars):
        """Test client initializes correctly with environment variables."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient'):

            client = AlpacaClient(paper=True)

            assert client.api_key == "test_api_key_123"
            assert client.secret_key == "test_secret_key_456"
            assert client.base_url == "https://paper-api.alpaca.markets"

    def test_client_initialization_with_explicit_credentials(self):
        """Test client initializes with explicit credentials."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient'):

            client = AlpacaClient(
                api_key="explicit_key",
                secret_key="explicit_secret",
                paper=True
            )

            assert client.api_key == "explicit_key"
            assert client.secret_key == "explicit_secret"

    def test_client_initialization_without_credentials(self, monkeypatch):
        """Test client raises error when credentials are missing."""
        monkeypatch.delenv("ALPACA_API_KEY", raising=False)
        monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

        with pytest.raises(ValueError, match="Alpaca API credentials not found"):
            AlpacaClient()

    def test_get_account(self, mock_env_vars):
        """Test fetching account information."""
        with patch('src.api.alpaca_client.TradingClient') as mock_trading, \
             patch('src.api.alpaca_client.StockHistoricalDataClient'):

            # Mock account response
            mock_account = Mock()
            mock_account.cash = "100000"
            mock_account.portfolio_value = "150000"
            mock_account.buying_power = "200000"
            mock_account.equity = "150000"
            mock_account.status = "ACTIVE"

            mock_trading.return_value.get_account.return_value = mock_account

            client = AlpacaClient(paper=True)
            account_info = client.get_account()

            assert account_info["cash"] == 100000.0
            assert account_info["portfolio_value"] == 150000.0
            assert account_info["status"] == "ACTIVE"

    def test_get_historical_bars(self, mock_env_vars, sample_ohlcv_data):
        """Test fetching historical bars."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient') as mock_data_client:

            # Mock bars response
            mock_bars = Mock()
            mock_bars.df = sample_ohlcv_data.set_index('timestamp')

            mock_data_client.return_value.get_stock_bars.return_value = mock_bars

            client = AlpacaClient(paper=True)
            start = datetime(2024, 1, 1)
            end = datetime(2024, 4, 10)

            df = client.get_historical_bars("AAPL", start, end, TimeFrame.Day)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 100
            assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])


# ============================================================================
# DATA FETCHER TESTS
# ============================================================================

class TestDataFetcher:
    """Test suite for DataFetcher functionality."""

    def test_fetch_multiple_symbols(self, mock_env_vars, sample_ohlcv_data):
        """Test fetching data for multiple symbols."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient') as mock_data_client:

            # Mock bars response
            mock_bars = Mock()
            mock_bars.df = sample_ohlcv_data.set_index('timestamp')
            mock_data_client.return_value.get_stock_bars.return_value = mock_bars

            client = AlpacaClient(paper=True)
            fetcher = DataFetcher(client)

            symbols = ["AAPL", "MSFT", "GOOGL"]
            start = datetime(2024, 1, 1)
            end = datetime(2024, 4, 10)

            data = fetcher.fetch_multiple_symbols(symbols, start, end)

            assert len(data) == 3
            assert all(symbol in data for symbol in symbols)
            assert all(isinstance(df, pd.DataFrame) for df in data.values())

    def test_fetch_last_n_days(self, mock_env_vars, sample_ohlcv_data):
        """Test fetching last N days of data."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient') as mock_data_client:

            mock_bars = Mock()
            mock_bars.df = sample_ohlcv_data.set_index('timestamp')
            mock_data_client.return_value.get_stock_bars.return_value = mock_bars

            client = AlpacaClient(paper=True)
            fetcher = DataFetcher(client)

            df = fetcher.fetch_last_n_days("AAPL", days=30)

            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0

    def test_get_latest_price(self, mock_env_vars, sample_ohlcv_data):
        """Test getting latest price for a symbol."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient') as mock_data_client:

            mock_bars = Mock()
            mock_bars.df = sample_ohlcv_data.set_index('timestamp')
            mock_data_client.return_value.get_stock_bars.return_value = mock_bars

            client = AlpacaClient(paper=True)
            fetcher = DataFetcher(client)

            price = fetcher.get_latest_price("AAPL")

            assert isinstance(price, float)
            assert price > 0


# ============================================================================
# DATA LOADER TESTS
# ============================================================================

class TestDataLoader:
    """Test suite for DataLoader file operations."""

    def test_save_and_load_csv(self, temp_data_dir, sample_ohlcv_data):
        """Test saving and loading CSV files."""
        loader = DataLoader(data_dir=temp_data_dir, cache_enabled=False)

        # Save data
        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        # Verify file exists
        csv_path = temp_data_dir / "AAPL.csv"
        assert csv_path.exists()

        # Load data
        loaded_df = loader.load_ohlcv("AAPL", source='csv')

        assert len(loaded_df) == len(sample_ohlcv_data)
        assert all(col in loaded_df.columns for col in ['open', 'high', 'low', 'close', 'volume'])

    def test_save_and_load_parquet(self, temp_data_dir, sample_ohlcv_data):
        """Test saving and loading Parquet files."""
        loader = DataLoader(data_dir=temp_data_dir, cache_enabled=False)

        # Save data
        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='parquet')

        # Verify file exists
        parquet_path = temp_data_dir / "AAPL.parquet"
        assert parquet_path.exists()

        # Load data
        loaded_df = loader.load_ohlcv("AAPL", source='parquet')

        assert len(loaded_df) == len(sample_ohlcv_data)

    def test_cache_functionality(self, temp_data_dir, sample_ohlcv_data):
        """Test data caching mechanism."""
        loader = DataLoader(data_dir=temp_data_dir, cache_enabled=True)

        # Save and load data
        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        # First load (from file)
        df1 = loader.load_ohlcv("AAPL", source='csv')

        # Second load (from cache)
        df2 = loader.load_ohlcv("AAPL", source='csv')

        assert df1.equals(df2)
        assert len(loader.cache) > 0

    def test_date_range_filtering(self, temp_data_dir, sample_ohlcv_data):
        """Test filtering data by date range."""
        loader = DataLoader(data_dir=temp_data_dir, cache_enabled=False)

        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        # Load with date range
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 2, 15)

        df = loader.load_ohlcv(
            "AAPL",
            start_date=start_date,
            end_date=end_date,
            source='csv'
        )

        assert df.index.min() >= start_date
        assert df.index.max() <= end_date

    def test_load_multiple_symbols(self, temp_data_dir, sample_ohlcv_data):
        """Test loading multiple symbols."""
        loader = DataLoader(data_dir=temp_data_dir, cache_enabled=False)

        # Save data for multiple symbols
        symbols = ["AAPL", "MSFT", "GOOGL"]
        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')

        for symbol in symbols:
            loader.save_data(symbol, sample_ohlcv_data_indexed, format='csv')

        # Load all symbols
        data = loader.load_multiple(symbols)

        assert len(data) == 3
        assert all(symbol in data for symbol in symbols)


# ============================================================================
# DATA VALIDATION TESTS
# ============================================================================

class TestDataValidation:
    """Test suite for data integrity and validation."""

    def test_valid_ohlc_relationships(self, temp_data_dir, sample_ohlcv_data):
        """Test that OHLC relationships are valid (high >= open/close, low <= open/close)."""
        loader = DataLoader(data_dir=temp_data_dir)

        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        df = loader.load_ohlcv("AAPL", source='csv')

        # Check OHLC relationships
        assert (df['high'] >= df['open']).all() or (df['high'] >= df['close']).all()
        assert (df['low'] <= df['open']).all() or (df['low'] <= df['close']).all()
        assert (df['high'] >= df['low']).all()

    def test_no_negative_prices(self, temp_data_dir, sample_ohlcv_data):
        """Test that all prices are positive."""
        loader = DataLoader(data_dir=temp_data_dir)

        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        df = loader.load_ohlcv("AAPL", source='csv')

        # Check no negative prices
        assert (df['open'] > 0).all()
        assert (df['high'] > 0).all()
        assert (df['low'] > 0).all()
        assert (df['close'] > 0).all()

    def test_no_negative_volume(self, temp_data_dir, sample_ohlcv_data):
        """Test that volume is non-negative."""
        loader = DataLoader(data_dir=temp_data_dir)

        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        df = loader.load_ohlcv("AAPL", source='csv')

        assert (df['volume'] >= 0).all()

    def test_no_duplicate_timestamps(self, temp_data_dir, sample_ohlcv_data):
        """Test that there are no duplicate timestamps."""
        loader = DataLoader(data_dir=temp_data_dir)

        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        df = loader.load_ohlcv("AAPL", source='csv')

        assert not df.index.duplicated().any()

    def test_sorted_by_timestamp(self, temp_data_dir, sample_ohlcv_data):
        """Test that data is sorted by timestamp."""
        loader = DataLoader(data_dir=temp_data_dir)

        # Shuffle data before saving
        shuffled_data = sample_ohlcv_data.sample(frac=1).set_index('timestamp')
        loader.save_data("AAPL", shuffled_data, format='csv')

        df = loader.load_ohlcv("AAPL", source='csv')

        # Check if sorted
        assert df.index.is_monotonic_increasing


# ============================================================================
# HISTORICAL DATA HANDLER TESTS
# ============================================================================

class TestHistoricalDataHandler:
    """Test suite for HistoricalDataHandler backtesting functionality."""

    def test_handler_initialization(self, temp_data_dir, sample_ohlcv_data):
        """Test handler initializes correctly."""
        # Save test data
        sample_ohlcv_data.to_csv(temp_data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=["AAPL"],
            data_dir=temp_data_dir,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 4, 10)
        )

        assert "AAPL" in handler.symbol_data
        assert len(handler.symbol_data["AAPL"]) > 0

    def test_update_bars(self, temp_data_dir, sample_ohlcv_data):
        """Test bar updates during backtest."""
        sample_ohlcv_data.to_csv(temp_data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=["AAPL"],
            data_dir=temp_data_dir
        )

        # Update bars
        handler.update_bars()

        assert handler.bar_index == 1
        assert len(handler.latest_bars["AAPL"]) > 0

    def test_get_latest_bar(self, temp_data_dir, sample_ohlcv_data):
        """Test retrieving latest bar."""
        sample_ohlcv_data.to_csv(temp_data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=["AAPL"],
            data_dir=temp_data_dir
        )

        handler.update_bars()
        bar = handler.get_latest_bar("AAPL")

        assert bar is not None
        assert bar.symbol == "AAPL"
        assert hasattr(bar, 'open')
        assert hasattr(bar, 'close')

    def test_get_latest_bars_multiple(self, temp_data_dir, sample_ohlcv_data):
        """Test retrieving multiple latest bars."""
        sample_ohlcv_data.to_csv(temp_data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=["AAPL"],
            data_dir=temp_data_dir
        )

        # Update bars 5 times
        for _ in range(5):
            handler.update_bars()

        bars = handler.get_latest_bars("AAPL", n=3)

        assert len(bars) == 3
        assert all(bar.symbol == "AAPL" for bar in bars)

    def test_get_latest_bar_value(self, temp_data_dir, sample_ohlcv_data):
        """Test retrieving specific field value from latest bar."""
        sample_ohlcv_data.to_csv(temp_data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=["AAPL"],
            data_dir=temp_data_dir
        )

        handler.update_bars()
        close_price = handler.get_latest_bar_value("AAPL", "close")

        assert close_price is not None
        assert isinstance(close_price, (int, float))
        assert close_price > 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling and edge cases."""

    def test_missing_data_file(self, temp_data_dir):
        """Test handling of missing data files."""
        loader = DataLoader(data_dir=temp_data_dir)

        with pytest.raises(FileNotFoundError):
            loader.load_ohlcv("NONEXISTENT", source='csv')

    def test_invalid_file_format(self, temp_data_dir):
        """Test handling of invalid file formats."""
        # Create invalid CSV file
        invalid_csv = temp_data_dir / "INVALID.csv"
        invalid_csv.write_text("not,valid,csv,data\n1,2,3,4")

        loader = DataLoader(data_dir=temp_data_dir)

        with pytest.raises(Exception):
            loader.load_ohlcv("INVALID", source='csv')

    def test_missing_required_columns(self, temp_data_dir):
        """Test handling of missing required columns."""
        # Create CSV with missing columns
        incomplete_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'open': [100] * 10,
            'close': [101] * 10,
            # Missing: high, low, volume
        })
        incomplete_data.to_csv(temp_data_dir / "INCOMPLETE.csv", index=False)

        loader = DataLoader(data_dir=temp_data_dir)

        with pytest.raises(ValueError, match="Missing required columns"):
            loader.load_ohlcv("INCOMPLETE", source='csv')

    def test_empty_symbol_list(self, temp_data_dir):
        """Test handling of empty symbol list."""
        with pytest.raises(ValueError, match="symbols list cannot be empty"):
            HistoricalDataHandler(
                symbols=[],
                data_dir=temp_data_dir
            )

    def test_invalid_date_range(self, temp_data_dir):
        """Test handling of invalid date range."""
        with pytest.raises(ValueError, match="start_date .* must be before end_date"):
            HistoricalDataHandler(
                symbols=["AAPL"],
                data_dir=temp_data_dir,
                start_date=datetime(2024, 12, 31),
                end_date=datetime(2024, 1, 1)
            )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete data pipeline."""

    def test_full_download_save_load_pipeline(self, mock_env_vars, temp_data_dir, sample_ohlcv_data):
        """Test complete pipeline: fetch -> save -> load."""
        with patch('src.api.alpaca_client.TradingClient'), \
             patch('src.api.alpaca_client.StockHistoricalDataClient') as mock_data_client:

            # Mock API response
            mock_bars = Mock()
            mock_bars.df = sample_ohlcv_data.set_index('timestamp')
            mock_data_client.return_value.get_stock_bars.return_value = mock_bars

            # 1. Fetch data
            client = AlpacaClient(paper=True)
            fetcher = DataFetcher(client)

            start = datetime(2024, 1, 1)
            end = datetime(2024, 4, 10)
            df = fetcher.fetch_last_n_days("AAPL", days=100)

            # 2. Save data
            loader = DataLoader(data_dir=temp_data_dir)
            loader.save_data("AAPL", df, format='parquet')

            # 3. Load data
            loaded_df = loader.load_ohlcv("AAPL", source='parquet')

            # 4. Verify data integrity
            assert len(loaded_df) == len(sample_ohlcv_data)
            assert all(col in loaded_df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
            assert (loaded_df['high'] >= loaded_df['low']).all()

    def test_backtest_with_real_data_flow(self, temp_data_dir, sample_ohlcv_data):
        """Test backtesting with realistic data flow."""
        # Save data
        sample_ohlcv_data.to_csv(temp_data_dir / "AAPL.csv", index=False)

        # Initialize handler
        handler = HistoricalDataHandler(
            symbols=["AAPL"],
            data_dir=temp_data_dir,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1)
        )

        # Simulate backtest loop
        bar_count = 0
        while handler.continue_backtest and bar_count < 10:
            handler.update_bars()
            bar = handler.get_latest_bar("AAPL")

            if bar:
                assert bar.close > 0
                assert bar.volume >= 0
                bar_count += 1

        assert bar_count > 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test suite for performance benchmarks."""

    def test_large_dataset_loading(self, temp_data_dir):
        """Test loading large datasets efficiently."""
        # Generate large dataset (1 year of minute data)
        large_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=365*390, freq='1min'),
            'open': np.random.uniform(100, 200, 365*390),
            'high': np.random.uniform(100, 200, 365*390),
            'low': np.random.uniform(100, 200, 365*390),
            'close': np.random.uniform(100, 200, 365*390),
            'volume': np.random.randint(1000, 100000, 365*390),
        })

        large_data.set_index('timestamp').to_parquet(temp_data_dir / "LARGE.parquet")

        loader = DataLoader(data_dir=temp_data_dir)

        import time
        start_time = time.time()
        df = loader.load_ohlcv("LARGE", source='parquet')
        load_time = time.time() - start_time

        # Should load in reasonable time (< 5 seconds)
        assert load_time < 5.0
        assert len(df) > 100000

    def test_cache_performance_improvement(self, temp_data_dir, sample_ohlcv_data):
        """Test that caching improves load performance."""
        loader = DataLoader(data_dir=temp_data_dir, cache_enabled=True)

        sample_ohlcv_data_indexed = sample_ohlcv_data.set_index('timestamp')
        loader.save_data("AAPL", sample_ohlcv_data_indexed, format='csv')

        import time

        # First load (from file)
        start_time = time.time()
        df1 = loader.load_ohlcv("AAPL", source='csv')
        first_load_time = time.time() - start_time

        # Second load (from cache)
        start_time = time.time()
        df2 = loader.load_ohlcv("AAPL", source='csv')
        cache_load_time = time.time() - start_time

        # Cache should be significantly faster
        assert cache_load_time < first_load_time


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
