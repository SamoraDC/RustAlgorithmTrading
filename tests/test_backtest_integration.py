"""
Integration tests for backtesting with correct initial capital.

Tests verify that the complete backtesting pipeline works correctly
with the fixed $1,000 initial capital.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import BacktestEngine
from backtesting.data_handler import HistoricalDataHandler
from backtesting.execution_handler import SimulatedExecutionHandler
from backtesting.portfolio_handler import PortfolioHandler
from strategies.simple_momentum import SimpleMomentumStrategy


class TestBacktestingIntegration:
    """Integration tests for backtesting pipeline."""

    def test_initial_capital_is_1000(self):
        """Test that initial capital is set to $1,000, not $100,000."""
        initial_capital = 1000.0

        portfolio = PortfolioHandler(initial_capital=initial_capital)

        assert portfolio.initial_capital == 1000.0
        assert portfolio.initial_capital != 100000.0
        print(f"✓ Initial capital correctly set to ${initial_capital:,.2f}")

    def test_backtest_with_real_data(self):
        """Test complete backtesting flow with real historical data."""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        data_dir = Path(__file__).parent.parent / 'data' / 'historical'

        # Check if data exists
        if not data_dir.exists():
            pytest.skip("Historical data directory not found")

        # Check for required files
        required_files = [data_dir / f"{symbol}.parquet" for symbol in symbols]
        if not all(f.exists() for f in required_files):
            # Try CSV
            required_files = [data_dir / f"{symbol}.csv" for symbol in symbols]
            if not all(f.exists() for f in required_files):
                pytest.skip("Required historical data files not found")

        # Setup backtest parameters
        start_date = datetime.now() - timedelta(days=90)
        end_date = datetime.now() - timedelta(days=1)
        initial_capital = 1000.0

        print(f"\n{'='*60}")
        print(f"BACKTEST INTEGRATION TEST")
        print(f"{'='*60}")
        print(f"Symbols: {symbols}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Initial capital: ${initial_capital:,.2f}")
        print(f"{'='*60}\n")

        # Initialize components
        try:
            data_handler = HistoricalDataHandler(
                symbols=symbols,
                data_dir=data_dir,
                start_date=start_date,
                end_date=end_date
            )

            execution_handler = SimulatedExecutionHandler()
            portfolio_handler = PortfolioHandler(initial_capital=initial_capital)
            strategy = SimpleMomentumStrategy(symbols)

            engine = BacktestEngine(
                data_handler=data_handler,
                execution_handler=execution_handler,
                portfolio_handler=portfolio_handler,
                strategy=strategy,
                start_date=start_date,
                end_date=end_date
            )

            # Run backtest
            results = engine.run()

            # Validate results structure
            assert 'metrics' in results
            assert 'equity_curve' in results

            metrics = results['metrics']

            # Print results
            print(f"\n{'='*60}")
            print(f"BACKTEST RESULTS")
            print(f"{'='*60}")

            if 'sharpe_ratio' in metrics:
                print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            if 'max_drawdown' in metrics:
                print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
            if 'win_rate' in metrics:
                print(f"Win Rate: {metrics['win_rate']:.2f}%")
            if 'profit_factor' in metrics:
                print(f"Profit Factor: {metrics['profit_factor']:.2f}")

            equity = results.get('equity_curve', {}).get('equity', [initial_capital])
            final_value = equity[-1] if equity else initial_capital
            total_return = ((final_value - initial_capital) / initial_capital) * 100

            print(f"\nInitial Capital: ${initial_capital:,.2f}")
            print(f"Final Value: ${final_value:,.2f}")
            print(f"Total Return: {total_return:.2f}%")
            print(f"{'='*60}\n")

            # Assertions
            assert portfolio_handler.initial_capital == 1000.0
            assert final_value > 0  # Portfolio should have positive value

            print("✓ Integration test PASSED")

        except Exception as e:
            print(f"\n✗ Integration test FAILED: {e}")
            import traceback
            traceback.print_exc()
            raise

    def test_timezone_handling_in_backtest(self):
        """Test that backtesting handles timezones correctly."""
        symbols = ['AAPL']
        data_dir = Path(__file__).parent.parent / 'data' / 'historical'

        if not data_dir.exists():
            pytest.skip("Historical data directory not found")

        # Use timezone-aware dates
        start_date = datetime(2024, 1, 1, 0, 0, 0)  # Naive
        end_date = datetime(2024, 1, 31, 23, 59, 59)  # Naive

        try:
            # Should not raise timezone comparison errors
            data_handler = HistoricalDataHandler(
                symbols=symbols,
                data_dir=data_dir,
                start_date=start_date,
                end_date=end_date
            )

            # Verify dates were converted to timezone-aware
            assert data_handler.start_date.tzinfo is not None
            assert data_handler.end_date.tzinfo is not None

            print("✓ Timezone handling test PASSED")

        except TypeError as e:
            if "can't compare" in str(e) and "timezone" in str(e).lower():
                pytest.fail(f"Timezone comparison error: {e}")
            else:
                raise


class TestCapitalConfiguration:
    """Test capital configuration across the system."""

    def test_portfolio_handler_capital(self):
        """Test PortfolioHandler respects initial capital."""
        test_capital = 1000.0
        portfolio = PortfolioHandler(initial_capital=test_capital)

        # Test initial capital is set correctly
        assert portfolio.initial_capital == test_capital
        assert portfolio.initial_capital != 100000.0

        print(f"✓ Portfolio initialized with ${test_capital:,.2f}")

    def test_script_uses_correct_capital(self):
        """Verify the autonomous trading script uses $1,000."""
        script_path = Path(__file__).parent.parent / 'scripts' / 'autonomous_trading_system.sh'

        if not script_path.exists():
            pytest.skip("Trading script not found")

        with open(script_path, 'r') as f:
            content = f.read()

        # Check for the correct capital value
        assert 'initial_capital = 1000.0' in content or 'initial_capital=1000.0' in content
        assert 'initial_capital = 100000.0' not in content
        assert 'initial_capital=100000.0' not in content

        print("✓ Script configured with correct initial capital")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
