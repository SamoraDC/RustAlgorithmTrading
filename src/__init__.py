"""
Algorithmic Trading System with Backtesting and Monte Carlo Simulations
"""

__version__ = "0.1.0"
__author__ = "Trading System"

from src.api.alpaca_client import AlpacaClient
from src.backtesting.engine import BacktestEngine
from src.simulations.monte_carlo import MonteCarloSimulator
from src.strategies.base import Strategy

__all__ = [
    "AlpacaClient",
    "BacktestEngine",
    "MonteCarloSimulator",
    "Strategy",
]
