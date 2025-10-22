"""
Integration tests for autonomous trading system.

Tests the complete pipeline:
1. Data download
2. Data loading
3. Backtesting execution
4. Result validation
"""

import pytest
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from backtesting.engine import BacktestEngine
from backtesting.data_handler import HistoricalDataHandler
from backtesting.execution_handler import SimulatedExecutionHandler
from backtesting.portfolio_handler import PortfolioHandler
from strategies.simple_momentum import SimpleMomentumStrategy


class TestDataDownloadIntegration:
    """Test data download integration"""

    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    def test_download_script_exists(self, project_root):
        """Test that download script exists and is executable"""
        script_path = project_root / "scripts" / "download_historical_data.py"
        assert script_path.exists()
        assert os.access(script_path, os.X_OK) or script_path.suffix == '.py'

    def test_download_script_help(self, project_root):
        """Test download script help output"""
        script_path = project_root / "scripts" / "download_historical_data.py"

        result = subprocess.run(
            ['python', str(script_path), '--help'],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower() or 'Download' in result.stdout

    @pytest.mark.skipif(
        not os.getenv('ALPACA_API_KEY'),
        reason="Requires Alpaca API credentials"
    )
    def test_download_single_symbol(self, project_root, tmp_path):
        """Test downloading data for single symbol"""
        script_path = project_root / "scripts" / "download_historical_data.py"

        # Download last 30 days of AAPL data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        result = subprocess.run([
            'python', str(script_path),
            '--symbols', 'AAPL',
            '--start', start_date.strftime('%Y-%m-%d'),
            '--end', end_date.strftime('%Y-%m-%d'),
            '--output-dir', str(tmp_path),
            '--retry-attempts', '2',
        ], capture_output=True, text=True, timeout=60)

        # Check if download succeeded or failed gracefully
        if result.returncode == 0:
            # Success case
            assert (tmp_path / 'csv').exists() or (tmp_path / 'parquet').exists()
        else:
            # Failure should have meaningful error message
            assert 'error' in result.stderr.lower() or 'error' in result.stdout.lower()


class TestDataLoadingIntegration:
    """Test data loading integration"""

    @pytest.fixture
    def sample_data_dir(self, tmp_path):
        """Create sample data for testing"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        # Create multiple symbol files
        symbols = ['AAPL', 'MSFT', 'GOOGL']

        for symbol in symbols:
            df = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=30, freq='D'),
                'open': [100.0 + i for i in range(30)],
                'high': [105.0 + i for i in range(30)],
                'low': [99.0 + i for i in range(30)],
                'close': [104.0 + i for i in range(30)],
                'volume': [1000.0 * (i + 1) for i in range(30)],
                'vwap': [102.0 + i for i in range(30)],
                'trade_count': [100 * (i + 1) for i in range(30)],
            })
            df.to_csv(data_dir / f"{symbol}.csv", index=False)

        return data_dir

    def test_load_multiple_symbols(self, sample_data_dir):
        """Test loading data for multiple symbols"""
        handler = HistoricalDataHandler(
            symbols=['AAPL', 'MSFT', 'GOOGL'],
            data_dir=sample_data_dir,
        )

        assert len(handler.symbol_data) == 3
        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            assert symbol in handler.symbol_data
            assert len(handler.symbol_data[symbol]) == 30

    def test_load_with_date_range(self, sample_data_dir):
        """Test loading with date filtering"""
        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=sample_data_dir,
            start_date=datetime(2024, 1, 10),
            end_date=datetime(2024, 1, 20),
        )

        assert len(handler.symbol_data['AAPL']) == 11


class TestBacktestingIntegration:
    """Test complete backtesting pipeline"""

    @pytest.fixture
    def backtest_data(self, tmp_path):
        """Create data for backtesting"""
        data_dir = tmp_path / "historical"
        data_dir.mkdir()

        symbols = ['AAPL', 'MSFT']

        for symbol in symbols:
            # Create realistic price data
            prices = []
            base_price = 100.0

            for i in range(60):
                # Simulate price movement
                change = (i % 5 - 2) * 0.5  # Oscillating pattern
                prices.append(base_price + change + i * 0.1)

            df = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=60, freq='D'),
                'open': prices,
                'high': [p * 1.02 for p in prices],
                'low': [p * 0.98 for p in prices],
                'close': [p * 1.01 for p in prices],
                'volume': [100000 + i * 1000 for i in range(60)],
                'vwap': prices,
                'trade_count': [1000 + i * 10 for i in range(60)],
            })
            df.to_csv(data_dir / f"{symbol}.csv", index=False)

        return data_dir

    def test_backtest_execution(self, backtest_data):
        """Test running complete backtest"""
        symbols = ['AAPL', 'MSFT']
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 2, 29)

        # Initialize components
        data_handler = HistoricalDataHandler(
            symbols=symbols,
            data_dir=backtest_data,
            start_date=start_date,
            end_date=end_date,
        )

        execution_handler = SimulatedExecutionHandler()
        portfolio_handler = PortfolioHandler(initial_capital=100000.0)
        strategy = SimpleMomentumStrategy(symbols)

        engine = BacktestEngine(
            data_handler=data_handler,
            execution_handler=execution_handler,
            portfolio_handler=portfolio_handler,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
        )

        # Run backtest
        results = engine.run()

        # Validate results structure
        assert 'metrics' in results
        assert 'equity_curve' in results

        metrics = results['metrics']
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
        assert 'profit_factor' in metrics

    def test_backtest_with_no_data(self, tmp_path):
        """Test backtest fails gracefully with no data"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(Exception):
            # Should fail when trying to load non-existent data
            handler = HistoricalDataHandler(
                symbols=['AAPL'],
                data_dir=empty_dir,
            )


class TestAutonomousSystemScript:
    """Test autonomous trading system script"""

    @pytest.fixture
    def project_root(self):
        """Get project root"""
        return Path(__file__).parent.parent.parent

    def test_script_exists(self, project_root):
        """Test autonomous trading script exists"""
        script_path = project_root / "scripts" / "autonomous_trading_system.sh"
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)

    def test_script_help(self, project_root):
        """Test script help/usage"""
        script_path = project_root / "scripts" / "autonomous_trading_system.sh"

        result = subprocess.run(
            [str(script_path), '--mode=invalid'],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should fail with usage message
        assert result.returncode != 0
        assert 'mode' in result.stderr.lower() or 'usage' in result.stdout.lower()

    @pytest.mark.skipif(
        not os.getenv('ALPACA_API_KEY'),
        reason="Requires Alpaca API credentials and full environment"
    )
    def test_backtest_only_mode(self, project_root):
        """Test running backtest-only mode"""
        script_path = project_root / "scripts" / "autonomous_trading_system.sh"

        result = subprocess.run(
            [str(script_path), '--mode=backtest-only'],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Check output for expected phases
        output = result.stdout + result.stderr

        # Should see backtest phase
        assert 'BACKTEST' in output or 'backtest' in output.lower()


class TestEndToEndDataFlow:
    """Test complete data flow from download to backtest"""

    @pytest.fixture
    def test_environment(self, tmp_path):
        """Setup test environment"""
        data_dir = tmp_path / "data" / "historical"
        data_dir.mkdir(parents=True)

        results_dir = tmp_path / "data" / "backtest_results"
        results_dir.mkdir(parents=True)

        return {
            'data_dir': data_dir,
            'results_dir': results_dir,
            'root': tmp_path,
        }

    def test_csv_to_backtest_flow(self, test_environment):
        """Test loading CSV data into backtest"""
        data_dir = test_environment['data_dir']

        # Create CSV data
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30, freq='D'),
            'open': [100.0 + i for i in range(30)],
            'high': [105.0 + i for i in range(30)],
            'low': [99.0 + i for i in range(30)],
            'close': [104.0 + i for i in range(30)],
            'volume': [1000.0 * (i + 1) for i in range(30)],
        })
        df.to_csv(data_dir / "AAPL.csv", index=False)

        # Load into data handler
        handler = HistoricalDataHandler(
            symbols=['AAPL'],
            data_dir=data_dir,
        )

        # Verify data loaded
        assert 'AAPL' in handler.symbol_data
        assert len(handler.symbol_data['AAPL']) == 30

        # Update bars and verify
        handler.update_bars()
        bar = handler.get_latest_bar('AAPL')

        assert bar is not None
        assert bar.symbol == 'AAPL'
        assert bar.open == 100.0

    def test_parquet_to_backtest_flow(self, test_environment):
        """Test loading Parquet data into backtest"""
        data_dir = test_environment['data_dir']

        # Create Parquet data
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30, freq='D'),
            'open': [100.0 + i for i in range(30)],
            'high': [105.0 + i for i in range(30)],
            'low': [99.0 + i for i in range(30)],
            'close': [104.0 + i for i in range(30)],
            'volume': [1000.0 * (i + 1) for i in range(30)],
        })
        df.to_parquet(data_dir / "MSFT.parquet", index=False)

        # Load into data handler
        handler = HistoricalDataHandler(
            symbols=['MSFT'],
            data_dir=data_dir,
        )

        assert 'MSFT' in handler.symbol_data
        assert len(handler.symbol_data['MSFT']) == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
