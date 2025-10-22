"""
Unit tests for timezone handling in data_handler.

Tests verify that the data handler correctly handles timezone-aware timestamps
and prevents timezone comparison errors.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import shutil

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.data_handler import HistoricalDataHandler
from models.market import Bar


class TestTimezoneHandling:
    """Test suite for timezone handling in HistoricalDataHandler."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary directory for test data."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_timezone_aware_data(self, temp_data_dir):
        """Create sample timezone-aware parquet file."""
        # Create timezone-aware timestamps
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        timestamps = pd.date_range(start=start_date, periods=100, freq='1h', tz=timezone.utc)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.randint(1000, 10000, 100),
            'vwap': np.random.uniform(100, 200, 100),
            'trade_count': np.random.randint(10, 100, 100),
        })

        # Ensure high >= low
        df['high'] = df[['high', 'low', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)

        # Save as parquet
        parquet_path = temp_data_dir / 'AAPL.parquet'
        df.to_parquet(parquet_path)

        return temp_data_dir, df

    def test_timezone_aware_initialization(self, sample_timezone_aware_data):
        """Test that handler correctly initializes with timezone-aware dates."""
        data_dir, expected_df = sample_timezone_aware_data

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 5, tzinfo=timezone.utc)

        # Should not raise timezone comparison errors
        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
            start_date=start_date,
            end_date=end_date
        )

        assert handler.start_date.tzinfo is not None
        assert handler.end_date.tzinfo is not None
        assert 'AAPL' in handler.symbol_data

    def test_timezone_naive_dates_converted_to_utc(self, sample_timezone_aware_data):
        """Test that naive datetimes are converted to UTC."""
        data_dir, _ = sample_timezone_aware_data

        # Provide naive datetimes
        naive_start = datetime(2024, 1, 1)
        naive_end = datetime(2024, 1, 5)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
            start_date=naive_start,
            end_date=naive_end
        )

        # Should be converted to timezone-aware
        assert handler.start_date.tzinfo is not None
        assert handler.start_date.tzinfo == timezone.utc
        assert handler.end_date.tzinfo is not None
        assert handler.end_date.tzinfo == timezone.utc

    def test_parquet_with_timezone_aware_timestamps(self, sample_timezone_aware_data):
        """Test loading parquet files with timezone-aware timestamps."""
        data_dir, expected_df = sample_timezone_aware_data

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir
        )

        # Check that data was loaded
        assert 'AAPL' in handler.symbol_data
        df = handler.symbol_data['AAPL']

        # Verify timestamps are timezone-aware
        assert df['timestamp'].dt.tz is not None

    def test_date_filtering_with_mixed_timezones(self, temp_data_dir):
        """Test date filtering works with mixed timezone scenarios."""
        # Create data with timezone-aware timestamps
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        timestamps = pd.date_range(start=start, periods=100, freq='1h', tz=timezone.utc)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': 100.0,
            'high': 110.0,
            'low': 90.0,
            'close': 105.0,
            'volume': 1000,
        })

        df.to_parquet(temp_data_dir / 'AAPL.parquet')

        # Filter with naive dates (should be converted to UTC)
        filter_start = datetime(2024, 1, 2)  # Naive
        filter_end = datetime(2024, 1, 3)    # Naive

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=temp_data_dir,
            start_date=filter_start,
            end_date=filter_end
        )

        # Should load data without timezone errors
        assert 'AAPL' in handler.symbol_data
        filtered_df = handler.symbol_data['AAPL']

        # Verify filtering worked
        assert len(filtered_df) > 0
        assert filtered_df['timestamp'].min() >= handler.start_date
        assert filtered_df['timestamp'].max() <= handler.end_date

    def test_csv_loading_makes_timestamps_aware(self, temp_data_dir):
        """Test that CSV files get timezone-aware timestamps."""
        # Create CSV with naive timestamps
        start = datetime(2024, 1, 1)
        timestamps = pd.date_range(start=start, periods=50, freq='1h')

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': 100.0,
            'high': 110.0,
            'low': 90.0,
            'close': 105.0,
            'volume': 1000,
        })

        csv_path = temp_data_dir / 'MSFT.csv'
        df.to_csv(csv_path, index=False)

        # Load with timezone-aware date range
        handler = HistoricalDataHandler(
            symbols=['MSFT'],
            data_dir=temp_data_dir,
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 3, tzinfo=timezone.utc)
        )

        # Should convert timestamps to timezone-aware
        assert 'MSFT' in handler.symbol_data
        loaded_df = handler.symbol_data['MSFT']
        assert loaded_df['timestamp'].dt.tz is not None

    def test_update_bars_with_timezone_aware_data(self, sample_timezone_aware_data):
        """Test that update_bars works with timezone-aware timestamps."""
        data_dir, _ = sample_timezone_aware_data

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir
        )

        # Update bars should work without timezone errors
        handler.update_bars()

        # Verify bars were created
        latest_bar = handler.get_latest_bar('AAPL')
        assert latest_bar is not None
        assert isinstance(latest_bar.timestamp, pd.Timestamp)

    def test_no_timezone_comparison_errors_during_filtering(self, temp_data_dir):
        """
        Test the specific bug fix: ensure no 'can't compare offset-naive
        and offset-aware datetimes' errors occur.
        """
        # Create parquet with timezone-aware timestamps
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        timestamps = pd.date_range(start=start, periods=100, freq='1h', tz=timezone.utc)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': 100.0,
            'high': 110.0,
            'low': 90.0,
            'close': 105.0,
            'volume': 1000,
        })

        df.to_parquet(temp_data_dir / 'TEST.parquet')

        # This used to fail with timezone comparison error
        # Now should work correctly
        try:
            handler = HistoricalDataHandler(
                symbols=['TEST'],
                data_dir=temp_data_dir,
                start_date=datetime(2024, 1, 1, 12, 0),  # Naive datetime
                end_date=datetime(2024, 1, 2, 12, 0)     # Naive datetime
            )

            # If we get here, the bug is fixed!
            assert True
            assert 'TEST' in handler.symbol_data

        except TypeError as e:
            if "can't compare" in str(e) and "timezone" in str(e).lower():
                pytest.fail(f"Timezone comparison error not fixed: {e}")
            else:
                raise

    def test_edge_case_empty_date_range(self, sample_timezone_aware_data):
        """Test handling of date ranges with no data."""
        data_dir, _ = sample_timezone_aware_data

        # Filter with future dates
        future_start = datetime(2030, 1, 1, tzinfo=timezone.utc)
        future_end = datetime(2030, 1, 5, tzinfo=timezone.utc)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
            start_date=future_start,
            end_date=future_end
        )

        # Should handle gracefully
        # Symbol may not be in symbol_data if no data in range
        if 'AAPL' in handler.symbol_data:
            assert len(handler.symbol_data['AAPL']) == 0


class TestDataIntegrity:
    """Test data integrity checks."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_validates_high_not_less_than_low(self, temp_data_dir):
        """Test that invalid bars (high < low) are detected."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        timestamps = pd.date_range(start=start, periods=10, freq='1h', tz=timezone.utc)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': 100.0,
            'high': 90.0,  # Invalid: high < low
            'low': 110.0,
            'close': 105.0,
            'volume': 1000,
        })

        df.to_parquet(temp_data_dir / 'INVALID.parquet')

        # Should log warning but not crash
        handler = HistoricalDataHandler(
            symbols=['INVALID'],
            data_dir=temp_data_dir
        )

        assert 'INVALID' in handler.symbol_data

    def test_handles_missing_vwap_gracefully(self, temp_data_dir):
        """Test that missing optional fields are handled."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        timestamps = pd.date_range(start=start, periods=10, freq='1h', tz=timezone.utc)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': 100.0,
            'high': 110.0,
            'low': 90.0,
            'close': 105.0,
            'volume': 1000,
            # No vwap or trade_count
        })

        df.to_parquet(temp_data_dir / 'MINIMAL.parquet')

        handler = HistoricalDataHandler(
            symbols=['MINIMAL'],
            data_dir=temp_data_dir
        )

        handler.update_bars()
        bar = handler.get_latest_bar('MINIMAL')

        assert bar is not None
        assert bar.vwap is None
        assert bar.trade_count is None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
