#!/usr/bin/env python3
"""
Test suite for data download functionality.

Tests:
- Data download script execution
- Data format validation
- Auto-download fallback
- Error handling
"""

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.download_market_data import MarketDataDownloader


class TestMarketDataDownloader:
    """Test market data download functionality"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory"""
        data_dir = tmp_path / "data" / "historical"
        data_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def downloader(self, temp_data_dir):
        """Create downloader instance"""
        # Skip if no API credentials
        if not os.getenv('ALPACA_API_KEY'):
            pytest.skip("No Alpaca API credentials available")

        return MarketDataDownloader(
            symbols=['AAPL'],
            data_dir=temp_data_dir.parent,
            days_back=30  # Short range for testing
        )

    def test_date_range_calculation(self, downloader):
        """Test date range calculation"""
        start, end = downloader._get_date_range()

        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert start < end
        assert (end - start).days <= downloader.days_back + 7  # Account for weekends

    def test_data_validation_valid(self, downloader):
        """Test data validation with valid data"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [100.0],
            'high': [105.0],
            'low': [99.0],
            'close': [102.0],
            'volume': [1000000]
        })

        assert downloader._validate_data(df, 'AAPL')

    def test_data_validation_invalid_prices(self, downloader):
        """Test data validation with invalid prices"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [100.0],
            'high': [95.0],  # Invalid: high < low
            'low': [99.0],
            'close': [102.0],
            'volume': [1000000]
        })

        assert not downloader._validate_data(df, 'AAPL')

    def test_data_validation_negative_prices(self, downloader):
        """Test data validation with negative prices"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [-100.0],  # Invalid: negative
            'high': [105.0],
            'low': [99.0],
            'close': [102.0],
            'volume': [1000000]
        })

        assert not downloader._validate_data(df, 'AAPL')

    def test_data_validation_missing_columns(self, downloader):
        """Test data validation with missing columns"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [100.0]
            # Missing required columns
        })

        assert not downloader._validate_data(df, 'AAPL')

    def test_save_data_creates_files(self, downloader, temp_data_dir):
        """Test that data is saved in both formats"""
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'symbol': ['AAPL'],
            'open': [100.0],
            'high': [105.0],
            'low': [99.0],
            'close': [102.0],
            'volume': [1000000],
            'vwap': [101.0],
            'trade_count': [100]
        })

        success = downloader._save_data(df, 'AAPL')

        assert success
        assert (temp_data_dir / 'AAPL.csv').exists()
        assert (temp_data_dir / 'AAPL.parquet').exists()

    @pytest.mark.integration
    def test_download_symbol_integration(self, downloader):
        """Integration test for downloading a symbol"""
        success = downloader.download_symbol('AAPL')

        # Should succeed or fail gracefully
        assert isinstance(success, bool)

        if success:
            # Verify files were created
            assert (downloader.data_dir / 'historical' / 'AAPL.csv').exists()
            assert (downloader.data_dir / 'historical' / 'AAPL.parquet').exists()

            # Verify data can be loaded
            df = pd.read_parquet(downloader.data_dir / 'historical' / 'AAPL.parquet')
            assert len(df) > 0
            assert all(col in df.columns for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume'])


class TestDataHandler:
    """Test data handler auto-download functionality"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory"""
        data_dir = tmp_path / "data" / "historical"
        data_dir.mkdir(parents=True)
        return data_dir

    def test_check_data_availability_missing(self, temp_data_dir):
        """Test data availability check with missing files"""
        from backtesting.data_handler import HistoricalDataHandler

        handler = HistoricalDataHandler.__new__(HistoricalDataHandler)
        handler.data_dir = temp_data_dir
        handler.symbols = ['AAPL']

        assert not handler._check_data_availability('AAPL')

    def test_check_data_availability_exists(self, temp_data_dir):
        """Test data availability check with existing files"""
        from backtesting.data_handler import HistoricalDataHandler

        # Create dummy data file
        df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [100.0],
            'high': [105.0],
            'low': [99.0],
            'close': [102.0],
            'volume': [1000000]
        })
        df.to_parquet(temp_data_dir / 'AAPL.parquet')

        handler = HistoricalDataHandler.__new__(HistoricalDataHandler)
        handler.data_dir = temp_data_dir
        handler.symbols = ['AAPL']

        assert handler._check_data_availability('AAPL')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
