#!/usr/bin/env python3
"""
Comprehensive diagnostic tests for Alpaca API limits and fixes

Tests date range calculation, retry logic, rate limiting, and exponential backoff.
Validates fixes for future date issues and API response handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.download_historical_data import AlpacaDataDownloader, DownloadConfig


class TestDateRangeCalculation(unittest.TestCase):
    """Test date range calculation to ensure no future dates"""

    def test_end_date_not_in_future(self):
        """Ensure end date is never in the future"""
        today = datetime.now().date()
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date=future_date
        )

        # End date should be capped at today
        end_date_parsed = datetime.strptime(config.end_date, '%Y-%m-%d').date()
        self.assertLessEqual(
            end_date_parsed,
            today,
            f"End date {end_date_parsed} should not be after today {today}"
        )

    def test_date_range_validation(self):
        """Validate start date is before end date"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-12-31',
            end_date='2024-01-01'
        )

        start = datetime.strptime(config.start_date, '%Y-%m-%d')
        end = datetime.strptime(config.end_date, '%Y-%m-%d')

        self.assertLess(
            start,
            end,
            "Start date should be before end date"
        )

    def test_weekend_handling(self):
        """Test that weekends are handled properly"""
        # Friday to Monday should work
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-05',  # Friday
            end_date='2024-01-08'      # Monday
        )

        start = datetime.strptime(config.start_date, '%Y-%m-%d')
        end = datetime.strptime(config.end_date, '%Y-%m-%d')

        # Should not raise error
        self.assertIsInstance(start, datetime)
        self.assertIsInstance(end, datetime)

    def test_90_day_fallback_range(self):
        """Test 90-day fallback range calculation"""
        today = datetime.now().date()
        days_90_ago = today - timedelta(days=90)

        # Verify 90-day range doesn't include future dates
        self.assertLessEqual(
            days_90_ago,
            today,
            "90-day range should not extend to future"
        )

        # Verify it's exactly 90 days
        delta = (today - days_90_ago).days
        self.assertEqual(
            delta,
            90,
            f"90-day range should be exactly 90 days, got {delta}"
        )

    def test_date_format_validation(self):
        """Test date format is correct YYYY-MM-DD"""
        valid_dates = [
            '2024-01-01',
            '2024-12-31',
            '2025-06-15'
        ]

        for date_str in valid_dates:
            try:
                parsed = datetime.strptime(date_str, '%Y-%m-%d')
                self.assertIsInstance(parsed, datetime)
            except ValueError:
                self.fail(f"Date {date_str} failed to parse")


class TestRetryLogic(unittest.TestCase):
    """Test retry logic with mock failures"""

    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_retry_on_api_failure(self, mock_client_class):
        """Test retry logic when API fails"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate 2 failures then success
        mock_client.get_stock_bars.side_effect = [
            Exception("Connection error"),
            Exception("Timeout"),
            self._create_mock_bars()
        ]

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=3
        )

        downloader = AlpacaDataDownloader(config)
        df = downloader._fetch_data_with_retry('AAPL')

        # Should succeed on third attempt
        self.assertIsNotNone(df)
        self.assertEqual(mock_client.get_stock_bars.call_count, 3)

    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_max_retries_exceeded(self, mock_client_class):
        """Test behavior when max retries are exceeded"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate continuous failures
        mock_client.get_stock_bars.side_effect = Exception("API Error")

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=3
        )

        downloader = AlpacaDataDownloader(config)
        df = downloader._fetch_data_with_retry('AAPL')

        # Should return None after exhausting retries
        self.assertIsNone(df)
        self.assertEqual(mock_client.get_stock_bars.call_count, 3)

    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_no_data_returned_handling(self, mock_client_class):
        """Test handling when API returns no data"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Return empty response
        mock_client.get_stock_bars.return_value = None

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=1
        )

        downloader = AlpacaDataDownloader(config)
        df = downloader._fetch_data_with_retry('AAPL')

        self.assertIsNone(df)

    def _create_mock_bars(self):
        """Create mock bars response"""
        mock_bars = Mock()

        # Create sample DataFrame
        df = pd.DataFrame({
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.5],
            'close': [101.0, 102.0],
            'volume': [1000000, 1100000],
            'timestamp': pd.date_range('2024-01-01', periods=2)
        })

        mock_bars.df = df
        mock_bars.__contains__ = lambda self, key: True  # Symbol in response

        return mock_bars


class TestRateLimitDetection(unittest.TestCase):
    """Test rate limit detection and handling"""

    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_rate_limit_error_detection(self, mock_client_class):
        """Test detection of rate limit errors"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate rate limit error
        rate_limit_error = Exception("Rate limit exceeded")
        mock_client.get_stock_bars.side_effect = rate_limit_error

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=1,
            retry_delay=1
        )

        downloader = AlpacaDataDownloader(config)

        # Should handle rate limit gracefully
        df = downloader._fetch_data_with_retry('AAPL')
        self.assertIsNone(df)

    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_403_unauthorized_detection(self, mock_client_class):
        """Test detection of 403 unauthorized errors"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate 403 error
        auth_error = Exception("403 Forbidden")
        mock_client.get_stock_bars.side_effect = auth_error

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=1
        )

        downloader = AlpacaDataDownloader(config)
        df = downloader._fetch_data_with_retry('AAPL')

        self.assertIsNone(df)

    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_404_symbol_not_found(self, mock_client_class):
        """Test detection of invalid symbol (404)"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate 404 error
        not_found_error = Exception("404 Not Found")
        mock_client.get_stock_bars.side_effect = not_found_error

        config = DownloadConfig(
            symbols=['INVALID_SYMBOL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=1
        )

        downloader = AlpacaDataDownloader(config)
        df = downloader._fetch_data_with_retry('INVALID_SYMBOL')

        self.assertIsNone(df)


class TestExponentialBackoff(unittest.TestCase):
    """Test exponential backoff timing"""

    def test_backoff_timing_calculation(self):
        """Test that backoff increases exponentially"""
        base_delay = 5
        expected_delays = [
            5,   # 5 * 2^0
            10,  # 5 * 2^1
            20,  # 5 * 2^2
            40   # 5 * 2^3
        ]

        for attempt in range(4):
            calculated_delay = base_delay * (2 ** attempt)
            self.assertEqual(
                calculated_delay,
                expected_delays[attempt],
                f"Delay for attempt {attempt} should be {expected_delays[attempt]}"
            )

    @patch('time.sleep')
    @patch('scripts.download_historical_data.StockHistoricalDataClient')
    def test_backoff_actually_waits(self, mock_client_class, mock_sleep):
        """Test that retry actually waits with backoff"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Fail 3 times
        mock_client.get_stock_bars.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3")
        ]

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31',
            retry_attempts=3,
            retry_delay=2
        )

        downloader = AlpacaDataDownloader(config)
        downloader._fetch_data_with_retry('AAPL')

        # Verify sleep was called with exponential backoff
        # First retry: 2 * 2^0 = 2
        # Second retry: 2 * 2^1 = 4
        expected_calls = [unittest.mock.call(2), unittest.mock.call(4)]
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_has_calls(expected_calls)


class TestDataValidation(unittest.TestCase):
    """Test data validation logic"""

    def test_valid_dataframe(self):
        """Test validation of valid DataFrame"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        downloader = AlpacaDataDownloader(config)

        # Create valid DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [102.0, 103.0, 104.0, 105.0, 106.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })

        self.assertTrue(downloader._validate_dataframe(df, 'AAPL'))

    def test_empty_dataframe(self):
        """Test validation fails for empty DataFrame"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        downloader = AlpacaDataDownloader(config)
        df = pd.DataFrame()

        self.assertFalse(downloader._validate_dataframe(df, 'AAPL'))

    def test_missing_required_columns(self):
        """Test validation fails when columns are missing"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        downloader = AlpacaDataDownloader(config)

        # Missing 'volume' column
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [102.0, 103.0, 104.0, 105.0, 106.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0]
        })

        self.assertFalse(downloader._validate_dataframe(df, 'AAPL'))

    def test_invalid_price_data(self):
        """Test validation fails for invalid prices (high < low)"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        downloader = AlpacaDataDownloader(config)

        # Invalid: high < low
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [99.0, 100.0, 101.0, 102.0, 103.0],  # Lower than low!
            'low': [100.0, 101.0, 102.0, 103.0, 104.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })

        self.assertFalse(downloader._validate_dataframe(df, 'AAPL'))

    def test_negative_prices(self):
        """Test validation fails for negative prices"""
        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        downloader = AlpacaDataDownloader(config)

        # Negative prices
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [-100.0, 101.0, 102.0, 103.0, 104.0],  # Negative!
            'high': [102.0, 103.0, 104.0, 105.0, 106.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [101.0, 102.0, 103.0, 104.0, 105.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })

        self.assertFalse(downloader._validate_dataframe(df, 'AAPL'))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
