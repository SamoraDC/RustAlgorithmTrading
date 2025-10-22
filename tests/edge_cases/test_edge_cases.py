"""
Edge case tests for data loading system.

Tests:
- Missing data directory
- No internet connection
- Invalid API credentials
- Partial data availability
- Corrupted files
- Empty files
- Malformed data
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, Mock
import pandas as pd
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting.data_handler import HistoricalDataHandler


class TestMissingDataDirectory:
    """Test handling of missing data directory"""

    def test_missing_directory_created(self, tmp_path):
        """Test that missing directory is created automatically"""
        missing_dir = tmp_path / "nonexistent" / "nested" / "path"

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=missing_dir,
        )

        assert missing_dir.exists()

    def test_no_data_files_in_directory(self, tmp_path):
        """Test loading with empty data directory"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        handler = HistoricalDataHandler(
            symbols=['AAPL', 'MSFT'],
            data_dir=empty_dir,
        )

        # Should not raise error, but have no loaded data
        assert len(handler.symbol_data) == 0


class TestInvalidAPICredentials:
    """Test handling of invalid API credentials"""

    @patch('download_historical_data.StockHistoricalDataClient')
    def test_invalid_credentials_raises_error(self, mock_client):
        """Test that invalid credentials are caught"""
        from download_historical_data import AlpacaDataDownloader, DownloadConfig

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            api_key='invalid_key',
            api_secret='invalid_secret',
        )

        # Mock client to raise auth error
        mock_client.side_effect = Exception("401 Unauthorized")

        with pytest.raises(Exception):
            downloader = AlpacaDataDownloader(config)

    def test_missing_credentials_raises_error(self):
        """Test that missing credentials raise appropriate error"""
        from download_historical_data import AlpacaDataDownloader, DownloadConfig

        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = DownloadConfig(
                symbols=['AAPL'],
                start_date='2024-01-01',
                end_date='2024-12-31',
            )

            with pytest.raises(ValueError, match="credentials not found"):
                downloader = AlpacaDataDownloader(config)


class TestPartialDataAvailability:
    """Test handling of partial data availability"""

    def test_some_symbols_missing(self, tmp_path):
        """Test when only some symbols have data files"""
        data_dir = tmp_path / "partial"
        data_dir.mkdir()

        # Create data for only AAPL
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [99.0] * 10,
            'close': [104.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        # Request AAPL and MSFT, but only AAPL exists
        handler = HistoricalDataHandler(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            data_dir=data_dir,
        )

        # Should load AAPL but skip others
        assert 'AAPL' in handler.symbol_data
        assert 'MSFT' not in handler.symbol_data
        assert 'GOOGL' not in handler.symbol_data

    def test_partial_date_range(self, tmp_path):
        """Test when data only covers part of requested range"""
        data_dir = tmp_path / "partial_range"
        data_dir.mkdir()

        # Create data for Jan 1-10
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [99.0] * 10,
            'close': [104.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        # Request Jan 1 - Jan 31
        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should have only 10 days
        assert len(handler.symbol_data['AAPL']) == 10


class TestCorruptedFiles:
    """Test handling of corrupted/malformed files"""

    def test_corrupted_csv(self, tmp_path):
        """Test loading corrupted CSV file"""
        data_dir = tmp_path / "corrupted"
        data_dir.mkdir()

        # Create invalid CSV
        with open(data_dir / "AAPL.csv", 'w') as f:
            f.write("This is not valid CSV content\n")
            f.write("Random garbage data\n")

        with pytest.raises(Exception):
            handler = HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=data_dir,
            )

    def test_empty_csv(self, tmp_path):
        """Test loading empty CSV file"""
        data_dir = tmp_path / "empty"
        data_dir.mkdir()

        # Create empty CSV
        with open(data_dir / "AAPL.csv", 'w') as f:
            f.write("timestamp,open,high,low,close,volume\n")

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Should handle empty file gracefully
        assert 'AAPL' not in handler.symbol_data or len(handler.symbol_data['AAPL']) == 0

    def test_csv_with_null_values(self, tmp_path):
        """Test CSV with null/NaN values"""
        data_dir = tmp_path / "nulls"
        data_dir.mkdir()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'open': [100.0, None, 102.0, None, 104.0, 105.0, None, 107.0, 108.0, 109.0],
            'high': [105.0] * 10,
            'low': [99.0] * 10,
            'close': [104.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Should load and handle nulls
        assert 'AAPL' in handler.symbol_data

    def test_csv_missing_required_columns(self, tmp_path):
        """Test CSV missing required columns"""
        data_dir = tmp_path / "missing_cols"
        data_dir.mkdir()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'open': [100.0] * 10,
            'close': [104.0] * 10,
            # Missing high, low, volume
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        with pytest.raises(ValueError, match="Missing required columns"):
            handler = HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=data_dir,
            )


class TestMalformedData:
    """Test handling of malformed data"""

    def test_unsorted_timestamps(self, tmp_path):
        """Test data with unsorted timestamps"""
        data_dir = tmp_path / "unsorted"
        data_dir.mkdir()

        # Create data with mixed timestamps
        dates = pd.date_range('2024-01-01', periods=10).tolist()
        dates = [dates[i] for i in [5, 2, 8, 1, 9, 0, 7, 3, 6, 4]]  # Shuffle

        df = pd.DataFrame({
            'timestamp': dates,
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [99.0] * 10,
            'close': [104.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Should sort automatically
        data = handler.symbol_data['AAPL']
        assert data['timestamp'].is_monotonic_increasing

    def test_duplicate_timestamps(self, tmp_path):
        """Test data with duplicate timestamps"""
        data_dir = tmp_path / "duplicates"
        data_dir.mkdir()

        df = pd.DataFrame({
            'timestamp': ['2024-01-01'] * 10,  # All same date
            'open': [100.0 + i for i in range(10)],
            'high': [105.0] * 10,
            'low': [99.0] * 10,
            'close': [104.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Should handle duplicates (may deduplicate)
        assert 'AAPL' in handler.symbol_data

    def test_invalid_price_relationships(self, tmp_path):
        """Test data where high < low or negative prices"""
        data_dir = tmp_path / "invalid_prices"
        data_dir.mkdir()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10),
            'open': [100.0] * 10,
            'high': [99.0] * 10,  # High less than low
            'low': [105.0] * 10,
            'close': [104.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Should load with warnings
        assert 'AAPL' in handler.symbol_data


class TestNetworkIssues:
    """Test handling of network-related issues"""

    @patch('download_historical_data.StockHistoricalDataClient')
    def test_network_timeout(self, mock_client):
        """Test handling of network timeout"""
        from download_historical_data import AlpacaDataDownloader, DownloadConfig

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            api_key='test_key',
            api_secret='test_secret',
            retry_attempts=2,
        )

        # Mock timeout
        mock_instance = Mock()
        mock_instance.get_stock_bars = Mock(side_effect=TimeoutError("Connection timeout"))
        mock_client.return_value = mock_instance

        downloader = AlpacaDataDownloader(config)

        with patch('time.sleep'):  # Skip delays
            result = downloader._fetch_data_with_retry('AAPL')

        assert result is None

    @patch('download_historical_data.StockHistoricalDataClient')
    def test_rate_limit_exceeded(self, mock_client):
        """Test handling of API rate limit"""
        from download_historical_data import AlpacaDataDownloader, DownloadConfig

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            api_key='test_key',
            api_secret='test_secret',
            retry_attempts=2,
        )

        mock_instance = Mock()
        mock_instance.get_stock_bars = Mock(
            side_effect=Exception("429 Rate limit exceeded")
        )
        mock_client.return_value = mock_instance

        downloader = AlpacaDataDownloader(config)

        with patch('time.sleep'):
            result = downloader._fetch_data_with_retry('AAPL')

        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
