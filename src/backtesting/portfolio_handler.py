"""
Portfolio handler for position and cash management during backtesting.
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from src.models.portfolio import Portfolio, Position
from src.models.events import SignalEvent, OrderEvent, FillEvent


class PortfolioHandler:
    """
    Manages portfolio state during backtesting.

    Tracks positions, cash, and equity over time. Generates orders based on
    trading signals and position sizing rules.
    """

    def __init__(
        self,
        initial_capital: float,
        position_sizer: Optional['PositionSizer'] = None,
        data_handler: Optional['HistoricalDataHandler'] = None,
    ):
        """
        Initialize portfolio handler.

        Args:
            initial_capital: Starting capital
            position_sizer: Position sizing strategy (defaults to FixedAmountSizer)
            data_handler: Data handler for getting current prices

        Raises:
            TypeError: If initial_capital is not a number
            ValueError: If initial_capital is not positive
        """
        # Validate initial_capital
        if not isinstance(initial_capital, (int, float)):
            raise TypeError(f"initial_capital must be a number, got {type(initial_capital).__name__}")

        if initial_capital <= 0:
            raise ValueError(f"initial_capital must be positive, got {initial_capital}")

        if position_sizer is not None and not isinstance(position_sizer, PositionSizer):
            raise TypeError(f"position_sizer must be a PositionSizer instance or None, got {type(position_sizer).__name__}")

        self.initial_capital = initial_capital
        self.data_handler = data_handler
        self.position_sizer = position_sizer or FixedAmountSizer(10000.0)

        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            cash=initial_capital,
        )

        # Track equity curve
        self.equity_curve: List[Dict] = []
        self.holdings_history: List[Dict] = []

        # RACE FIX: Track reserved cash for pending orders in the same bar
        self.reserved_cash: float = 0.0

        logger.info(f"Initialized PortfolioHandler with ${initial_capital:,.2f}")

    def update_timeindex(self, timestamp: datetime):
        """
        Update portfolio timestamp and record equity snapshot.

        Args:
            timestamp: Current timestamp

        Raises:
            TypeError: If timestamp is not a datetime
        """
        if not isinstance(timestamp, datetime):
            raise TypeError(f"timestamp must be a datetime, got {type(timestamp).__name__}")

        self.portfolio.timestamp = timestamp

        # Record equity curve point
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.portfolio.equity,
            'cash': self.portfolio.cash,
            'total_pnl': self.portfolio.total_pnl,
            'return_pct': self.portfolio.return_percentage,
        })

    def generate_orders(self, signal: SignalEvent) -> List[OrderEvent]:
        """
        Generate orders from trading signal with race condition protection.

        CRITICAL FIX: EXIT signals bypass position sizing and always close full position.

        This method prevents cash overdraft when multiple orders are generated
        in the same bar by tracking reserved cash for pending orders.

        Args:
            signal: Trading signal (LONG/SHORT/EXIT)

        Returns:
            List of order events (may be empty if insufficient cash or no position)
        """
        orders = []

        # ENHANCED LOGGING: Log incoming signal details
        logger.debug(
            f"📥 Signal received: {signal.signal_type} for {signal.symbol}, "
            f"confidence={signal.strength:.2f}, strategy={signal.strategy_id}"
        )

        # Get current market price
        current_price = None
        if self.data_handler:
            latest_bar = self.data_handler.get_latest_bar(signal.symbol)
            if latest_bar:
                current_price = latest_bar.close
                logger.debug(f"📊 Current market price for {signal.symbol}: ${current_price:.2f}")
            else:
                logger.warning(f"⚠️ No market data available for {signal.symbol}")
        else:
            logger.warning(f"⚠️ No data handler configured for price lookup")

        # Get current position
        current_position = self.portfolio.positions.get(signal.symbol)
        current_quantity = current_position.quantity if current_position else 0
        logger.debug(
            f"💼 Current position: {current_quantity} shares of {signal.symbol} "
            f"(value: ${abs(current_quantity * (current_price or 0)):,.2f})"
        )

        # ================================
        # CRITICAL FIX: Handle EXIT signals FIRST
        # ================================
        # EXIT signals should ALWAYS close the full position, bypassing position sizing
        # This ensures proper exit execution regardless of position sizer logic
        if signal.signal_type == 'EXIT':
            if current_quantity == 0:
                logger.debug(f"🚫 EXIT signal for {signal.symbol} but no position to close (skipping)")
                return orders

            # Close the entire position (negate current quantity)
            order_quantity = -current_quantity
            logger.info(
                f"🚪 EXIT signal: closing {abs(order_quantity)} shares of {signal.symbol} "
                f"(current: {current_quantity} → target: 0)"
            )

            # Create SELL order to exit position
            order = OrderEvent(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                order_type='MKT',
                quantity=abs(order_quantity),
                direction='SELL',  # Always SELL for EXIT
            )

            orders.append(order)

            logger.info(
                f"✅ EXIT ORDER: SELL {order.quantity} {signal.symbol} @ market | "
                f"Expected proceeds: ${abs(order_quantity) * (current_price or 0):,.2f}"
            )

            return orders

        # ================================
        # Handle LONG and SHORT signals through position sizer
        # ================================

        # RACE FIX: Calculate available cash minus reserved cash
        available_cash = self.portfolio.cash - self.reserved_cash

        logger.debug(
            f"💰 Cash status: portfolio=${self.portfolio.cash:,.2f}, "
            f"reserved=${self.reserved_cash:,.2f}, available=${available_cash:,.2f}"
        )

        if available_cash < 0:
            logger.warning(
                f"❌ Available cash is negative: ${available_cash:,.2f} "
                f"(portfolio: ${self.portfolio.cash:,.2f}, reserved: ${self.reserved_cash:,.2f}) - skipping order"
            )
            return orders

        # Calculate target position based on signal using position sizer
        target_quantity = self.position_sizer.calculate_position_size(
            signal=signal,
            portfolio=self.portfolio,
            current_price=current_price,
        )

        logger.debug(
            f"🎯 Position sizing: signal={signal.signal_type}, current={current_quantity}, "
            f"target={target_quantity}, delta={target_quantity - current_quantity}"
        )

        # Calculate order quantity needed to reach target
        order_quantity = target_quantity - current_quantity

        if order_quantity == 0:
            logger.debug(f"⏸️ No order needed: target position already achieved for {signal.symbol}")
            return orders

        # RACE FIX: For BUY orders, validate cash and reserve funds
        if order_quantity > 0:  # BUY order (opening long or adding to position)
            if current_price is None or current_price <= 0:
                logger.warning(f"❌ Invalid price for {signal.symbol}, cannot generate BUY order")
                return orders

            # Calculate estimated cost (position + commission + slippage)
            position_cost = abs(order_quantity) * current_price
            estimated_commission = position_cost * 0.001  # 0.1% commission
            estimated_slippage = position_cost * 0.0005  # 0.05% slippage
            total_estimated_cost = position_cost + estimated_commission + estimated_slippage

            # Check if we have enough available cash
            if total_estimated_cost > available_cash:
                # Calculate maximum affordable quantity
                max_affordable_value = available_cash / (1 + 0.001 + 0.0005)  # Adjust for fees
                max_affordable_quantity = int(max_affordable_value / current_price)

                if max_affordable_quantity <= 0:
                    logger.info(
                        f"💸 Insufficient cash for {signal.symbol}: "
                        f"need ${total_estimated_cost:,.2f}, have ${available_cash:,.2f} - skipping order"
                    )
                    return orders

                # Adjust order quantity to what we can afford
                logger.info(
                    f"⚠️ Reducing order for {signal.symbol} from {order_quantity} to {max_affordable_quantity} shares "
                    f"(cash constraint: ${available_cash:,.2f} available)"
                )
                order_quantity = max_affordable_quantity

                # Recalculate costs with adjusted quantity
                position_cost = abs(order_quantity) * current_price
                estimated_commission = position_cost * 0.001
                estimated_slippage = position_cost * 0.0005
                total_estimated_cost = position_cost + estimated_commission + estimated_slippage

            # RACE FIX: Reserve cash for this pending BUY order
            self.reserved_cash += total_estimated_cost
            logger.debug(
                f"💰 Reserved ${total_estimated_cost:,.2f} for {signal.symbol} BUY order "
                f"(total reserved: ${self.reserved_cash:,.2f})"
            )
        else:
            # SELL order - closing or reducing position, no cash needed
            logger.debug(
                f"💵 SELL order for {abs(order_quantity)} shares of {signal.symbol} "
                f"(expected proceeds: ~${abs(order_quantity) * (current_price or 0):,.2f})"
            )

        # Create order
        order = OrderEvent(
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            order_type='MKT',
            quantity=abs(order_quantity),
            direction='BUY' if order_quantity > 0 else 'SELL',
        )

        orders.append(order)

        # ENHANCED LOGGING: Detailed order generation summary
        logger.info(
            f"✅ ORDER GENERATED: {order.direction} {order.quantity} {signal.symbol} @ market | "
            f"Signal: {signal.signal_type}, Position: {current_quantity}→{current_quantity + order_quantity}, "
            f"Cash: ${self.portfolio.cash:,.2f}"
        )

        return orders

    def update_fill(self, fill: FillEvent):
        """
        Update portfolio with fill event.

        Args:
            fill: Fill event

        Raises:
            ValueError: If fill would result in negative cash
        """
        # CRITICAL FIX: Validate that we have enough cash BEFORE updating
        position_cost = abs(fill.quantity) * fill.fill_price
        total_cost = position_cost + fill.commission

        # Get position before fill
        old_position = self.portfolio.positions.get(fill.symbol)
        old_quantity = old_position.quantity if old_position else 0

        # ENHANCED LOGGING: Fill event details
        logger.debug(
            f"📦 FILL RECEIVED: {fill.direction} {fill.quantity} {fill.symbol} @ ${fill.fill_price:.2f} | "
            f"Cost: ${position_cost:,.2f}, Commission: ${fill.commission:.2f}, Total: ${total_cost:,.2f}"
        )

        # For BUY orders, check if we have enough cash
        if fill.quantity > 0:  # BUY (positive quantity means adding shares)
            if total_cost > self.portfolio.cash:
                error_msg = (
                    f"❌ Insufficient cash for fill: need ${total_cost:,.2f} "
                    f"(position: ${position_cost:,.2f} + commission: ${fill.commission:,.2f}), "
                    f"but only have ${self.portfolio.cash:,.2f}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        # Update position
        self.portfolio.update_position(
            symbol=fill.symbol,
            quantity=fill.quantity,
            price=fill.fill_price,
        )

        # Deduct commission
        self.portfolio.cash -= fill.commission

        # Final safety check
        if self.portfolio.cash < 0:
            error_msg = (
                f"❌ Portfolio cash went negative: ${self.portfolio.cash:,.2f} "
                f"after processing {fill.quantity} {fill.symbol} @ ${fill.fill_price:,.2f}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Record holdings
        self.holdings_history.append({
            'timestamp': fill.timestamp,
            'symbol': fill.symbol,
            'quantity': fill.quantity,
            'price': fill.fill_price,
            'commission': fill.commission,
            'cash': self.portfolio.cash,
            'equity': self.portfolio.equity,
        })

        # Log final position state
        new_position = self.portfolio.positions.get(fill.symbol)
        new_quantity = new_position.quantity if new_position else 0
        logger.debug(
            f"📊 Position updated: {fill.symbol} {old_quantity}→{new_quantity} shares, "
            f"Cash: ${self.portfolio.cash:,.2f}, Equity: ${self.portfolio.equity:,.2f}"
        )

    def get_equity_curve(self) -> pd.DataFrame:
        """Get equity curve as DataFrame."""
        return pd.DataFrame(self.equity_curve)

    def get_holdings(self) -> pd.DataFrame:
        """Get holdings history as DataFrame."""
        return pd.DataFrame(self.holdings_history)

    def clear_reserved_cash(self):
        """
        Clear reserved cash after all orders in a bar have been processed.

        This should be called by the engine after processing all fills for a bar
        to reset the reservation system for the next bar.
        """
        if self.reserved_cash > 0:
            logger.debug(f"🔄 Clearing reserved cash: ${self.reserved_cash:,.2f}")
            self.reserved_cash = 0.0


class PositionSizer:
    """Base class for position sizing strategies."""

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio, current_price: Optional[float] = None
    ) -> int:
        """
        Calculate target position size.

        Args:
            signal: Trading signal
            portfolio: Current portfolio state
            current_price: Current market price for the symbol (optional)

        Returns:
            Target position quantity (positive for long, negative for short, 0 for exit)
        """
        raise NotImplementedError


class FixedAmountSizer(PositionSizer):
    """Fixed notional amount position sizer."""

    def __init__(self, amount: float):
        """
        Initialize sizer.

        Args:
            amount: Fixed dollar amount per position

        Raises:
            TypeError: If amount is not a number
            ValueError: If amount is not positive
        """
        if not isinstance(amount, (int, float)):
            raise TypeError(f"amount must be a number, got {type(amount).__name__}")

        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")

        self.amount = amount

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio, current_price: Optional[float] = None
    ) -> int:
        """
        Calculate position size based on fixed amount.

        CRITICAL FIX: For EXIT signals, return 0 (generate_orders will handle closing).

        Args:
            signal: Trading signal
            portfolio: Current portfolio state
            current_price: Current market price for the symbol

        Returns:
            Target position quantity
        """
        # CRITICAL FIX: EXIT signals should return 0 target (full close handled by generate_orders)
        if signal.signal_type == 'EXIT':
            return 0

        # Get current price from parameter, position, or fail safely with 0
        if current_price is None:
            current_position = portfolio.positions.get(signal.symbol)
            if current_position:
                price = current_position.current_price
            else:
                logger.warning(
                    f"No current price available for {signal.symbol}, cannot calculate position size"
                )
                return 0
        else:
            price = current_price

        if price <= 0:
            logger.warning(f"Invalid price {price} for {signal.symbol}")
            return 0

        # CRITICAL FIX: Account for commission, slippage, and market impact
        # Commission: 0.1% (10 bps)
        # Slippage: 0.5% (50 bps) average
        # Market impact: variable based on notional
        # Safety buffer: 0.5% for rounding and price movements
        # Total buffer: ~2% to be safe

        # Calculate target shares based on position size
        target_shares = int(self.amount / price) if price > 0 else 0

        # Calculate worst-case cost including all fees
        # Slippage can add up to 0.5%, so effective price is price * 1.005
        # Commission is 0.1% of notional
        # Add 0.5% safety margin
        cost_multiplier = 1.016  # 1.005 (slippage) + 0.001 (commission) + 0.010 (safety) = 1.6% total buffer

        # Calculate how many shares we can afford with the buffer
        max_affordable_shares = int(portfolio.cash / (price * cost_multiplier))

        # Use the minimum to respect cash constraints
        shares = min(target_shares, max_affordable_shares)

        # Double-check: ensure total cost doesn't exceed available cash
        estimated_fill_price = price * 1.005  # Account for slippage
        estimated_commission = shares * estimated_fill_price * 0.001
        total_estimated_cost = (shares * estimated_fill_price) + estimated_commission

        if total_estimated_cost > portfolio.cash:
            # Emergency recalculation with even more conservative buffer
            shares = int(portfolio.cash / (price * 1.020))  # 2% safety margin
            logger.debug(
                f"Applied emergency position size reduction to {shares} shares "
                f"(cash: ${portfolio.cash:,.2f}, estimated cost: ${total_estimated_cost:,.2f})"
            )

        if signal.signal_type == 'LONG':
            return shares
        elif signal.signal_type == 'SHORT':
            return -shares
        else:
            return 0


class PercentageOfEquitySizer(PositionSizer):
    """Position sizer based on percentage of portfolio equity."""

    def __init__(self, percentage: float):
        """
        Initialize sizer.

        Args:
            percentage: Percentage of equity to allocate (0-1)

        Raises:
            TypeError: If percentage is not a number
            ValueError: If percentage is not in range (0, 1]
        """
        if not isinstance(percentage, (int, float)):
            raise TypeError(f"percentage must be a number, got {type(percentage).__name__}")

        if not 0 < percentage <= 1:
            raise ValueError(f"percentage must be in range (0, 1], got {percentage}")

        self.percentage = percentage

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio, current_price: Optional[float] = None
    ) -> int:
        """
        Calculate position size based on equity percentage.

        CRITICAL FIX: For EXIT signals, return 0 (generate_orders handles closing).

        Args:
            signal: Trading signal
            portfolio: Current portfolio state
            current_price: Current market price for the symbol

        Returns:
            Target position quantity
        """
        # CRITICAL FIX: EXIT signals should return 0
        if signal.signal_type == 'EXIT':
            return 0

        # Get current price from parameter, position, or fail safely with 0
        if current_price is None:
            current_position = portfolio.positions.get(signal.symbol)
            if current_position:
                price = current_position.current_price
            else:
                logger.warning(
                    f"No current price available for {signal.symbol}, cannot calculate position size"
                )
                return 0
        else:
            price = current_price

        if price <= 0:
            logger.warning(f"Invalid price {price} for {signal.symbol}")
            return 0

        # Calculate target amount based on equity percentage
        amount = portfolio.equity * self.percentage
        target_shares = int(amount / price) if price > 0 else 0

        # CRITICAL FIX: Account for all costs with proper buffer
        cost_multiplier = 1.016  # Slippage + Commission + Safety (1.6% total)
        max_affordable_shares = int(portfolio.cash / (price * cost_multiplier))

        # Use the minimum to respect cash constraints
        shares = min(target_shares, max_affordable_shares)

        # Double-check with estimated costs
        estimated_fill_price = price * 1.005
        estimated_commission = shares * estimated_fill_price * 0.001
        total_estimated_cost = (shares * estimated_fill_price) + estimated_commission

        if total_estimated_cost > portfolio.cash:
            shares = int(portfolio.cash / (price * 1.020))
            logger.debug(
                f"Applied emergency position size reduction to {shares} shares"
            )

        if signal.signal_type == 'LONG':
            return shares
        elif signal.signal_type == 'SHORT':
            return -shares
        else:
            return 0


class KellyPositionSizer(PositionSizer):
    """Kelly Criterion position sizer."""

    def __init__(self, fraction: float = 0.25):
        """
        Initialize Kelly sizer.

        Args:
            fraction: Fraction of Kelly to use (for safety)

        Raises:
            TypeError: If fraction is not a number
            ValueError: If fraction is not in range (0, 1]
        """
        if not isinstance(fraction, (int, float)):
            raise TypeError(f"fraction must be a number, got {type(fraction).__name__}")

        if not 0 < fraction <= 1:
            raise ValueError(f"fraction must be in range (0, 1], got {fraction}")

        self.fraction = fraction

    def calculate_position_size(
        self, signal: SignalEvent, portfolio: Portfolio, current_price: Optional[float] = None
    ) -> int:
        """
        Calculate position size using Kelly Criterion.

        CRITICAL FIX: For EXIT signals, return 0 (generate_orders handles closing).

        Args:
            signal: Trading signal
            portfolio: Current portfolio state
            current_price: Current market price for the symbol

        Returns:
            Target position quantity
        """
        # CRITICAL FIX: EXIT signals should return 0
        if signal.signal_type == 'EXIT':
            return 0

        # Get current price from parameter, position, or fail safely with 0
        if current_price is None:
            current_position = portfolio.positions.get(signal.symbol)
            if current_position:
                price = current_position.current_price
            else:
                logger.warning(
                    f"No current price available for {signal.symbol}, cannot calculate position size"
                )
                return 0
        else:
            price = current_price

        if price <= 0:
            logger.warning(f"Invalid price {price} for {signal.symbol}")
            return 0

        # Kelly formula: f = (bp - q) / b
        # where b = odds, p = win probability, q = 1-p
        # For this implementation, use signal strength as proxy for probability

        win_prob = signal.strength
        loss_prob = 1 - win_prob
        win_loss_ratio = 2.0  # Assume 2:1 reward:risk

        kelly_fraction = (win_prob * win_loss_ratio - loss_prob) / win_loss_ratio
        kelly_fraction = max(0, min(kelly_fraction, 1.0))  # Clamp to [0, 1]
        kelly_fraction *= self.fraction  # Apply fractional Kelly

        amount = portfolio.equity * kelly_fraction
        target_shares = int(amount / price) if price > 0 else 0

        # CRITICAL FIX: Account for all costs with proper buffer
        cost_multiplier = 1.016  # Slippage + Commission + Safety (1.6% total)
        max_affordable_shares = int(portfolio.cash / (price * cost_multiplier))

        # Use the minimum to respect cash constraints
        shares = min(target_shares, max_affordable_shares)

        # Double-check with estimated costs
        estimated_fill_price = price * 1.005
        estimated_commission = shares * estimated_fill_price * 0.001
        total_estimated_cost = (shares * estimated_fill_price) + estimated_commission

        if total_estimated_cost > portfolio.cash:
            shares = int(portfolio.cash / (price * 1.020))
            logger.debug(
                f"Applied emergency position size reduction to {shares} shares"
            )

        if signal.signal_type == 'LONG':
            return shares
        elif signal.signal_type == 'SHORT':
            return -shares
        else:
            return 0
