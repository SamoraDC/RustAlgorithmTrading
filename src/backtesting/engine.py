"""
Event-driven backtesting engine.
"""

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from src.models.events import Event, EventType, MarketEvent, SignalEvent
from .data_handler import HistoricalDataHandler
from .execution_handler import SimulatedExecutionHandler
from .portfolio_handler import PortfolioHandler
from .performance import PerformanceAnalyzer


class BacktestEngine:
    """
    Event-driven backtesting engine that processes events in chronological order.

    This engine implements a queue-based event processing system where market data,
    signals, orders, and fills are processed sequentially, mimicking live trading.
    """

    def __init__(
        self,
        data_handler: HistoricalDataHandler,
        execution_handler: SimulatedExecutionHandler,
        portfolio_handler: PortfolioHandler,
        strategy,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Initialize backtesting engine.

        Args:
            data_handler: Historical data provider
            execution_handler: Order execution simulator
            portfolio_handler: Portfolio and position tracker
            strategy: Trading strategy instance
            start_date: Backtest start date
            end_date: Backtest end date
        """
        self.data_handler = data_handler
        self.execution_handler = execution_handler
        self.portfolio_handler = portfolio_handler
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date

        self.events: deque[Event] = deque()
        self.continue_backtest = True
        self.performance_analyzer = PerformanceAnalyzer()

        # Metrics
        self.events_processed = 0
        self.signals_generated = 0
        self.orders_placed = 0
        self.fills_executed = 0

        logger.info(
            f"Initialized BacktestEngine from {start_date} to {end_date}"
        )

    def run(self) -> Dict:
        """
        Execute backtest and return performance metrics.

        Returns:
            Dictionary containing performance metrics and equity curve
        """
        logger.info("Starting backtest execution")
        start_time = datetime.utcnow()

        # Process all market data events
        while self.continue_backtest:
            # Update market data bars
            if self.data_handler.continue_backtest:
                self.data_handler.update_bars()

                # FIXED: Create MarketEvent after updating bars
                # Get latest bar from first symbol to trigger signal generation for all symbols
                if self.data_handler.symbols:
                    symbol = self.data_handler.symbols[0]
                    latest_bars = self.data_handler.get_latest_bars(symbol, n=1)
                    if latest_bars:
                        bar = latest_bars[0]
                        market_event = MarketEvent(
                            timestamp=bar.timestamp,
                            symbol=symbol,
                            price=bar.close,
                            volume=bar.volume
                        )
                        self.events.append(market_event)
            else:
                self.continue_backtest = False

            # Process event queue for this bar
            while self.events:
                event = self.events.popleft()
                self._dispatch_event(event)
                self.events_processed += 1

            # RACE FIX: Clear reserved cash after all events in bar are processed
            # This resets the cash reservation system for the next bar
            self.portfolio_handler.clear_reserved_cash()

        # Calculate final performance metrics
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        results = self._generate_results(duration)

        logger.info(
            f"Backtest completed in {duration:.2f}s. "
            f"Processed {self.events_processed} events, "
            f"Generated {self.signals_generated} signals, "
            f"Placed {self.orders_placed} orders, "
            f"Executed {self.fills_executed} fills"
        )

        return results

    def _dispatch_event(self, event: Event):
        """
        Dispatch event to appropriate handler.

        Args:
            event: Event to process
        """
        if event.event_type == EventType.MARKET:
            self._handle_market_event(event)
        elif event.event_type == EventType.SIGNAL:
            self._handle_signal_event(event)
            self.signals_generated += 1
        elif event.event_type == EventType.ORDER:
            self._handle_order_event(event)
            self.orders_placed += 1
        elif event.event_type == EventType.FILL:
            self._handle_fill_event(event)
            self.fills_executed += 1

    def _handle_market_event(self, event: MarketEvent):
        """
        Handle market data update.

        Args:
            event: Market event
        """
        # Update portfolio with latest prices
        self.portfolio_handler.update_timeindex(event.timestamp)

        # FIXED: Convert MarketEvent to format strategy expects
        try:
            # Get latest bars for all symbols from data handler
            bars_data = {}
            for symbol in self.data_handler.symbols:
                # Get last N bars for technical indicators
                bars = self.data_handler.get_latest_bars(symbol, n=50)
                if bars:
                    # Convert to DataFrame format
                    df = pd.DataFrame([
                        {
                            'timestamp': bar.timestamp,
                            'open': bar.open,
                            'high': bar.high,
                            'low': bar.low,
                            'close': bar.close,
                            'volume': bar.volume
                        }
                        for bar in bars
                    ])
                    df.set_index('timestamp', inplace=True)
                    bars_data[symbol] = df

            # Generate signals for each symbol with enough data
            all_signals = []
            for symbol, df in bars_data.items():
                if len(df) >= 20:  # Minimum bars for indicators
                    # Call strategy's per-symbol signal generation
                    if hasattr(self.strategy, 'generate_signals_for_symbol'):
                        signals = self.strategy.generate_signals_for_symbol(symbol, df)
                        all_signals.extend(signals)
                    else:
                        logger.warning(f"Strategy {self.strategy} doesn't support per-symbol signals")

            # Add signal events to queue
            if all_signals:
                for signal in all_signals:
                    # Convert Strategy Signal to SignalEvent
                    # FIXED: Use signal_type.value instead of action attribute
                    signal_event = SignalEvent(
                        timestamp=event.timestamp,
                        symbol=signal.symbol,
                        signal_type=signal.signal_type.value,  # 'BUY', 'SELL', 'HOLD'
                        strength=getattr(signal, 'confidence', 0.8),
                        strategy_id=self.strategy.name
                    )
                    self.events.append(signal_event)

        except Exception as e:
            logger.error(f"Error generating signals from market event: {e}", exc_info=True)

    def _handle_signal_event(self, event):
        """
        Handle trading signal.

        Args:
            event: Signal event
        """
        # Convert signal to orders
        orders = self.portfolio_handler.generate_orders(event)

        # Add order events to queue
        for order in orders:
            self.events.append(order)

    def _handle_order_event(self, event):
        """
        Handle order placement.

        Args:
            event: Order event
        """
        # Execute order through simulated execution
        fill_event = self.execution_handler.execute_order(event)

        if fill_event:
            self.events.append(fill_event)

    def _handle_fill_event(self, event):
        """
        Handle order fill.

        Args:
            event: Fill event
        """
        # Update portfolio with fill
        self.portfolio_handler.update_fill(event)

        # Record for performance analysis
        self.performance_analyzer.record_fill(event)

    def _generate_results(self, duration: float) -> Dict:
        """
        Generate backtest results and performance metrics.

        Args:
            duration: Backtest duration in seconds

        Returns:
            Results dictionary
        """
        equity_curve = self.portfolio_handler.get_equity_curve()
        holdings = self.portfolio_handler.get_holdings()

        metrics = self.performance_analyzer.calculate_performance_metrics(
            equity_curve=equity_curve,
            initial_capital=self.portfolio_handler.initial_capital
        )

        return {
            'metrics': metrics.to_dict(),
            'equity_curve': equity_curve,
            'holdings': holdings,
            'execution_stats': {
                'duration_seconds': duration,
                'events_processed': self.events_processed,
                'signals_generated': self.signals_generated,
                'orders_placed': self.orders_placed,
                'fills_executed': self.fills_executed,
                'events_per_second': self.events_processed / duration if duration > 0 else 0,
            }
        }
