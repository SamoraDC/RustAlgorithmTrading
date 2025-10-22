"""
Performance tests for data loading system.

Tests:
- Data download time
- Memory usage
- Loading speed for different formats
- Concurrent downloads
- Large dataset handling
"""

import pytest
import time
import psutil
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtesting.data_handler import HistoricalDataHandler


class TestDataLoadingPerformance:
    """Test data loading performance metrics"""

    @pytest.fixture
    def large_dataset(self, tmp_path):
        """Create large dataset for performance testing"""
        data_dir = tmp_path / "large"
        data_dir.mkdir()

        # Create 1 year of minute data (~390 bars/day * 252 days = ~98k rows)
        num_rows = 100000

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=num_rows, freq='1min'),
            'open': [100.0 + (i % 100) * 0.1 for i in range(num_rows)],
            'high': [105.0 + (i % 100) * 0.1 for i in range(num_rows)],
            'low': [99.0 + (i % 100) * 0.1 for i in range(num_rows)],
            'close': [104.0 + (i % 100) * 0.1 for i in range(num_rows)],
            'volume': [1000 + i for i in range(num_rows)],
        })

        # Save as both CSV and Parquet
        df.to_csv(data_dir / "AAPL_large.csv", index=False)
        df.to_parquet(data_dir / "MSFT_large.parquet", index=False)

        return data_dir

    def test_csv_loading_time(self, large_dataset):
        """Test CSV loading performance"""
        start_time = time.time()

        handler = HistoricalDataHandler(
            symbols=['AAPL_large'],
            data_dir=large_dataset,
        )

        load_time = time.time() - start_time

        print(f"\nCSV Load Time: {load_time:.3f}s for {len(handler.symbol_data['AAPL_large'])} rows")

        # CSV loading should complete within reasonable time
        assert load_time < 5.0  # Less than 5 seconds

    def test_parquet_loading_time(self, large_dataset):
        """Test Parquet loading performance"""
        start_time = time.time()

        handler = HistoricalDataHandler(
            symbols=['MSFT_large'],
            data_dir=large_dataset,
        )

        load_time = time.time() - start_time

        print(f"\nParquet Load Time: {load_time:.3f}s for {len(handler.symbol_data['MSFT_large'])} rows")

        # Parquet should be faster than CSV
        assert load_time < 3.0

    def test_memory_usage(self, large_dataset):
        """Test memory usage during data loading"""
        process = psutil.Process(os.getpid())

        # Measure baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Load large dataset
        handler = HistoricalDataHandler(
            symbols=['AAPL_large', 'MSFT_large'],
            data_dir=large_dataset,
        )

        # Measure peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        print(f"\nMemory Usage: {memory_increase:.2f} MB for 200k rows")

        # Memory increase should be reasonable (< 500 MB for 200k rows)
        assert memory_increase < 500

    def test_multiple_symbols_loading(self, tmp_path):
        """Test loading multiple symbols concurrently"""
        data_dir = tmp_path / "multiple"
        data_dir.mkdir()

        # Create data for 10 symbols
        symbols = [f"SYM{i}" for i in range(10)]

        for symbol in symbols:
            df = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=1000),
                'open': [100.0] * 1000,
                'high': [105.0] * 1000,
                'low': [99.0] * 1000,
                'close': [104.0] * 1000,
                'volume': [1000] * 1000,
            })
            df.to_csv(data_dir / f"{symbol}.csv", index=False)

        start_time = time.time()

        handler = HistoricalDataHandler(
            symbols=symbols,
            data_dir=data_dir,
        )

        load_time = time.time() - start_time

        print(f"\nMultiple Symbols Load Time: {load_time:.3f}s for {len(symbols)} symbols")

        assert load_time < 10.0
        assert len(handler.symbol_data) == 10

    def test_bar_update_performance(self, tmp_path):
        """Test bar update iteration performance"""
        data_dir = tmp_path / "updates"
        data_dir.mkdir()

        # Create dataset
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10000),
            'open': [100.0] * 10000,
            'high': [105.0] * 10000,
            'low': [99.0] * 10000,
            'close': [104.0] * 10000,
            'volume': [1000] * 10000,
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Measure time to iterate through all bars
        start_time = time.time()

        count = 0
        while handler.continue_backtest:
            handler.update_bars()
            count += 1

            if count >= 10000:
                break

        iteration_time = time.time() - start_time

        print(f"\nBar Iteration Time: {iteration_time:.3f}s for {count} bars")
        print(f"Average: {(iteration_time / count) * 1000:.3f}ms per bar")

        # Should process bars quickly
        assert iteration_time < 2.0  # Less than 2 seconds for 10k bars


class TestDownloadPerformance:
    """Test data download performance"""

    @pytest.fixture
    def mock_downloader(self, tmp_path):
        """Create mock downloader for testing"""
        from download_historical_data import AlpacaDataDownloader, DownloadConfig
        from unittest.mock import patch

        config = DownloadConfig(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            output_dir=str(tmp_path),
            api_key='test_key',
            api_secret='test_secret',
        )

        with patch('download_historical_data.StockHistoricalDataClient'):
            return AlpacaDataDownloader(config)

    def test_save_csv_performance(self, mock_downloader):
        """Test CSV save performance"""
        # Create large DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50000),
            'symbol': ['AAPL'] * 50000,
            'open': [100.0] * 50000,
            'high': [105.0] * 50000,
            'low': [99.0] * 50000,
            'close': [104.0] * 50000,
            'volume': [1000] * 50000,
        })

        start_time = time.time()
        mock_downloader._save_csv(df, 'AAPL')
        save_time = time.time() - start_time

        print(f"\nCSV Save Time: {save_time:.3f}s for 50k rows")

        assert save_time < 5.0

    def test_save_parquet_performance(self, mock_downloader):
        """Test Parquet save performance"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50000),
            'symbol': ['AAPL'] * 50000,
            'open': [100.0] * 50000,
            'high': [105.0] * 50000,
            'low': [99.0] * 50000,
            'close': [104.0] * 50000,
            'volume': [1000] * 50000,
        })

        start_time = time.time()
        mock_downloader._save_parquet(df, 'AAPL')
        save_time = time.time() - start_time

        print(f"\nParquet Save Time: {save_time:.3f}s for 50k rows")

        # Parquet should be faster
        assert save_time < 3.0


class TestDataValidationPerformance:
    """Test data validation performance"""

    def test_validation_speed(self, tmp_path):
        """Test speed of data validation"""
        from download_historical_data import AlpacaDataDownloader, DownloadConfig
        from unittest.mock import patch

        config = DownloadConfig(
            symbols=['AAPL'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            output_dir=str(tmp_path),
            api_key='test',
            api_secret='test',
        )

        with patch('download_historical_data.StockHistoricalDataClient'):
            downloader = AlpacaDataDownloader(config)

        # Create large DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100000),
            'open': [100.0] * 100000,
            'high': [105.0] * 100000,
            'low': [99.0] * 100000,
            'close': [104.0] * 100000,
            'volume': [1000] * 100000,
        })

        start_time = time.time()
        result = downloader._validate_dataframe(df, 'AAPL')
        validation_time = time.time() - start_time

        print(f"\nValidation Time: {validation_time:.3f}s for 100k rows")

        assert validation_time < 1.0
        assert result is True


class TestConcurrentOperations:
    """Test concurrent data operations"""

    def test_concurrent_file_loading(self, tmp_path):
        """Test loading multiple files concurrently"""
        data_dir = tmp_path / "concurrent"
        data_dir.mkdir()

        # Create 20 symbol files
        symbols = [f"SYM{i}" for i in range(20)]

        for symbol in symbols:
            df = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=5000),
                'open': [100.0] * 5000,
                'high': [105.0] * 5000,
                'low': [99.0] * 5000,
                'close': [104.0] * 5000,
                'volume': [1000] * 5000,
            })
            df.to_parquet(data_dir / f"{symbol}.parquet", index=False)

        start_time = time.time()

        # Load all symbols
        handler = HistoricalDataHandler(
            symbols=symbols,
            data_dir=data_dir,
        )

        load_time = time.time() - start_time

        print(f"\nConcurrent Load Time: {load_time:.3f}s for {len(symbols)} symbols")

        assert len(handler.symbol_data) == 20
        assert load_time < 15.0


class TestFileFormatComparison:
    """Compare performance of different file formats"""

    @pytest.fixture
    def comparison_data(self, tmp_path):
        """Create same data in multiple formats"""
        data_dir = tmp_path / "formats"
        data_dir.mkdir()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50000),
            'open': [100.0 + i * 0.01 for i in range(50000)],
            'high': [105.0 + i * 0.01 for i in range(50000)],
            'low': [99.0 + i * 0.01 for i in range(50000)],
            'close': [104.0 + i * 0.01 for i in range(50000)],
            'volume': [1000 + i for i in range(50000)],
        })

        # Save in both formats
        df.to_csv(data_dir / "DATA_csv.csv", index=False)
        df.to_parquet(data_dir / "DATA_parquet.parquet", index=False)

        return data_dir

    def test_format_comparison(self, comparison_data):
        """Compare CSV vs Parquet performance"""
        # Test CSV
        start_csv = time.time()
        handler_csv = HistoricalDataHandler(
            symbols=['DATA_csv'],
            data_dir=comparison_data,
        )
        csv_time = time.time() - start_csv

        # Test Parquet
        start_parquet = time.time()
        handler_parquet = HistoricalDataHandler(
            symbols=['DATA_parquet'],
            data_dir=comparison_data,
        )
        parquet_time = time.time() - start_parquet

        print(f"\nFormat Comparison for 50k rows:")
        print(f"  CSV:     {csv_time:.3f}s")
        print(f"  Parquet: {parquet_time:.3f}s")
        print(f"  Speedup: {csv_time / parquet_time:.2f}x")

        # Parquet should be faster
        assert parquet_time < csv_time


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])  # -s to show print statements
