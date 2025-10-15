"""
Visualization utilities for backtesting results.
"""

from typing import Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def plot_equity_curve(
    equity_curve: pd.DataFrame,
    title: str = "Equity Curve",
    save_path: Optional[Path] = None,
):
    """
    Plot equity curve over time.

    Args:
        equity_curve: DataFrame with timestamp and equity columns
        title: Plot title
        save_path: Optional path to save figure
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Equity curve
    axes[0].plot(equity_curve['timestamp'], equity_curve['equity'], linewidth=2)
    axes[0].set_ylabel('Equity ($)')
    axes[0].set_title(title)
    axes[0].grid(True, alpha=0.3)

    # Returns
    if 'return_pct' in equity_curve.columns:
        axes[1].plot(equity_curve['timestamp'], equity_curve['return_pct'], linewidth=1)
        axes[1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[1].set_ylabel('Return (%)')
        axes[1].set_xlabel('Date')
        axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    plt.show()


def plot_drawdown(
    equity_curve: pd.DataFrame,
    title: str = "Drawdown",
    save_path: Optional[Path] = None,
):
    """
    Plot drawdown over time.

    Args:
        equity_curve: DataFrame with timestamp and equity columns
        title: Plot title
        save_path: Optional path to save figure
    """
    # Calculate drawdown
    running_max = equity_curve['equity'].expanding().max()
    drawdown = (equity_curve['equity'] - running_max) / running_max * 100

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.fill_between(
        equity_curve['timestamp'],
        drawdown,
        0,
        alpha=0.3,
        color='red',
        label='Drawdown'
    )
    ax.plot(equity_curve['timestamp'], drawdown, color='red', linewidth=1)

    ax.set_ylabel('Drawdown (%)')
    ax.set_xlabel('Date')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    plt.show()


def plot_returns_distribution(
    equity_curve: pd.DataFrame,
    title: str = "Returns Distribution",
    save_path: Optional[Path] = None,
):
    """
    Plot returns distribution and statistics.

    Args:
        equity_curve: DataFrame with equity data
        title: Plot title
        save_path: Optional path to save figure
    """
    # Calculate returns
    returns = equity_curve['equity'].pct_change().dropna()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram
    axes[0].hist(returns, bins=50, alpha=0.7, edgecolor='black')
    axes[0].axvline(returns.mean(), color='r', linestyle='--', label=f'Mean: {returns.mean():.4f}')
    axes[0].axvline(returns.median(), color='g', linestyle='--', label=f'Median: {returns.median():.4f}')
    axes[0].set_xlabel('Returns')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Returns Distribution')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Q-Q plot
    from scipy import stats
    stats.probplot(returns, dist="norm", plot=axes[1])
    axes[1].set_title('Q-Q Plot (Normal Distribution)')
    axes[1].grid(True, alpha=0.3)

    plt.suptitle(title, fontsize=14, y=1.02)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    plt.show()
