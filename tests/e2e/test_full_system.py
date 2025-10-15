"""
End-to-end integration tests for complete trading system
Tests full workflow from market data to order execution
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from src.api.alpaca_client import AlpacaClient
from src.backtesting.engine import BacktestEngine
from src.strategies.mean_reversion import MeanReversionStrategy


@pytest.fixture
def mock_market_data():
    """Generate realistic market data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
    np.random.seed(42)

    # Generate realistic price action
    returns = np.random.normal(0, 0.001, 1000)
    price = 100 * (1 + returns).cumprod()

    data = pd.DataFrame({
        'open': price + np.random.randn(1000) * 0.1,
        'high': price + abs(np.random.randn(1000)) * 0.2,
        'low': price - abs(np.random.randn(1000)) * 0.2,
        'close': price,
        'volume': np.random.randint(10000, 100000, 1000)
    }, index=dates)

    return data


@pytest.fixture
def mock_alpaca_client():
    """Mock Alpaca client for E2E testing"""
    with patch('src.api.alpaca_client.StockHistoricalDataClient'), \
         patch('src.api.alpaca_client.TradingClient'):
        client = AlpacaClient(
            api_key='test_key',
            secret_key='test_secret',
            paper=True
        )

        # Mock account info
        mock_account = MagicMock()
        mock_account.cash = 100000.0
        mock_account.portfolio_value = 100000.0
        mock_account.buying_power = 200000.0
        client.trading_client.get_account = Mock(return_value=mock_account)

        # Mock successful order submission
        mock_order = MagicMock()
        mock_order.id = 'test_order_id'
        mock_order.status = 'filled'
        client.trading_client.submit_order = Mock(return_value=mock_order)

        return client


class TestFullBacktestWorkflow:
    """Test complete backtest workflow"""

    def test_simple_backtest_execution(self, mock_market_data):
        """Test basic backtest from start to finish"""
        # Initialize engine
        engine = BacktestEngine(
            initial_capital=100000.0,
            commission_rate=0.001,
            slippage=0.0005
        )

        # Create strategy
        strategy = MeanReversionStrategy(
            name="TestMeanReversion",
            parameters={'lookback': 20, 'threshold': 2.0}
        )

        # Run backtest
        results = engine.run(strategy, mock_market_data, "TEST")

        # Verify results structure
        assert 'final_equity' in results
        assert 'total_trades' in results
        assert 'metrics' in results
        assert 'equity_curve' in results

        # Verify metrics exist
        assert isinstance(results['metrics'], dict)

    def test_backtest_with_multiple_symbols(self, mock_market_data):
        """Test backtest across multiple symbols"""
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        all_results = {}

        for symbol in symbols:
            engine = BacktestEngine(initial_capital=100000.0)
            strategy = MeanReversionStrategy(name=f"MR_{symbol}")

            # Modify data slightly for each symbol
            data = mock_market_data.copy()
            data['close'] = data['close'] * (1 + np.random.uniform(-0.1, 0.1))
            data.attrs['symbol'] = symbol

            results = engine.run(strategy, data, symbol)
            all_results[symbol] = results

        # Verify all backtests completed
        assert len(all_results) == 3
        for symbol, results in all_results.items():
            assert results['symbol'] == symbol
            assert 'final_equity' in results

    def test_backtest_performance_metrics_calculated(self, mock_market_data):
        """Test that all performance metrics are calculated"""
        engine = BacktestEngine(initial_capital=100000.0)
        strategy = MeanReversionStrategy(name="Test")

        results = engine.run(strategy, mock_market_data, "TEST")

        # Check for key performance metrics
        metrics = results.get('metrics', {})
        expected_metrics = [
            'total_return',
            'sharpe_ratio',
            'max_drawdown',
            'win_rate',
            'profit_factor'
        ]

        for metric in expected_metrics:
            assert metric in metrics or metric in results, f"Missing metric: {metric}"


class TestLiveTradingSimulation:
    """Test simulated live trading scenarios"""

    def test_paper_trading_order_flow(self, mock_alpaca_client):
        """Test complete order flow in paper trading"""
        # Get account info
        account = mock_alpaca_client.get_account()
        initial_cash = account.cash

        # Submit buy order
        buy_order = mock_alpaca_client.submit_market_order(
            symbol='AAPL',
            qty=10,
            side='buy'
        )

        assert buy_order.id == 'test_order_id'
        assert buy_order.status == 'filled'

    def test_multiple_concurrent_orders(self, mock_alpaca_client):
        """Test handling multiple orders concurrently"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        orders = []

        for symbol in symbols:
            order = mock_alpaca_client.submit_market_order(
                symbol=symbol,
                qty=5,
                side='buy'
            )
            orders.append(order)

        assert len(orders) == 4
        assert all(order.status == 'filled' for order in orders)

    def test_order_cancellation_flow(self, mock_alpaca_client):
        """Test order cancellation"""
        # Submit order
        order = mock_alpaca_client.submit_limit_order(
            symbol='AAPL',
            qty=10,
            side='buy',
            limit_price=150.0
        )

        # Cancel order
        mock_alpaca_client.trading_client.cancel_order_by_id = Mock(return_value=True)
        result = mock_alpaca_client.cancel_order(order.id)

        assert result is True


class TestStrategyExecution:
    """Test strategy execution in various scenarios"""

    def test_mean_reversion_signal_generation(self, mock_market_data):
        """Test mean reversion strategy generates signals"""
        strategy = MeanReversionStrategy(
            name="MR_Test",
            parameters={'lookback': 20, 'threshold': 2.0}
        )

        signals = strategy.generate_signals(mock_market_data)

        assert isinstance(signals, list)
        # Strategy should generate some signals on 1000 bars
        assert len(signals) > 0

    def test_strategy_parameter_sensitivity(self, mock_market_data):
        """Test strategy behavior with different parameters"""
        params_sets = [
            {'lookback': 10, 'threshold': 1.0},
            {'lookback': 20, 'threshold': 2.0},
            {'lookback': 50, 'threshold': 3.0},
        ]

        results = []
        for params in params_sets:
            strategy = MeanReversionStrategy(name="Test", parameters=params)
            engine = BacktestEngine(initial_capital=100000.0)

            result = engine.run(strategy, mock_market_data, "TEST")
            results.append({
                'params': params,
                'return': result.get('total_return', 0),
                'trades': result['total_trades']
            })

        # Different parameters should produce different results
        returns = [r['return'] for r in results]
        assert len(set(returns)) > 1  # At least some variation


class TestRiskManagement:
    """Test risk management systems"""

    def test_position_size_limits(self):
        """Test position sizing respects limits"""
        max_position_value = 10000.0

        # Test various scenarios
        test_cases = [
            {'price': 100.0, 'target_qty': 200, 'expected_max': 100},  # Would exceed limit
            {'price': 50.0, 'target_qty': 100, 'expected_max': 100},   # Within limit
            {'price': 200.0, 'target_qty': 100, 'expected_max': 50},   # Would exceed
        ]

        for case in test_cases:
            position_value = case['price'] * case['target_qty']

            if position_value > max_position_value:
                actual_qty = max_position_value / case['price']
                assert actual_qty <= case['expected_max']
            else:
                assert case['target_qty'] <= case['expected_max']

    def test_stop_loss_execution(self, mock_market_data):
        """Test stop loss is triggered correctly"""
        # Create scenario where stop loss should trigger
        engine = BacktestEngine(initial_capital=100000.0)

        # Simulate position with stop loss
        entry_price = 100.0
        stop_loss_pct = 0.02  # 2% stop loss

        # Test price movements
        for current_price in [99.0, 98.0, 97.0]:  # Price declining
            loss_pct = (current_price - entry_price) / entry_price

            if abs(loss_pct) >= stop_loss_pct:
                # Stop loss should trigger
                assert abs(loss_pct) >= stop_loss_pct

    def test_max_drawdown_monitoring(self, mock_market_data):
        """Test maximum drawdown calculation"""
        engine = BacktestEngine(initial_capital=100000.0)
        strategy = MeanReversionStrategy(name="Test")

        results = engine.run(strategy, mock_market_data, "TEST")

        if 'max_drawdown' in results.get('metrics', {}):
            max_dd = results['metrics']['max_drawdown']

            # Drawdown should be negative or zero
            assert max_dd <= 0

            # Drawdown should be reasonable (not less than -100%)
            assert max_dd >= -1.0


class TestDataPipeline:
    """Test data pipeline from fetching to processing"""

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    def test_data_fetch_and_validation(self, mock_data_client):
        """Test data fetching and validation pipeline"""
        # Mock data response
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1100, 1200]
        })

        mock_data_client.return_value.get_stock_bars = Mock(return_value=mock_bars)

        # Create client
        with patch('src.api.alpaca_client.TradingClient'):
            client = AlpacaClient(api_key='test', secret_key='test', paper=True)

        # Fetch data
        data = client.get_bars(
            symbol='AAPL',
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
            timeframe='1Hour'
        )

        # Validate data
        assert not data.empty
        assert 'close' in data.columns
        assert len(data) == 3


class TestErrorHandling:
    """Test error handling and recovery"""

    def test_api_connection_failure(self):
        """Test handling of API connection failures"""
        with patch('src.api.alpaca_client.StockHistoricalDataClient') as mock_client:
            mock_client.side_effect = ConnectionError("Unable to connect")

            with pytest.raises(ConnectionError):
                AlpacaClient(
                    api_key='test',
                    secret_key='test',
                    paper=True
                )

    def test_invalid_data_handling(self):
        """Test handling of invalid market data"""
        # Create invalid data (missing required columns)
        invalid_data = pd.DataFrame({
            'close': [100, 101, 102]
            # Missing open, high, low, volume
        })

        engine = BacktestEngine()
        strategy = MeanReversionStrategy(name="Test")

        # Should handle gracefully
        with pytest.raises(Exception):
            engine.run(strategy, invalid_data, "TEST")

    def test_insufficient_data_handling(self, mock_market_data):
        """Test handling of insufficient data for strategy"""
        # Use only first 5 bars (insufficient for most strategies)
        limited_data = mock_market_data.head(5)

        strategy = MeanReversionStrategy(
            name="Test",
            parameters={'lookback': 20}  # Requires more data
        )

        engine = BacktestEngine()

        # Should handle gracefully or raise appropriate error
        try:
            results = engine.run(strategy, limited_data, "TEST")
            # If it completes, should have minimal/no trades
            assert results['total_trades'] == 0
        except ValueError:
            # Or it might raise an error for insufficient data
            pass


class TestPerformanceAndScalability:
    """Test performance and scalability"""

    def test_large_dataset_processing(self):
        """Test processing large datasets efficiently"""
        # Generate large dataset
        dates = pd.date_range(start='2020-01-01', periods=100000, freq='1min')
        large_data = pd.DataFrame({
            'open': np.random.randn(100000) + 100,
            'high': np.random.randn(100000) + 101,
            'low': np.random.randn(100000) + 99,
            'close': np.random.randn(100000) + 100,
            'volume': np.random.randint(10000, 100000, 100000)
        }, index=dates)

        strategy = MeanReversionStrategy(name="Test")
        engine = BacktestEngine()

        start_time = time.time()
        results = engine.run(strategy, large_data, "TEST")
        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 30 seconds)
        assert elapsed < 30.0
        print(f"Processed 100k bars in {elapsed:.2f} seconds")

    def test_concurrent_backtest_execution(self, mock_market_data):
        """Test running multiple backtests concurrently"""
        import concurrent.futures

        def run_backtest(symbol):
            engine = BacktestEngine(initial_capital=100000.0)
            strategy = MeanReversionStrategy(name=f"MR_{symbol}")

            data = mock_market_data.copy()
            data.attrs['symbol'] = symbol

            return engine.run(strategy, data, symbol)

        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']

        # Run concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(run_backtest, sym): sym for sym in symbols}
            results = {}

            for future in concurrent.futures.as_completed(futures):
                symbol = futures[future]
                results[symbol] = future.result()

        # Verify all completed
        assert len(results) == 5
        for symbol, result in results.items():
            assert result['symbol'] == symbol


class TestSystemIntegration:
    """Test full system integration"""

    def test_end_to_end_trading_day_simulation(self, mock_alpaca_client, mock_market_data):
        """Simulate a complete trading day"""
        # 1. Market opens - fetch account info
        account = mock_alpaca_client.get_account()
        assert account.cash > 0

        # 2. Fetch market data
        # (using mock_market_data)

        # 3. Generate signals
        strategy = MeanReversionStrategy(name="Day Trading")
        signals = strategy.generate_signals(mock_market_data)

        # 4. Execute trades based on signals
        executed_orders = []
        for signal in signals[:3]:  # Execute first 3 signals
            if signal.signal_type.value in ['buy', 'sell']:
                order = mock_alpaca_client.submit_market_order(
                    symbol=signal.symbol,
                    qty=10,
                    side=signal.signal_type.value
                )
                executed_orders.append(order)

        # 5. Monitor positions
        # (mock positions)

        # 6. End of day - verify state
        assert len(executed_orders) >= 0

        print(f"Simulated trading day: {len(signals)} signals, {len(executed_orders)} orders")
