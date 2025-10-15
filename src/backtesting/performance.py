"""
Performance analysis and metrics calculation.
"""

from typing import Dict, List
import numpy as np
import pandas as pd
from scipy import stats
from loguru import logger

from src.models.portfolio import PerformanceMetrics
from src.models.events import FillEvent


class PerformanceAnalyzer:
    """
    Calculates comprehensive performance metrics for backtested strategies.

    Metrics include:
    - Sharpe ratio, Sortino ratio
    - Maximum drawdown and duration
    - Win rate, profit factor
    - Calmar ratio, volatility
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize performance analyzer.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculation
        """
        self.risk_free_rate = risk_free_rate
        self.fills: List[FillEvent] = []

        logger.info(f"Initialized PerformanceAnalyzer (rf={risk_free_rate})")

    def record_fill(self, fill: FillEvent):
        """Record fill for trade analysis."""
        self.fills.append(fill)

    def calculate_performance_metrics(
        self,
        equity_curve: pd.DataFrame,
        initial_capital: float,
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            equity_curve: DataFrame with equity over time
            initial_capital: Initial capital amount

        Returns:
            Performance metrics
        """
        if equity_curve.empty:
            logger.warning("Empty equity curve, returning zero metrics")
            return PerformanceMetrics()

        # Calculate returns
        equity_curve = equity_curve.copy()
        equity_curve['returns'] = equity_curve['equity'].pct_change()

        # Total return
        total_return = (
            (equity_curve['equity'].iloc[-1] - initial_capital) / initial_capital
        )

        # Sharpe ratio
        sharpe = self._calculate_sharpe_ratio(equity_curve['returns'])

        # Sortino ratio
        sortino = self._calculate_sortino_ratio(equity_curve['returns'])

        # Maximum drawdown
        max_dd, max_dd_duration = self._calculate_max_drawdown(equity_curve['equity'])

        # Trade statistics
        trade_stats = self._calculate_trade_statistics()

        # Volatility (annualized)
        volatility = equity_curve['returns'].std() * np.sqrt(252)

        # Calmar ratio
        calmar = abs(total_return / max_dd) if max_dd != 0 else 0.0

        metrics = PerformanceMetrics(
            total_return=total_return * 100,  # Convert to percentage
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=abs(max_dd) * 100,
            max_drawdown_duration=max_dd_duration,
            volatility=volatility * 100,
            calmar_ratio=calmar,
            **trade_stats,
        )

        logger.info(
            f"Performance: Return={metrics.total_return:.2f}%, "
            f"Sharpe={metrics.sharpe_ratio:.2f}, "
            f"MaxDD={metrics.max_drawdown:.2f}%, "
            f"WinRate={metrics.win_rate:.2f}%"
        )

        return metrics

    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """
        Calculate annualized Sharpe ratio.

        Args:
            returns: Series of returns

        Returns:
            Sharpe ratio
        """
        if returns.empty or returns.std() == 0:
            return 0.0

        # Annualize returns
        mean_return = returns.mean() * 252
        std_return = returns.std() * np.sqrt(252)

        sharpe = (mean_return - self.risk_free_rate) / std_return
        return sharpe

    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """
        Calculate annualized Sortino ratio (downside deviation).

        Args:
            returns: Series of returns

        Returns:
            Sortino ratio
        """
        if returns.empty:
            return 0.0

        # Calculate downside deviation
        downside_returns = returns[returns < 0]
        if downside_returns.empty or downside_returns.std() == 0:
            return 0.0

        mean_return = returns.mean() * 252
        downside_std = downside_returns.std() * np.sqrt(252)

        sortino = (mean_return - self.risk_free_rate) / downside_std
        return sortino

    def _calculate_max_drawdown(self, equity: pd.Series) -> tuple[float, int]:
        """
        Calculate maximum drawdown and duration.

        Args:
            equity: Series of equity values

        Returns:
            Tuple of (max_drawdown, duration_in_bars)
        """
        if equity.empty:
            return 0.0, 0

        # Calculate running maximum
        running_max = equity.expanding().max()

        # Calculate drawdown
        drawdown = (equity - running_max) / running_max

        # Maximum drawdown
        max_dd = drawdown.min()

        # Calculate duration
        dd_duration = 0
        current_dd_duration = 0

        for dd in drawdown:
            if dd < 0:
                current_dd_duration += 1
                dd_duration = max(dd_duration, current_dd_duration)
            else:
                current_dd_duration = 0

        return max_dd, dd_duration

    def _calculate_trade_statistics(self) -> Dict:
        """
        Calculate trade-level statistics.

        Returns:
            Dictionary of trade statistics
        """
        if not self.fills:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
            }

        # Group fills by symbol to calculate trade P&L
        trades_by_symbol: Dict[str, List[FillEvent]] = {}
        for fill in self.fills:
            if fill.symbol not in trades_by_symbol:
                trades_by_symbol[fill.symbol] = []
            trades_by_symbol[fill.symbol].append(fill)

        # Calculate P&L for each completed trade
        trade_pnls = []

        for symbol, fills in trades_by_symbol.items():
            position = 0
            avg_price = 0.0

            for fill in fills:
                if position == 0:
                    # Opening position
                    position = fill.quantity
                    avg_price = fill.fill_price
                elif (position > 0 and fill.quantity < 0) or (position < 0 and fill.quantity > 0):
                    # Closing (partial or full)
                    close_qty = min(abs(position), abs(fill.quantity))
                    pnl = close_qty * (fill.fill_price - avg_price) * np.sign(position)
                    pnl -= fill.commission

                    trade_pnls.append(pnl)

                    position += fill.quantity
                    if position == 0:
                        avg_price = 0.0
                else:
                    # Adding to position
                    total_cost = (abs(position) * avg_price) + (abs(fill.quantity) * fill.fill_price)
                    position += fill.quantity
                    avg_price = total_cost / abs(position)

        if not trade_pnls:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
            }

        trade_pnls = np.array(trade_pnls)
        winning_trades = trade_pnls[trade_pnls > 0]
        losing_trades = trade_pnls[trade_pnls < 0]

        total_trades = len(trade_pnls)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0

        gross_profit = winning_trades.sum() if len(winning_trades) > 0 else 0.0
        gross_loss = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

        avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0.0
        avg_loss = losing_trades.mean() if len(losing_trades) > 0 else 0.0
        largest_win = winning_trades.max() if len(winning_trades) > 0 else 0.0
        largest_loss = losing_trades.min() if len(losing_trades) > 0 else 0.0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_count,
            'losing_trades': losing_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_win': avg_win,
            'average_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
        }
