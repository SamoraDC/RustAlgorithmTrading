"""
Performance metrics calculation for backtesting
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger


class PerformanceMetrics:
    """Calculate trading strategy performance metrics"""

    @staticmethod
    def calculate(
        trades: List[Any],
        equity_curve: pd.DataFrame,
        initial_capital: float,
        risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics

        Args:
            trades: List of Trade objects
            equity_curve: DataFrame with equity over time
            initial_capital: Starting capital
            risk_free_rate: Annual risk-free rate (default: 2%)

        Returns:
            Dictionary with performance metrics
        """
        if equity_curve.empty:
            return PerformanceMetrics._empty_metrics()

        # Calculate returns
        equity_curve = equity_curve.copy()
        equity_curve['returns'] = equity_curve['equity'].pct_change().fillna(0)

        # Basic metrics
        final_equity = float(equity_curve.iloc[-1]['equity'])
        total_return = (final_equity - initial_capital) / initial_capital
        total_return_pct = total_return * 100

        # Trade statistics
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]

        num_trades = len(trades)
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        win_rate = (num_winning / num_trades * 100) if num_trades > 0 else 0

        # Profit metrics
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_loss = sum(t.pnl for t in losing_trades) if losing_trades else 0
        net_profit = total_profit + total_loss

        avg_win = total_profit / num_winning if num_winning > 0 else 0
        avg_loss = total_loss / num_losing if num_losing > 0 else 0

        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else np.inf

        # Risk metrics
        sharpe_ratio = PerformanceMetrics._calculate_sharpe_ratio(
            equity_curve['returns'],
            risk_free_rate
        )

        sortino_ratio = PerformanceMetrics._calculate_sortino_ratio(
            equity_curve['returns'],
            risk_free_rate
        )

        max_drawdown, max_drawdown_pct = PerformanceMetrics._calculate_max_drawdown(
            equity_curve['equity']
        )

        # Calmar ratio
        annual_return = PerformanceMetrics._annualize_return(total_return, len(equity_curve))
        calmar_ratio = (annual_return / abs(max_drawdown_pct)) if max_drawdown_pct != 0 else 0

        # Expectancy
        expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * abs(avg_loss))

        metrics = {
            # Returns
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'annual_return': annual_return,
            'net_profit': net_profit,

            # Trade statistics
            'num_trades': num_trades,
            'num_winning': num_winning,
            'num_losing': num_losing,
            'win_rate': win_rate,

            # Profit metrics
            'total_profit': total_profit,
            'total_loss': total_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,

            # Risk metrics
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'calmar_ratio': calmar_ratio,

            # Volatility
            'volatility': float(equity_curve['returns'].std() * np.sqrt(252)),
        }

        logger.info("Performance metrics calculated successfully")
        return metrics

    @staticmethod
    def _calculate_sharpe_ratio(
        returns: pd.Series,
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        sharpe = np.sqrt(252) * excess_returns.mean() / returns.std()
        return float(sharpe)

    @staticmethod
    def _calculate_sortino_ratio(
        returns: pd.Series,
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sortino ratio (only considers downside volatility)"""
        if len(returns) == 0:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        sortino = np.sqrt(252) * excess_returns.mean() / downside_returns.std()
        return float(sortino)

    @staticmethod
    def _calculate_max_drawdown(equity: pd.Series) -> tuple[float, float]:
        """Calculate maximum drawdown"""
        if len(equity) == 0:
            return 0.0, 0.0

        running_max = equity.expanding().max()
        drawdown = equity - running_max
        max_drawdown = float(drawdown.min())
        max_drawdown_pct = float((drawdown / running_max).min() * 100)

        return max_drawdown, max_drawdown_pct

    @staticmethod
    def _annualize_return(total_return: float, num_periods: int) -> float:
        """Annualize return based on number of periods"""
        if num_periods == 0:
            return 0.0

        # Assume daily data
        years = num_periods / 252
        annual_return = ((1 + total_return) ** (1 / years)) - 1
        return float(annual_return)

    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Return empty metrics dict"""
        return {
            'total_return': 0.0,
            'total_return_pct': 0.0,
            'annual_return': 0.0,
            'net_profit': 0.0,
            'num_trades': 0,
            'num_winning': 0,
            'num_losing': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'calmar_ratio': 0.0,
            'volatility': 0.0,
        }
