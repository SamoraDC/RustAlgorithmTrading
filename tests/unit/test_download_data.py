"""
Unit tests for data download script.

Tests:
- Configuration loading and validation
- Data fetching with retry logic
- CSV/Parquet file saving
- Data validation
- Error handling
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from download_historical_data import (
    DownloadConfig,
    AlpacaDataDownloader,
)


class TestDownloadConfig:
    """Test DownloadConfig dataclass"""

    def test_config_creation(self):
        """Test config creation with valid parameters"""
        config = DownloadConfig(
            symbols=['AAPL', 'MSFT'],
            start_date='2024-01-01',
            end_date='2024-12-31',
        )
        assert config.symbols == ['AAPL', 'MSFT']
        assert config.start_date == '2024-01-01'
        assert config.end_date == '2024-12-31'
        assert config.timeframe == '1Day'  # default

    def test_config_from_dict(self):
        """Test loading config from dictionary"""
        config_dict = {
            'symbols': ['AAPL'],
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'timeframe': '1Hour',
        }
        config = DownloadConfig.from_dict(config_dict)
        assert config.symbols == ['AAPL']
        assert config.timeframe == '1Hour'

    def test_config_defaults(self):
        """Test default configuration values"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
        )
        assert config.save_csv is True
        assert config.save_parquet is True
        assert config.retry_attempts == 3
        assert config.feed == 'iex'


class TestAlpacaDataDownloader:
    """Test AlpacaDataDownloader class"""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration"""
        return DownloadConfig(
            symbols=['AAPL', 'MSFT'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            output_dir=str(tmp_path),
            api_key='test_key',
            api_secret='test_secret',
        )

    @pytest.fixture
    def downloader(self, mock_config):
        """Create downloader instance with mocked API"""
        with patch('download_historical_data.StockHistoricalDataClient'):
            return AlpacaDataDownloader(mock_config)

    def test_initialization(self, downloader, tmp_path):
        """Test downloader initialization"""
        assert downloader.config is not None
        assert len(downloader.config.symbols) == 2
        assert downloader.output_dir.exists()

    def test_directory_creation(self, downloader):
        """Test output directories are created"""
        assert downloader.csv_dir.exists()
        assert downloader.parquet_dir.exists()

    def test_parse_timeframe_valid(self, downloader):
        """Test parsing valid timeframe strings"""
        from alpaca.data.timeframe import TimeFrame

        assert downloader._parse_timeframe('1Day') == TimeFrame.Day
        assert downloader._parse_timeframe('1Hour') == TimeFrame.Hour
        assert downloader._parse_timeframe('1Min') == TimeFrame.Minute

    def test_parse_timeframe_invalid(self, downloader):
        """Test parsing invalid timeframe defaults to 1Day"""
        from alpaca.data.timeframe import TimeFrame

        result = downloader._parse_timeframe('InvalidTimeframe')
        assert result == TimeFrame.Day

    def test_validate_dataframe_valid(self, downloader):
        """Test validation of valid DataFrame"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })

        assert downloader._validate_dataframe(df, 'AAPL') is True

    def test_validate_dataframe_empty(self, downloader):
        """Test validation of empty DataFrame"""
        df = pd.DataFrame()
        assert downloader._validate_dataframe(df, 'AAPL') is False

    def test_validate_dataframe_missing_columns(self, downloader):
        """Test validation with missing required columns"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, 102, 103, 104],
            # Missing high, low, close, volume
        })

        assert downloader._validate_dataframe(df, 'AAPL') is False

    def test_validate_dataframe_invalid_prices(self, downloader):
        """Test validation with invalid price data"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, -102, 103, 104],  # Negative price
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })

        assert downloader._validate_dataframe(df, 'AAPL') is False

    def test_validate_dataframe_high_low_mismatch(self, downloader):
        """Test validation where high < low"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, 102, 103, 104],
            'high': [99, 100, 101, 102, 103],  # Lower than low
            'low': [105, 106, 107, 108, 109],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })

        assert downloader._validate_dataframe(df, 'AAPL') is False

    def test_save_csv(self, downloader):
        """Test saving DataFrame to CSV"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'symbol': ['AAPL'] * 5,
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })

        result = downloader._save_csv(df, 'AAPL')
        assert result is True

        # Verify file exists
        csv_files = list(downloader.csv_dir.glob('AAPL_*.csv'))
        assert len(csv_files) > 0

    def test_save_parquet(self, downloader):
        """Test saving DataFrame to Parquet"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'symbol': ['AAPL'] * 5,
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })

        result = downloader._save_parquet(df, 'AAPL')
        assert result is True

        # Verify file exists
        parquet_files = list(downloader.parquet_dir.glob('AAPL_*.parquet'))
        assert len(parquet_files) > 0

    def test_statistics_tracking(self, downloader):
        """Test that statistics are tracked correctly"""
        assert downloader.stats['total_symbols'] == 2
        assert downloader.stats['successful_downloads'] == 0
        assert downloader.stats['failed_downloads'] == 0


class TestDataFetchingWithRetry:
    """Test data fetching with retry logic"""

    @pytest.fixture
    def downloader(self, tmp_path):
        """Create downloader with mocked client"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            output_dir=str(tmp_path),
            api_key='test_key',
            api_secret='test_secret',
            retry_attempts=3,
            retry_delay=1,
        )

        with patch('download_historical_data.StockHistoricalDataClient'):
            return AlpacaDataDownloader(config)

    def test_fetch_success_first_attempt(self, downloader):
        """Test successful data fetch on first attempt"""
        # Mock successful API response
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })
        mock_bars.__contains__ = lambda self, x: True

        downloader.client.get_stock_bars = Mock(return_value=mock_bars)

        result = downloader._fetch_data_with_retry('AAPL')

        assert result is not None
        assert len(result) == 5
        assert 'symbol' in result.columns
        assert result['symbol'].iloc[0] == 'AAPL'

    def test_fetch_retry_on_failure(self, downloader):
        """Test retry logic on API failure"""
        # Mock API to fail twice then succeed
        call_count = [0]

        def mock_get_bars(request):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("API Error")

            mock_bars = MagicMock()
            mock_bars.df = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=5),
                'open': [100, 101, 102, 103, 104],
                'high': [105, 106, 107, 108, 109],
                'low': [99, 100, 101, 102, 103],
                'close': [104, 105, 106, 107, 108],
                'volume': [1000, 2000, 3000, 4000, 5000],
            })
            mock_bars.__contains__ = lambda self, x: True
            return mock_bars

        downloader.client.get_stock_bars = Mock(side_effect=mock_get_bars)

        with patch('time.sleep'):  # Skip actual sleep
            result = downloader._fetch_data_with_retry('AAPL')

        assert result is not None
        assert call_count[0] == 3

    def test_fetch_max_retries_exceeded(self, downloader):
        """Test failure after max retries"""
        # Mock API to always fail
        downloader.client.get_stock_bars = Mock(side_effect=Exception("API Error"))

        with patch('time.sleep'):
            result = downloader._fetch_data_with_retry('AAPL')

        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
