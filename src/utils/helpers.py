"""
Helper utility functions
"""

from typing import Optional
import numpy as np


def calculate_position_size(
    account_value: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """
    Calculate position size based on risk management

    Args:
        account_value: Total account value
        risk_per_trade: Risk per trade as decimal (e.g., 0.02 for 2%)
        entry_price: Entry price for position
        stop_loss_price: Stop loss price

    Returns:
        Number of shares to trade
    """
    risk_amount = account_value * risk_per_trade
    price_risk = abs(entry_price - stop_loss_price)

    if price_risk == 0:
        return 0

    shares = risk_amount / price_risk
    return round(shares, 2)


def format_currency(amount: float, symbol: str = "$") -> str:
    """
    Format amount as currency string

    Args:
        amount: Amount to format
        symbol: Currency symbol

    Returns:
        Formatted currency string
    """
    return f"{symbol}{amount:,.2f}"


def calculate_kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Calculate Kelly Criterion for position sizing

    Args:
        win_rate: Win rate (0-1)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount

    Returns:
        Optimal position size fraction (0-1)
    """
    if avg_loss == 0:
        return 0

    win_loss_ratio = abs(avg_win / avg_loss)
    kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

    # Cap at 25% for safety (Kelly can be aggressive)
    return max(0, min(kelly, 0.25))


def calculate_compound_annual_growth_rate(
    beginning_value: float,
    ending_value: float,
    num_periods: int,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR)

    Args:
        beginning_value: Starting value
        ending_value: Ending value
        num_periods: Number of periods
        periods_per_year: Trading periods per year (default: 252)

    Returns:
        CAGR as decimal
    """
    if beginning_value <= 0 or num_periods <= 0:
        return 0

    years = num_periods / periods_per_year
    cagr = (ending_value / beginning_value) ** (1 / years) - 1

    return cagr


def annualize_metric(
    metric_value: float,
    num_periods: int,
    periods_per_year: int = 252
) -> float:
    """
    Annualize a metric (like volatility or return)

    Args:
        metric_value: Metric value for the period
        num_periods: Number of periods
        periods_per_year: Trading periods per year

    Returns:
        Annualized metric value
    """
    if num_periods <= 0:
        return 0

    scaling_factor = np.sqrt(periods_per_year / num_periods)
    return metric_value * scaling_factor
