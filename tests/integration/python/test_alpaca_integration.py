"""
Integration tests for Alpaca API client with mocking
Tests API interactions without making real network calls
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from src.api.alpaca_client import AlpacaClient


@pytest.fixture
def mock_credentials():
    """Mock API credentials"""
    return {
        'api_key': 'test_api_key',
        'secret_key': 'test_secret_key',
        'paper': True
    }


@pytest.fixture
def alpaca_client(mock_credentials):
    """Create AlpacaClient with mocked credentials"""
    with patch('src.api.alpaca_client.StockHistoricalDataClient'), \
         patch('src.api.alpaca_client.TradingClient'):
        client = AlpacaClient(
            api_key=mock_credentials['api_key'],
            secret_key=mock_credentials['secret_key'],
            paper=mock_credentials['paper']
        )
        return client


class TestAlpacaClientInitialization:
    """Test client initialization"""

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    @patch('src.api.alpaca_client.TradingClient')
    def test_initialization_paper_trading(self, mock_trading, mock_data, mock_credentials):
        """Test initialization with paper trading credentials"""
        client = AlpacaClient(
            api_key=mock_credentials['api_key'],
            secret_key=mock_credentials['secret_key'],
            paper=True
        )

        assert client.api_key == mock_credentials['api_key']
        assert client.paper is True

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    @patch('src.api.alpaca_client.TradingClient')
    def test_initialization_live_trading(self, mock_trading, mock_data):
        """Test initialization with live trading credentials"""
        client = AlpacaClient(
            api_key='live_key',
            secret_key='live_secret',
            paper=False
        )

        assert client.paper is False


class TestHistoricalDataFetching:
    """Test historical data fetching with mocks"""

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    def test_fetch_bars_single_symbol(self, mock_data_client, alpaca_client):
        """Test fetching bars for single symbol"""
        # Mock response
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2024-01-01', periods=3, freq='1h'))

        alpaca_client.data_client.get_stock_bars = Mock(return_value=mock_bars)

        # Fetch data
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 2)

        data = alpaca_client.get_bars(
            symbol='AAPL',
            start=start,
            end=end,
            timeframe='1Hour'
        )

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 3
        assert 'close' in data.columns
        alpaca_client.data_client.get_stock_bars.assert_called_once()

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    def test_fetch_bars_multiple_symbols(self, mock_data_client, alpaca_client):
        """Test fetching bars for multiple symbols"""
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame({
            'open': [100, 200],
            'high': [101, 201],
            'low': [99, 199],
            'close': [100.5, 200.5],
            'volume': [1000, 2000],
            'symbol': ['AAPL', 'GOOGL']
        }, index=pd.MultiIndex.from_tuples([
            ('AAPL', pd.Timestamp('2024-01-01 09:00')),
            ('GOOGL', pd.Timestamp('2024-01-01 09:00'))
        ]))

        alpaca_client.data_client.get_stock_bars = Mock(return_value=mock_bars)

        data = alpaca_client.get_bars(
            symbol=['AAPL', 'GOOGL'],
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
            timeframe='1Hour'
        )

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 2

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    def test_fetch_bars_empty_result(self, mock_data_client, alpaca_client):
        """Test handling empty data response"""
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame()

        alpaca_client.data_client.get_stock_bars = Mock(return_value=mock_bars)

        data = alpaca_client.get_bars(
            symbol='INVALID',
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
            timeframe='1Hour'
        )

        assert data.empty

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    def test_fetch_bars_api_error(self, mock_data_client, alpaca_client):
        """Test handling API errors"""
        alpaca_client.data_client.get_stock_bars = Mock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(Exception, match="API Error"):
            alpaca_client.get_bars(
                symbol='AAPL',
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
                timeframe='1Hour'
            )


class TestOrderExecution:
    """Test order execution with mocks"""

    @patch('src.api.alpaca_client.TradingClient')
    def test_submit_market_order_buy(self, mock_trading_client, alpaca_client):
        """Test submitting market buy order"""
        mock_order = MagicMock()
        mock_order.id = 'order_123'
        mock_order.symbol = 'AAPL'
        mock_order.qty = 10
        mock_order.side = OrderSide.BUY

        alpaca_client.trading_client.submit_order = Mock(return_value=mock_order)

        order = alpaca_client.submit_market_order(
            symbol='AAPL',
            qty=10,
            side='buy'
        )

        assert order.id == 'order_123'
        assert order.symbol == 'AAPL'
        alpaca_client.trading_client.submit_order.assert_called_once()

    @patch('src.api.alpaca_client.TradingClient')
    def test_submit_market_order_sell(self, mock_trading_client, alpaca_client):
        """Test submitting market sell order"""
        mock_order = MagicMock()
        mock_order.id = 'order_456'
        mock_order.symbol = 'GOOGL'
        mock_order.qty = 5
        mock_order.side = OrderSide.SELL

        alpaca_client.trading_client.submit_order = Mock(return_value=mock_order)

        order = alpaca_client.submit_market_order(
            symbol='GOOGL',
            qty=5,
            side='sell'
        )

        assert order.id == 'order_456'
        assert order.side == OrderSide.SELL

    @patch('src.api.alpaca_client.TradingClient')
    def test_submit_limit_order(self, mock_trading_client, alpaca_client):
        """Test submitting limit order"""
        mock_order = MagicMock()
        mock_order.id = 'order_789'
        mock_order.limit_price = 150.0

        alpaca_client.trading_client.submit_order = Mock(return_value=mock_order)

        order = alpaca_client.submit_limit_order(
            symbol='AAPL',
            qty=10,
            side='buy',
            limit_price=150.0
        )

        assert order.limit_price == 150.0

    @patch('src.api.alpaca_client.TradingClient')
    def test_submit_order_insufficient_funds(self, mock_trading_client, alpaca_client):
        """Test handling insufficient funds error"""
        alpaca_client.trading_client.submit_order = Mock(
            side_effect=Exception("Insufficient buying power")
        )

        with pytest.raises(Exception, match="Insufficient buying power"):
            alpaca_client.submit_market_order(
                symbol='AAPL',
                qty=10000,
                side='buy'
            )

    @patch('src.api.alpaca_client.TradingClient')
    def test_cancel_order(self, mock_trading_client, alpaca_client):
        """Test canceling an order"""
        alpaca_client.trading_client.cancel_order_by_id = Mock(return_value=True)

        result = alpaca_client.cancel_order('order_123')

        assert result is True
        alpaca_client.trading_client.cancel_order_by_id.assert_called_once_with('order_123')


class TestAccountManagement:
    """Test account management operations"""

    @patch('src.api.alpaca_client.TradingClient')
    def test_get_account_info(self, mock_trading_client, alpaca_client):
        """Test fetching account information"""
        mock_account = MagicMock()
        mock_account.cash = 100000.0
        mock_account.portfolio_value = 125000.0
        mock_account.buying_power = 200000.0

        alpaca_client.trading_client.get_account = Mock(return_value=mock_account)

        account = alpaca_client.get_account()

        assert account.cash == 100000.0
        assert account.portfolio_value == 125000.0
        assert account.buying_power == 200000.0

    @patch('src.api.alpaca_client.TradingClient')
    def test_get_positions(self, mock_trading_client, alpaca_client):
        """Test fetching all positions"""
        mock_position1 = MagicMock()
        mock_position1.symbol = 'AAPL'
        mock_position1.qty = 10
        mock_position1.current_price = 150.0

        mock_position2 = MagicMock()
        mock_position2.symbol = 'GOOGL'
        mock_position2.qty = 5
        mock_position2.current_price = 2800.0

        alpaca_client.trading_client.get_all_positions = Mock(
            return_value=[mock_position1, mock_position2]
        )

        positions = alpaca_client.get_positions()

        assert len(positions) == 2
        assert positions[0].symbol == 'AAPL'
        assert positions[1].symbol == 'GOOGL'

    @patch('src.api.alpaca_client.TradingClient')
    def test_get_position_single_symbol(self, mock_trading_client, alpaca_client):
        """Test fetching position for specific symbol"""
        mock_position = MagicMock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 145.0

        alpaca_client.trading_client.get_open_position = Mock(return_value=mock_position)

        position = alpaca_client.get_position('AAPL')

        assert position.symbol == 'AAPL'
        assert position.qty == 10


class TestRateLimiting:
    """Test rate limiting behavior"""

    @patch('src.api.alpaca_client.TradingClient')
    def test_rate_limit_handling(self, mock_trading_client, alpaca_client):
        """Test handling of rate limit errors"""
        alpaca_client.trading_client.submit_order = Mock(
            side_effect=Exception("429 Too Many Requests")
        )

        with pytest.raises(Exception, match="429 Too Many Requests"):
            alpaca_client.submit_market_order(
                symbol='AAPL',
                qty=10,
                side='buy'
            )


class TestDataValidation:
    """Test data validation and error handling"""

    @patch('src.api.alpaca_client.TradingClient')
    def test_invalid_symbol(self, mock_trading_client, alpaca_client):
        """Test handling of invalid symbol"""
        alpaca_client.trading_client.submit_order = Mock(
            side_effect=Exception("Invalid symbol")
        )

        with pytest.raises(Exception, match="Invalid symbol"):
            alpaca_client.submit_market_order(
                symbol='INVALID_SYMBOL_123',
                qty=10,
                side='buy'
            )

    def test_invalid_quantity_negative(self, alpaca_client):
        """Test handling of negative quantity"""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            alpaca_client.validate_order_params(
                symbol='AAPL',
                qty=-10,
                side='buy'
            )

    def test_invalid_quantity_zero(self, alpaca_client):
        """Test handling of zero quantity"""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            alpaca_client.validate_order_params(
                symbol='AAPL',
                qty=0,
                side='buy'
            )

    def test_invalid_side(self, alpaca_client):
        """Test handling of invalid order side"""
        with pytest.raises(ValueError, match="Side must be 'buy' or 'sell'"):
            alpaca_client.validate_order_params(
                symbol='AAPL',
                qty=10,
                side='invalid_side'
            )


class TestConnectionHandling:
    """Test connection and reconnection logic"""

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    @patch('src.api.alpaca_client.TradingClient')
    def test_connection_timeout(self, mock_trading, mock_data):
        """Test handling of connection timeout"""
        mock_data.side_effect = TimeoutError("Connection timeout")

        with pytest.raises(TimeoutError):
            AlpacaClient(
                api_key='test_key',
                secret_key='test_secret',
                paper=True
            )

    @patch('src.api.alpaca_client.TradingClient')
    def test_network_error_handling(self, mock_trading_client, alpaca_client):
        """Test handling of network errors"""
        alpaca_client.trading_client.get_account = Mock(
            side_effect=ConnectionError("Network error")
        )

        with pytest.raises(ConnectionError):
            alpaca_client.get_account()


class TestBatchOperations:
    """Test batch operations"""

    @patch('src.api.alpaca_client.TradingClient')
    def test_cancel_all_orders(self, mock_trading_client, alpaca_client):
        """Test canceling all open orders"""
        alpaca_client.trading_client.cancel_orders = Mock(return_value=True)

        result = alpaca_client.cancel_all_orders()

        assert result is True
        alpaca_client.trading_client.cancel_orders.assert_called_once()

    @patch('src.api.alpaca_client.TradingClient')
    def test_close_all_positions(self, mock_trading_client, alpaca_client):
        """Test closing all positions"""
        alpaca_client.trading_client.close_all_positions = Mock(return_value=True)

        result = alpaca_client.close_all_positions()

        assert result is True
        alpaca_client.trading_client.close_all_positions.assert_called_once()


class TestWebSocketIntegration:
    """Test WebSocket streaming integration"""

    @patch('src.api.alpaca_client.StockDataStream')
    def test_subscribe_to_trades(self, mock_stream, alpaca_client):
        """Test subscribing to trade updates"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance

        alpaca_client.subscribe_trades(['AAPL', 'GOOGL'])

        # Verify subscription was called
        assert mock_stream_instance.subscribe_trades.called

    @patch('src.api.alpaca_client.StockDataStream')
    def test_subscribe_to_quotes(self, mock_stream, alpaca_client):
        """Test subscribing to quote updates"""
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance

        alpaca_client.subscribe_quotes(['AAPL'])

        assert mock_stream_instance.subscribe_quotes.called

    @patch('src.api.alpaca_client.StockDataStream')
    def test_websocket_reconnection(self, mock_stream, alpaca_client):
        """Test WebSocket automatic reconnection"""
        mock_stream_instance = MagicMock()
        mock_stream_instance.run = Mock(side_effect=ConnectionError("Disconnected"))

        with pytest.raises(ConnectionError):
            alpaca_client.start_streaming()


class TestCachingBehavior:
    """Test caching of data and requests"""

    @patch('src.api.alpaca_client.StockHistoricalDataClient')
    def test_cache_hit(self, mock_data_client, alpaca_client):
        """Test cache hit for repeated requests"""
        mock_bars = MagicMock()
        mock_bars.df = pd.DataFrame({
            'close': [100, 101, 102]
        })

        alpaca_client.data_client.get_stock_bars = Mock(return_value=mock_bars)

        # First request
        data1 = alpaca_client.get_bars(
            symbol='AAPL',
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
            timeframe='1Hour',
            use_cache=True
        )

        # Second request (should use cache)
        data2 = alpaca_client.get_bars(
            symbol='AAPL',
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
            timeframe='1Hour',
            use_cache=True
        )

        # Should only call API once
        assert alpaca_client.data_client.get_stock_bars.call_count == 1
