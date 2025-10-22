"""
Unit tests for HistoricalDataHandler.

Tests:
- Data loading from CSV/Parquet
- Bar updates and iteration
- Data validation
- Error handling
- Edge cases
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from backtesting.data_handler import HistoricalDataHandler
from models.market import Bar


class TestHistoricalDataHandlerInit:
    """Test HistoricalDataHandler initialization"""

    @pytest.fixture
    def test_data_dir(self, tmp_path):
        """Create temporary data directory with test data"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        # Create test CSV
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='D'),
            'open': [100 + i for i in range(10)],
            'high': [105 + i for i in range(10)],
            'low': [99 + i for i in range(10)],
            'close': [104 + i for i in range(10)],
            'volume': [1000 * (i + 1) for i in range(10)],
            'vwap': [102 + i for i in range(10)],
            'trade_count': [100 * (i + 1) for i in range(10)],
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        # Create test Parquet
        df.to_parquet(data_dir / "MSFT.parquet", index=False)

        return data_dir

    def test_init_valid_params(self, test_data_dir):
        """Test initialization with valid parameters"""
        handler = HistoricalDataHandler(
            symbols=['AAPL', 'MSFT'],
            data_dir=test_data_dir,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 10),
        )

        assert handler.symbols == ['AAPL', 'MSFT']
        assert handler.data_dir == test_data_dir
        assert len(handler.symbol_data) == 2

    def test_init_empty_symbols(self, test_data_dir):
        """Test initialization with empty symbols list"""
        with pytest.raises(ValueError, match="symbols list cannot be empty"):
            HistoricalDataHandler(
                symbols=[],
                data_dir=test_data_dir,
            )

    def test_init_invalid_symbols_type(self, test_data_dir):
        """Test initialization with invalid symbols type"""
        with pytest.raises(TypeError, match="symbols must be a list"):
            HistoricalDataHandler(
                symbols='AAPL',
                data_dir=test_data_dir,
            )

    def test_init_invalid_symbol_element(self, test_data_dir):
        """Test initialization with non-string symbol"""
        with pytest.raises(TypeError, match="All symbols must be strings"):
            HistoricalDataHandler(
                symbols=['AAPL', 123],
                data_dir=test_data_dir,
            )

    def test_init_invalid_data_dir_type(self):
        """Test initialization with invalid data_dir type"""
        with pytest.raises(TypeError, match="data_dir must be a valid path"):
            HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=None,
            )

    def test_init_nonexistent_data_dir(self, tmp_path):
        """Test initialization creates missing data directory"""
        data_dir = tmp_path / "nonexistent"

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        assert data_dir.exists()

    def test_init_invalid_date_types(self, test_data_dir):
        """Test initialization with invalid date types"""
        with pytest.raises(TypeError, match="start_date must be datetime or None"):
            HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=test_data_dir,
                start_date='2024-01-01',
            )

    def test_init_invalid_date_range(self, test_data_dir):
        """Test initialization with start_date >= end_date"""
        with pytest.raises(ValueError, match="start_date .* must be before end_date"):
            HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=test_data_dir,
                start_date=datetime(2024, 1, 10),
                end_date=datetime(2024, 1, 1),
            )


class TestDataLoading:
    """Test data loading functionality"""

    @pytest.fixture
    def test_data_dir(self, tmp_path):
        """Create test data directory"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        # Valid CSV
        df_valid = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='D'),
            'open': [100.0 + i for i in range(10)],
            'high': [105.0 + i for i in range(10)],
            'low': [99.0 + i for i in range(10)],
            'close': [104.0 + i for i in range(10)],
            'volume': [1000.0 * (i + 1) for i in range(10)],
        })
        df_valid.to_csv(data_dir / "AAPL.csv", index=False)

        # Parquet with extra columns
        df_with_extras = df_valid.copy()
        df_with_extras['vwap'] = [102.0 + i for i in range(10)]
        df_with_extras['trade_count'] = [100 * (i + 1) for i in range(10)]
        df_with_extras.to_parquet(data_dir / "MSFT.parquet", index=False)

        return data_dir

    def test_load_csv_data(self, test_data_dir):
        """Test loading data from CSV"""
        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=test_data_dir,
        )

        assert 'AAPL' in handler.symbol_data
        assert len(handler.symbol_data['AAPL']) == 10

    def test_load_parquet_data(self, test_data_dir):
        """Test loading data from Parquet"""
        handler = HistoricalDataHandler(
            symbols=['MSFT'],
            data_dir=test_data_dir,
        )

        assert 'MSFT' in handler.symbol_data
        assert len(handler.symbol_data['MSFT']) == 10

    def test_load_missing_file(self, test_data_dir):
        """Test loading non-existent symbol"""
        handler = HistoricalDataHandler(
            symbols=['GOOGL'],
            data_dir=test_data_dir,
        )

        # Should not raise error, just skip symbol
        assert 'GOOGL' not in handler.symbol_data

    def test_load_with_date_filter(self, test_data_dir):
        """Test loading with date range filter"""
        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=test_data_dir,
            start_date=datetime(2024, 1, 3),
            end_date=datetime(2024, 1, 7),
        )

        assert len(handler.symbol_data['AAPL']) == 5

    def test_load_invalid_csv_missing_columns(self, tmp_path):
        """Test loading CSV with missing required columns"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        # CSV missing 'close' column
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [99, 100, 101, 102, 103],
            # Missing close
            'volume': [1000, 2000, 3000, 4000, 5000],
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        with pytest.raises(ValueError, match="Missing required columns"):
            HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=data_dir,
            )

    def test_load_invalid_prices(self, tmp_path):
        """Test data validation catches invalid prices"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        # Data where high < low
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5),
            'open': [100, 101, 102, 103, 104],
            'high': [99, 100, 101, 102, 103],  # Lower than low
            'low': [105, 106, 107, 108, 109],
            'close': [104, 105, 106, 107, 108],
            'volume': [1000, 2000, 3000, 4000, 5000],
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Should still load but log warning
        assert 'AAPL' in handler.symbol_data


class TestBarUpdates:
    """Test bar update functionality"""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create handler with test data"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=5, freq='D'),
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [105.0, 106.0, 107.0, 108.0, 109.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [104.0, 105.0, 106.0, 107.0, 108.0],
            'volume': [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
            'vwap': [102.0, 103.0, 104.0, 105.0, 106.0],
            'trade_count': [100, 200, 300, 400, 500],
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        return HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

    def test_update_bars(self, handler):
        """Test bar updates advance correctly"""
        handler.update_bars()

        assert handler.bar_index == 1
        assert len(handler.latest_bars['AAPL']) == 1

    def test_multiple_updates(self, handler):
        """Test multiple bar updates"""
        for i in range(3):
            handler.update_bars()

        assert handler.bar_index == 3
        assert len(handler.latest_bars['AAPL']) == 3

    def test_get_latest_bar(self, handler):
        """Test getting latest bar"""
        handler.update_bars()
        bar = handler.get_latest_bar('AAPL')

        assert bar is not None
        assert bar.symbol == 'AAPL'
        assert bar.open == 100.0
        assert bar.close == 104.0

    def test_get_latest_bars_multiple(self, handler):
        """Test getting multiple latest bars"""
        for _ in range(3):
            handler.update_bars()

        bars = handler.get_latest_bars('AAPL', n=2)
        assert len(bars) == 2
        assert bars[0].open == 101.0
        assert bars[1].open == 102.0

    def test_get_latest_bar_value(self, handler):
        """Test getting specific bar field value"""
        handler.update_bars()

        close = handler.get_latest_bar_value('AAPL', 'close')
        assert close == 104.0

        volume = handler.get_latest_bar_value('AAPL', 'volume')
        assert volume == 1000.0

    def test_get_latest_bars_values(self, handler):
        """Test getting field values from multiple bars"""
        for _ in range(3):
            handler.update_bars()

        closes = handler.get_latest_bars_values('AAPL', 'close', n=3)
        assert closes == [104.0, 105.0, 106.0]

    def test_backtest_continues(self, handler):
        """Test backtest continuation flag"""
        assert handler.continue_backtest is True

        # Update past all data
        for _ in range(10):
            handler.update_bars()

        assert handler.continue_backtest is False

    def test_get_bar_invalid_symbol(self, handler):
        """Test getting bar for invalid symbol"""
        handler.update_bars()
        bar = handler.get_latest_bar('INVALID')
        assert bar is None

    def test_get_bar_invalid_field(self, handler):
        """Test getting invalid bar field"""
        handler.update_bars()

        with pytest.raises(ValueError, match="Invalid field"):
            handler.get_latest_bar_value('AAPL', 'invalid_field')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
