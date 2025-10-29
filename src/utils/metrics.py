"""
Performance metrics calculation utilities.
"""

from typing import Dict
import pandas as pd

# Temporary workaround: tabulate installation failing
try:
    from tabulate import tabulate
except ImportError:
    # Fallback: Simple table formatting without tabulate
    def tabulate(data, tablefmt='grid'):
        """Simple fallback table formatter"""
        lines = []
        for row in data:
            lines.append(f"{row[0]:<30} | {row[1]:>15}")
        return '\n'.join(lines)


def calculate_metrics(results: Dict) -> Dict:
    """
    Calculate summary metrics from backtest results.

    Args:
        results: Backtest results dictionary

    Returns:
        Dictionary of calculated metrics
    """
    metrics = results['metrics']
    equity_curve = results['equity_curve']
    exec_stats = results['execution_stats']

    # Extract key metrics
    summary = {
        'Total Return (%)': metrics['total_return'],
        'Sharpe Ratio': metrics['sharpe_ratio'],
        'Sortino Ratio': metrics['sortino_ratio'],
        'Max Drawdown (%)': metrics['max_drawdown'],
        'Calmar Ratio': metrics['calmar_ratio'],
        'Win Rate (%)': metrics['win_rate'],
        'Profit Factor': metrics['profit_factor'],
        'Total Trades': metrics['total_trades'],
        'Avg Win ($)': metrics['average_win'],
        'Avg Loss ($)': metrics['average_loss'],
        'Largest Win ($)': metrics['largest_win'],
        'Largest Loss ($)': metrics['largest_loss'],
        'Events Processed': exec_stats['events_processed'],
        'Events/Second': exec_stats['events_per_second'],
    }

    return summary


def format_metrics_table(metrics: Dict) -> str:
    """
    Format metrics as a table string.

    Args:
        metrics: Metrics dictionary

    Returns:
        Formatted table string
    """
    # Group metrics
    performance_metrics = [
        ('Total Return (%)', f"{metrics.get('Total Return (%)', 0):.2f}"),
        ('Sharpe Ratio', f"{metrics.get('Sharpe Ratio', 0):.2f}"),
        ('Sortino Ratio', f"{metrics.get('Sortino Ratio', 0):.2f}"),
        ('Calmar Ratio', f"{metrics.get('Calmar Ratio', 0):.2f}"),
        ('Max Drawdown (%)', f"{metrics.get('Max Drawdown (%)', 0):.2f}"),
    ]

    trade_metrics = [
        ('Total Trades', f"{metrics.get('Total Trades', 0)}"),
        ('Win Rate (%)', f"{metrics.get('Win Rate (%)', 0):.2f}"),
        ('Profit Factor', f"{metrics.get('Profit Factor', 0):.2f}"),
        ('Avg Win ($)', f"{metrics.get('Avg Win ($)', 0):.2f}"),
        ('Avg Loss ($)', f"{metrics.get('Avg Loss ($)', 0):.2f}"),
        ('Largest Win ($)', f"{metrics.get('Largest Win ($)', 0):.2f}"),
        ('Largest Loss ($)', f"{metrics.get('Largest Loss ($)', 0):.2f}"),
    ]

    execution_metrics = [
        ('Events Processed', f"{metrics.get('Events Processed', 0)}"),
        ('Events/Second', f"{metrics.get('Events/Second', 0):.2f}"),
    ]

    # Format tables
    output = "\n"
    output += "=" * 50 + "\n"
    output += "PERFORMANCE METRICS\n"
    output += "=" * 50 + "\n"
    output += tabulate(performance_metrics, tablefmt='grid') + "\n\n"

    output += "=" * 50 + "\n"
    output += "TRADE STATISTICS\n"
    output += "=" * 50 + "\n"
    output += tabulate(trade_metrics, tablefmt='grid') + "\n\n"

    output += "=" * 50 + "\n"
    output += "EXECUTION STATISTICS\n"
    output += "=" * 50 + "\n"
    output += tabulate(execution_metrics, tablefmt='grid') + "\n"

    return output
