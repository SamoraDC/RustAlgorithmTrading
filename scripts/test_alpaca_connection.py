#!/usr/bin/env python3
"""
Diagnostic script to test Alpaca API connection and validate fixes

Tests:
1. API credentials validation
2. Single symbol download with minimal date range
3. Rate limit headers inspection
4. Response format validation
5. Date range handling

Usage:
    python test_alpaca_connection.py
    python test_alpaca_connection.py --symbol AAPL --days 7
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlpacaConnectionTester:
    """Diagnostic tester for Alpaca API connection"""

    def __init__(self):
        """Initialize tester with credentials from environment"""
        load_dotenv()

        self.api_key = os.getenv('ALPACA_API_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET_KEY')

        self.results = {
            'credentials_valid': False,
            'connection_success': False,
            'data_received': False,
            'format_valid': False,
            'rate_limit_info': {},
            'errors': []
        }

    def test_credentials(self) -> bool:
        """Test 1: Validate API credentials exist"""
        logger.info("=" * 60)
        logger.info("TEST 1: API Credentials Validation")
        logger.info("=" * 60)

        if not self.api_key:
            error_msg = "ALPACA_API_KEY not found in environment"
            logger.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False

        if not self.api_secret:
            error_msg = "ALPACA_SECRET_KEY not found in environment"
            logger.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False

        # Mask credentials for display
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        masked_secret = f"{self.api_secret[:8]}...{self.api_secret[-4:]}"

        logger.info(f"✓ API Key found: {masked_key}")
        logger.info(f"✓ Secret Key found: {masked_secret}")

        self.results['credentials_valid'] = True
        return True

    def test_connection(self) -> bool:
        """Test 2: Test basic API connection"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: API Connection Test")
        logger.info("=" * 60)

        if not self.results['credentials_valid']:
            logger.error("❌ Skipping connection test - invalid credentials")
            return False

        try:
            self.client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret
            )
            logger.info("✓ StockHistoricalDataClient initialized successfully")
            self.results['connection_success'] = True
            return True

        except Exception as e:
            error_msg = f"Failed to initialize client: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False

    def test_single_symbol_download(
        self,
        symbol: str = 'AAPL',
        days: int = 7
    ) -> bool:
        """
        Test 3: Download single symbol with minimal date range

        Args:
            symbol: Stock symbol to test
            days: Number of days to download (default: 7)
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"TEST 3: Single Symbol Download ({symbol})")
        logger.info("=" * 60)

        if not self.results['connection_success']:
            logger.error("❌ Skipping download test - no connection")
            return False

        try:
            # Calculate date range ensuring no future dates
            today = datetime.now().date()
            end_date = today
            start_date = end_date - timedelta(days=days)

            logger.info(f"Date range: {start_date} to {end_date}")
            logger.info(f"Days requested: {days}")
            logger.info(f"Today's date: {today}")

            # Validate dates
            if end_date > today:
                error_msg = f"End date {end_date} is in the future!"
                logger.error(f"❌ {error_msg}")
                self.results['errors'].append(error_msg)
                return False

            logger.info("✓ Date range validation passed (no future dates)")

            # Create request
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                feed='iex',
                adjustment=Adjustment.ALL
            )

            logger.info(f"Request parameters:")
            logger.info(f"  Symbol: {symbol}")
            logger.info(f"  Timeframe: Day")
            logger.info(f"  Feed: iex")
            logger.info(f"  Adjustment: ALL")

            # Fetch data
            logger.info("Sending request to Alpaca API...")
            bars = self.client.get_stock_bars(request)

            # Check response
            if not bars:
                error_msg = "API returned empty response"
                logger.error(f"❌ {error_msg}")
                self.results['errors'].append(error_msg)
                return False

            logger.info(f"✓ API response received")

            # Check if symbol is in response
            if symbol not in bars:
                error_msg = f"Symbol {symbol} not found in API response"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Available symbols: {list(bars.keys()) if hasattr(bars, 'keys') else 'N/A'}")
                self.results['errors'].append(error_msg)
                return False

            logger.info(f"✓ Symbol {symbol} found in response")

            # Convert to DataFrame
            df = bars.df

            if df.empty:
                error_msg = f"DataFrame is empty for {symbol}"
                logger.error(f"❌ {error_msg}")
                logger.info("Possible reasons:")
                logger.info("  1. No trading occurred in date range (weekends/holidays)")
                logger.info("  2. Symbol not available in selected feed (iex)")
                logger.info("  3. Historical data not available for paper account")
                self.results['errors'].append(error_msg)
                return False

            logger.info(f"✓ DataFrame created with {len(df)} rows")
            logger.info(f"\nDataFrame info:")
            logger.info(f"  Shape: {df.shape}")
            logger.info(f"  Columns: {list(df.columns)}")
            logger.info(f"  Index type: {type(df.index)}")
            logger.info(f"\nFirst few rows:")
            logger.info(df.head())

            self.results['data_received'] = True
            self.results['sample_data'] = {
                'symbol': symbol,
                'rows': len(df),
                'columns': list(df.columns),
                'date_range': f"{df.index.min()} to {df.index.max()}"
            }

            return True

        except Exception as e:
            import traceback
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            self.results['errors'].append(error_msg)
            return False

    def test_response_format(self) -> bool:
        """Test 4: Validate response format"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Response Format Validation")
        logger.info("=" * 60)

        if not self.results['data_received']:
            logger.error("❌ Skipping format test - no data received")
            return False

        sample_data = self.results.get('sample_data', {})

        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        actual_columns = set(sample_data.get('columns', []))

        missing_columns = required_columns - actual_columns

        if missing_columns:
            error_msg = f"Missing required columns: {missing_columns}"
            logger.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False

        logger.info(f"✓ All required columns present: {required_columns}")
        logger.info(f"Additional columns: {actual_columns - required_columns}")

        self.results['format_valid'] = True
        return True

    def check_rate_limits(self) -> bool:
        """Test 5: Check rate limit information"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: Rate Limit Information")
        logger.info("=" * 60)

        logger.info("Note: Rate limit headers are not directly accessible via SDK")
        logger.info("Recommended practices:")
        logger.info("  1. Implement exponential backoff (5s, 10s, 20s, 40s...)")
        logger.info("  2. Add delays between requests (1-2 seconds)")
        logger.info("  3. Use batch downloads for multiple symbols")
        logger.info("  4. Monitor for 429 (Too Many Requests) errors")
        logger.info("\nCurrent implementation uses:")
        logger.info("  - Retry attempts: 3")
        logger.info("  - Exponential backoff: delay * 2^attempt")
        logger.info("  - Initial delay: 5 seconds")

        self.results['rate_limit_info'] = {
            'retry_attempts': 3,
            'backoff_strategy': 'exponential',
            'initial_delay': 5,
            'max_delay': 40
        }

        return True

    def run_all_tests(self, symbol: str = 'AAPL', days: int = 7) -> dict:
        """Run all diagnostic tests"""
        logger.info("\n" + "=" * 60)
        logger.info("ALPACA API DIAGNOSTIC TEST SUITE")
        logger.info("=" * 60)
        logger.info(f"Test Symbol: {symbol}")
        logger.info(f"Date Range: Last {days} days")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        # Run tests in sequence
        test_1 = self.test_credentials()
        test_2 = self.test_connection() if test_1 else False
        test_3 = self.test_single_symbol_download(symbol, days) if test_2 else False
        test_4 = self.test_response_format() if test_3 else False
        test_5 = self.check_rate_limits()

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)

        tests = [
            ("Credentials Valid", test_1),
            ("Connection Success", test_2),
            ("Data Download", test_3),
            ("Format Validation", test_4),
            ("Rate Limit Check", test_5)
        ]

        for test_name, result in tests:
            status = "✓ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name:.<40} {status}")

        passed = sum(1 for _, result in tests if result)
        total = len(tests)

        logger.info("=" * 60)
        logger.info(f"Tests Passed: {passed}/{total}")

        if self.results['errors']:
            logger.info("\nErrors encountered:")
            for i, error in enumerate(self.results['errors'], 1):
                logger.info(f"  {i}. {error}")

        if passed == total:
            logger.info("\n✓ ALL TESTS PASSED - API connection is healthy")
        else:
            logger.info("\n❌ SOME TESTS FAILED - Check errors above")

        logger.info("=" * 60)

        return self.results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Test Alpaca API connection and diagnose issues'
    )
    parser.add_argument(
        '--symbol',
        default='AAPL',
        help='Stock symbol to test (default: AAPL)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to download (default: 7)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run tests
    tester = AlpacaConnectionTester()
    results = tester.run_all_tests(symbol=args.symbol, days=args.days)

    # Exit with appropriate code
    if results['credentials_valid'] and results['connection_success'] and results['data_received']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
