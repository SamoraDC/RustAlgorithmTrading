"""
Enhanced Alpaca API Paper Trading Integration.

Provides comprehensive paper trading functionality with:
  - Portfolio tracking and P&L calculation
  - Order management with validation
  - Position tracking with risk metrics
  - Historical data fetching
  - Real-time market data streaming
"""

import os
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.live import StockDataStream

from loguru import logger


class OrderType(str, Enum):
    """Order types supported."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_equity: Decimal
    cash: Decimal
    portfolio_value: Decimal
    buying_power: Decimal
    total_pl: Decimal
    total_pl_pct: Decimal
    day_pl: Decimal = Decimal("0.0")
    day_pl_pct: Decimal = Decimal("0.0")
    positions_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PositionInfo:
    """Extended position information."""
    symbol: str
    qty: Decimal
    avg_entry_price: Decimal
    current_price: Decimal
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pl: Decimal
    unrealized_pl_pct: Decimal
    side: str  # "long" or "short"
    timestamp: datetime = field(default_factory=datetime.now)


class AlpacaPaperTrading:
    """
    Enhanced Alpaca paper trading client with comprehensive functionality.

    Features:
      - Safe paper trading operations
      - Portfolio and position tracking
      - Historical and real-time data
      - Order validation and management
      - Performance metrics calculation

    Example:
        >>> client = AlpacaPaperTrading()
        >>> client.connect()
        >>> account = client.get_account_info()
        >>> print(f"Buying power: ${account['buying_power']}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
        validate_credentials: bool = True
    ):
        """
        Initialize Alpaca paper trading client.

        Args:
            api_key: Alpaca API key (defaults to env variable)
            secret_key: Alpaca secret key (defaults to env variable)
            paper: Whether to use paper trading (MUST be True for safety)
            validate_credentials: Whether to validate credentials on init
        """
        # Force paper trading for safety
        if not paper:
            logger.warning("🚨 Live trading disabled for safety. Using paper trading.")
            paper = True

        load_dotenv()

        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")

        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca credentials not found. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY environment variables."
            )

        self.trading_client: Optional[TradingClient] = None
        self.data_client: Optional[StockHistoricalDataClient] = None
        self.stream_client: Optional[StockDataStream] = None
        self._connected = False

        logger.info(f"AlpacaPaperTrading initialized (paper={paper})")
        logger.info(f"API Key: {self.api_key[:8]}...")

        if validate_credentials:
            self.connect()

    def connect(self) -> bool:
        """
        Connect to Alpaca API and validate credentials.

        Returns:
            True if connection successful

        Raises:
            RuntimeError: If connection fails
        """
        try:
            # Initialize trading client
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=True  # Always paper trading
            )

            # Initialize data client
            self.data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key
            )

            # Validate by fetching account
            account = self.trading_client.get_account()

            self._connected = True
            logger.info("✓ Connected to Alpaca API")
            logger.info(f"  Account status: {account.status}")
            logger.info(f"  Buying power: ${float(account.buying_power):,.2f}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Alpaca API: {e}")
            raise RuntimeError(f"Alpaca connection failed: {e}") from e

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get current account information.

        Returns:
            Dictionary with account details
        """
        self._ensure_connected()

        try:
            account = self.trading_client.get_account()

            return {
                "status": account.status,
                "cash": Decimal(str(account.cash)),
                "portfolio_value": Decimal(str(account.portfolio_value)),
                "buying_power": Decimal(str(account.buying_power)),
                "equity": Decimal(str(account.equity)),
                "long_market_value": Decimal(str(account.long_market_value)),
                "short_market_value": Decimal(str(account.short_market_value)),
                "initial_margin": Decimal(str(account.initial_margin)),
                "maintenance_margin": Decimal(str(account.maintenance_margin)),
                "daytrade_count": account.daytrade_count,
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_blocked": account.account_blocked,
                "created_at": account.created_at,
            }
        except Exception as e:
            logger.error(f"Failed to fetch account info: {e}")
            raise

    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """
        Calculate comprehensive portfolio metrics.

        Returns:
            PortfolioMetrics object with performance data
        """
        self._ensure_connected()

        try:
            account = self.trading_client.get_account()
            positions = self.trading_client.get_all_positions()

            # Calculate metrics
            equity = Decimal(str(account.equity))
            cash = Decimal(str(account.cash))
            portfolio_value = Decimal(str(account.portfolio_value))
            buying_power = Decimal(str(account.buying_power))

            # P&L calculation
            cost_basis = sum(
                Decimal(str(p.qty)) * Decimal(str(p.avg_entry_price))
                for p in positions
            )
            current_value = sum(Decimal(str(p.market_value)) for p in positions)
            total_pl = current_value - cost_basis if cost_basis > 0 else Decimal("0.0")
            total_pl_pct = (total_pl / cost_basis * 100) if cost_basis > 0 else Decimal("0.0")

            return PortfolioMetrics(
                total_equity=equity,
                cash=cash,
                portfolio_value=portfolio_value,
                buying_power=buying_power,
                total_pl=total_pl,
                total_pl_pct=total_pl_pct,
                positions_count=len(positions)
            )

        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            raise

    def get_positions(self) -> List[PositionInfo]:
        """
        Get all current positions with extended information.

        Returns:
            List of PositionInfo objects
        """
        self._ensure_connected()

        try:
            positions = self.trading_client.get_all_positions()

            position_list = []
            for pos in positions:
                qty = Decimal(str(pos.qty))
                avg_entry = Decimal(str(pos.avg_entry_price))
                current_price = Decimal(str(pos.current_price))
                market_value = Decimal(str(pos.market_value))
                cost_basis = qty * avg_entry
                unrealized_pl = Decimal(str(pos.unrealized_pl))
                unrealized_pl_pct = Decimal(str(pos.unrealized_plpc)) * 100

                position_list.append(PositionInfo(
                    symbol=pos.symbol,
                    qty=qty,
                    avg_entry_price=avg_entry,
                    current_price=current_price,
                    market_value=market_value,
                    cost_basis=cost_basis,
                    unrealized_pl=unrealized_pl,
                    unrealized_pl_pct=unrealized_pl_pct,
                    side="long" if float(qty) > 0 else "short"
                ))

            return position_list

        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise

    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place an order with validation.

        Args:
            symbol: Stock symbol
            qty: Quantity to trade
            side: "buy" or "sell"
            order_type: Type of order
            limit_price: Limit price (for limit/stop-limit orders)
            stop_price: Stop price (for stop/stop-limit orders)
            time_in_force: "day", "gtc", "ioc", or "fok"
            validate_only: If True, only validate without submitting

        Returns:
            Order details dictionary
        """
        self._ensure_connected()

        # Validate parameters
        if qty <= 0:
            raise ValueError(f"Quantity must be positive: {qty}")

        if side.lower() not in ["buy", "sell"]:
            raise ValueError(f"Side must be 'buy' or 'sell': {side}")

        if order_type == OrderType.LIMIT and limit_price is None:
            raise ValueError("Limit price required for limit orders")

        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and stop_price is None:
            raise ValueError("Stop price required for stop orders")

        try:
            # Convert parameters
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif_map = {
                "day": TimeInForce.DAY,
                "gtc": TimeInForce.GTC,
                "ioc": TimeInForce.IOC,
                "fok": TimeInForce.FOK,
            }
            tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

            # Create order request based on type
            if order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=tif
                )
            elif order_type == OrderType.LIMIT:
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=tif,
                    limit_price=limit_price
                )
            elif order_type == OrderType.STOP:
                order_request = StopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=tif,
                    stop_price=stop_price
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            if validate_only:
                logger.info(f"✓ Order validation passed: {side} {qty} {symbol} @ {order_type.value}")
                return {
                    "validated": True,
                    "symbol": symbol,
                    "qty": qty,
                    "side": side,
                    "type": order_type.value
                }

            # Submit order
            order = self.trading_client.submit_order(order_request)

            logger.info(f"✓ Order placed: {side} {qty} {symbol}")
            logger.info(f"  Order ID: {order.id}")
            logger.info(f"  Status: {order.status.value}")

            return {
                "id": str(order.id),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "type": order.type.value,
                "status": order.status.value,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0.0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
            }

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise

    def get_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get orders with optional filtering.

        Args:
            status: Filter by status ("open", "closed", "all")
            limit: Maximum number of orders to return
            symbols: Filter by symbols

        Returns:
            List of order dictionaries
        """
        self._ensure_connected()

        try:
            # Build request
            request_params = GetOrdersRequest(
                status=QueryOrderStatus.OPEN if status == "open" else QueryOrderStatus.CLOSED if status == "closed" else QueryOrderStatus.ALL,
                limit=limit,
                symbols=symbols
            )

            orders = self.trading_client.get_orders(request_params)

            return [
                {
                    "id": str(order.id),
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side.value,
                    "type": order.type.value,
                    "status": order.status.value,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0.0,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "created_at": order.created_at,
                    "updated_at": order.updated_at,
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Failed to fetch orders: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successfully cancelled
        """
        self._ensure_connected()

        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"✓ Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders.

        Returns:
            Number of orders cancelled
        """
        self._ensure_connected()

        try:
            cancelled = self.trading_client.cancel_orders()
            count = len(cancelled) if cancelled else 0
            logger.info(f"✓ Cancelled {count} orders")
            return count
        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            raise

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close a position by selling/buying all shares.

        Args:
            symbol: Symbol to close

        Returns:
            Order details
        """
        self._ensure_connected()

        try:
            order = self.trading_client.close_position(symbol)
            logger.info(f"✓ Position {symbol} closed")

            return {
                "id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side.value,
                "status": order.status.value,
            }
        except Exception as e:
            logger.error(f"Failed to close position {symbol}: {e}")
            raise

    def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Close all open positions.

        Returns:
            List of close order details
        """
        self._ensure_connected()

        try:
            orders = self.trading_client.close_all_positions(cancel_orders=True)
            logger.info(f"✓ Closed {len(orders)} positions")

            return [
                {
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side.value,
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            raise

    def get_latest_quote(self, symbol: str) -> Dict[str, float]:
        """
        Get latest quote for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with bid, ask, and mid prices
        """
        self._ensure_connected()

        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            quote = quotes[symbol]

            return {
                "bid_price": float(quote.bid_price),
                "ask_price": float(quote.ask_price),
                "mid_price": (float(quote.bid_price) + float(quote.ask_price)) / 2.0,
                "bid_size": float(quote.bid_size),
                "ask_size": float(quote.ask_size),
                "timestamp": quote.timestamp,
            }
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            raise

    def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: TimeFrame = TimeFrame.Day
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical price bars.

        Args:
            symbol: Stock symbol
            start: Start datetime
            end: End datetime
            timeframe: Bar timeframe

        Returns:
            List of bar dictionaries
        """
        self._ensure_connected()

        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=timeframe,
                start=start,
                end=end
            )

            bars = self.data_client.get_stock_bars(request_params)
            bars_list = bars.data.get(symbol, [])

            logger.info(f"Fetched {len(bars_list)} bars for {symbol}")

            return [
                {
                    "timestamp": bar.timestamp,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": float(bar.volume),
                }
                for bar in bars_list
            ]

        except Exception as e:
            logger.error(f"Failed to fetch historical bars for {symbol}: {e}")
            raise

    def _ensure_connected(self):
        """Ensure client is connected."""
        if not self._connected or self.trading_client is None:
            raise RuntimeError(
                "Client not connected. Call connect() first."
            )


# Convenience function for testing
def test_alpaca_paper_trading():
    """Test Alpaca paper trading functionality."""
    logger.info("Testing Alpaca paper trading integration...")

    try:
        # Initialize client
        client = AlpacaPaperTrading()

        # Get account info
        account = client.get_account_info()
        logger.info(f"✓ Account info: ${account['buying_power']} buying power")

        # Get portfolio metrics
        metrics = client.get_portfolio_metrics()
        logger.info(f"✓ Portfolio: ${metrics.total_equity} equity, {metrics.positions_count} positions")

        # Get positions
        positions = client.get_positions()
        logger.info(f"✓ Positions: {len(positions)} open")

        # Validate order (don't actually place)
        order = client.place_order(
            symbol="AAPL",
            qty=1,
            side="buy",
            order_type=OrderType.LIMIT,
            limit_price=150.0,
            validate_only=True
        )
        logger.info(f"✓ Order validation: {order['validated']}")

        # Get historical data
        bars = client.get_historical_bars(
            symbol="AAPL",
            start=datetime.now() - timedelta(days=5),
            end=datetime.now(),
            timeframe=TimeFrame.Day
        )
        logger.info(f"✓ Historical data: {len(bars)} bars fetched")

        logger.info("✅ All Alpaca paper trading tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Alpaca paper trading test failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run tests
    success = test_alpaca_paper_trading()
    sys.exit(0 if success else 1)
