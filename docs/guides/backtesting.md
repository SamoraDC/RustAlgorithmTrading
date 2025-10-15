# Backtesting Guide

Comprehensive guide to backtesting trading strategies in the py_rt system.

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Backtesting](#basic-backtesting)
3. [Walk-Forward Analysis](#walk-forward-analysis)
4. [Performance Metrics](#performance-metrics)
5. [Transaction Costs](#transaction-costs)
6. [Monte Carlo Simulation](#monte-carlo-simulation)
7. [Optimization](#optimization)
8. [Best Practices](#best-practices)

## Introduction

Backtesting allows you to test trading strategies on historical data to evaluate performance before risking real capital.

### Why Backtest?

- **Validate Strategy Logic**: Ensure your strategy behaves as expected
- **Estimate Performance**: Understand potential returns and risks
- **Optimize Parameters**: Find optimal strategy settings
- **Identify Issues**: Discover edge cases and failure modes

### Backtesting Limitations

- **Historical Performance ≠ Future Results**: Past performance is not indicative of future results
- **Overfitting Risk**: Strategies optimized on historical data may not generalize
- **Survivorship Bias**: Historical data may exclude delisted stocks
- **Look-Ahead Bias**: Ensure you don't use future information
- **Transaction Costs**: Include realistic commissions and slippage

## Basic Backtesting

### Step 1: Import Required Modules

```python
from src.backtesting.engine import BacktestEngine
from src.backtesting.metrics import calculate_metrics
from src.strategies.momentum import MomentumStrategy
from src.data.fetcher import DataFetcher
from datetime import datetime, timedelta
import pandas as pd
```

### Step 2: Fetch Historical Data

```python
# Initialize data fetcher
fetcher = DataFetcher()

# Define date range
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

# Fetch data
data = fetcher.get_bars(
    symbol="AAPL",
    start=start_date,
    end=end_date,
    timeframe="1Day"
)

print(f"Loaded {len(data)} bars from {start_date} to {end_date}")
```

### Step 3: Initialize Backtest Engine

```python
# Create backtest engine with realistic settings
engine = BacktestEngine(
    initial_capital=100000.0,
    commission=0.001,        # 0.1% per trade
    slippage=0.0005,         # 0.05% slippage
    enable_short=False,      # Long only
    margin_requirement=1.0   # No leverage
)
```

### Step 4: Run Backtest

```python
# Initialize strategy
strategy = MomentumStrategy(
    lookback_period=20,
    threshold=0.02,
    position_pct=0.1
)

# Run backtest
results = engine.run(strategy, data)

print(f"\nBacktest completed:")
print(f"Total trades: {results.num_trades}")
print(f"Final capital: ${results.final_capital:,.2f}")
```

### Step 5: Analyze Results

```python
# Calculate performance metrics
metrics = calculate_metrics(results)

print("\n=== Performance Metrics ===")
print(f"Total Return: {metrics['total_return']:.2%}")
print(f"Annual Return: {metrics['annual_return']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
print(f"Win Rate: {metrics['win_rate']:.2%}")
print(f"Profit Factor: {metrics['profit_factor']:.2f}")
print(f"Calmar Ratio: {metrics['calmar_ratio']:.2f}")
```

## Walk-Forward Analysis

Walk-forward analysis prevents overfitting by continuously training on historical data and testing on out-of-sample data.

### Concept

```
|----Training----|--Test--|----Training----|--Test--|----Training----|--Test--|
0              252       315              567       630              882      945
                          └─ Walk Forward ─┘
```

### Implementation

```python
from src.backtesting.walk_forward import WalkForwardAnalysis

# Initialize walk-forward analyzer
wf_analyzer = WalkForwardAnalysis(
    train_period=252,    # 1 year training
    test_period=63,      # 3 months testing
    step_size=63,        # Re-train every 3 months
    optimize=True        # Optimize parameters during training
)

# Run walk-forward analysis
wf_results = wf_analyzer.run(
    strategy_class=MomentumStrategy,
    data=data,
    param_ranges={
        'lookback_period': range(10, 50, 5),
        'threshold': [0.01, 0.015, 0.02, 0.025, 0.03]
    }
)

# Analyze results
print("\n=== Walk-Forward Results ===")
print(f"Avg Test Return: {wf_results.avg_test_return:.2%}")
print(f"Avg Train Return: {wf_results.avg_train_return:.2%}")
print(f"Degradation: {wf_results.degradation:.2%}")
print(f"Consistency: {wf_results.consistency:.2%}")
```

### Interpret Results

- **Degradation < 20%**: Strategy is not overfit
- **Consistency > 60%**: Strategy performs consistently
- **Test Return > 0**: Strategy is profitable out-of-sample

## Performance Metrics

### Return Metrics

```python
def calculate_return_metrics(results):
    """Calculate various return metrics."""
    returns = results.equity_curve.pct_change().dropna()

    metrics = {
        # Total return
        'total_return': (results.final_capital / results.initial_capital) - 1,

        # Annualized return
        'annual_return': (
            (results.final_capital / results.initial_capital) **
            (252 / len(results.equity_curve)) - 1
        ),

        # Average daily return
        'avg_daily_return': returns.mean(),

        # Volatility (annualized)
        'volatility': returns.std() * np.sqrt(252),

        # Downside deviation (annualized)
        'downside_deviation': returns[returns < 0].std() * np.sqrt(252)
    }

    return metrics
```

### Risk-Adjusted Metrics

```python
def calculate_risk_metrics(results, risk_free_rate=0.02):
    """Calculate risk-adjusted performance metrics."""
    returns = results.equity_curve.pct_change().dropna()

    # Sharpe Ratio
    excess_returns = returns.mean() - (risk_free_rate / 252)
    sharpe_ratio = excess_returns / returns.std() * np.sqrt(252)

    # Sortino Ratio
    downside_returns = returns[returns < 0]
    sortino_ratio = (
        excess_returns / downside_returns.std() * np.sqrt(252)
        if len(downside_returns) > 0 else np.inf
    )

    # Calmar Ratio
    annual_return = results.annual_return
    max_drawdown = calculate_max_drawdown(results)
    calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else np.inf

    return {
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio
    }
```

### Drawdown Analysis

```python
def calculate_drawdown_metrics(results):
    """Calculate drawdown metrics."""
    equity = results.equity_curve
    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max

    return {
        'max_drawdown': drawdown.min(),
        'avg_drawdown': drawdown[drawdown < 0].mean(),
        'max_drawdown_duration': calculate_max_dd_duration(drawdown),
        'recovery_time': calculate_recovery_time(drawdown)
    }
```

### Trade Metrics

```python
def calculate_trade_metrics(results):
    """Calculate trade-level metrics."""
    trades = results.trades

    wins = trades[trades['pnl'] > 0]
    losses = trades[trades['pnl'] < 0]

    return {
        'num_trades': len(trades),
        'win_rate': len(wins) / len(trades) if len(trades) > 0 else 0,
        'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
        'profit_factor': (
            abs(wins['pnl'].sum() / losses['pnl'].sum())
            if len(losses) > 0 and losses['pnl'].sum() != 0
            else np.inf
        ),
        'max_consecutive_wins': calculate_max_consecutive(wins),
        'max_consecutive_losses': calculate_max_consecutive(losses)
    }
```

## Transaction Costs

### Realistic Commission Model

```python
class CommissionModel:
    """Commission model for backtesting."""

    def __init__(self,
                 per_share: float = 0.0,
                 per_trade: float = 1.0,
                 percentage: float = 0.001):
        """Initialize commission model.

        Args:
            per_share: Commission per share
            per_trade: Fixed commission per trade
            percentage: Percentage commission
        """
        self.per_share = per_share
        self.per_trade = per_trade
        self.percentage = percentage

    def calculate(self, price: float, quantity: int) -> float:
        """Calculate total commission for trade."""
        value = price * quantity

        commission = (
            self.per_share * quantity +
            self.per_trade +
            value * self.percentage
        )

        return commission
```

### Slippage Model

```python
class SlippageModel:
    """Slippage model for backtesting."""

    def __init__(self, fixed_bps: float = 5.0, volume_pct: float = 0.01):
        """Initialize slippage model.

        Args:
            fixed_bps: Fixed slippage in basis points
            volume_pct: Percentage of volume that causes 1bp slippage
        """
        self.fixed_bps = fixed_bps
        self.volume_pct = volume_pct

    def calculate(self, price: float, quantity: int,
                  avg_volume: int) -> float:
        """Calculate slippage for trade."""
        # Fixed slippage
        fixed_slippage = price * (self.fixed_bps / 10000)

        # Volume-based slippage
        volume_impact = (quantity / avg_volume) / self.volume_pct
        volume_slippage = price * (volume_impact / 10000)

        total_slippage = fixed_slippage + volume_slippage

        return total_slippage
```

## Monte Carlo Simulation

Monte Carlo simulation estimates the probability distribution of strategy returns.

### Implementation

```python
from src.simulations.monte_carlo import MonteCarloSimulation

# Initialize Monte Carlo simulator
mc_sim = MonteCarloSimulation(
    num_simulations=10000,
    confidence_level=0.95
)

# Run simulations
mc_results = mc_sim.run(
    strategy=strategy,
    data=data,
    resample_method='bootstrap'  # or 'parametric'
)

print("\n=== Monte Carlo Results ===")
print(f"Mean Return: {mc_results.mean_return:.2%}")
print(f"Std Return: {mc_results.std_return:.2%}")
print(f"95% Confidence Interval: [{mc_results.ci_lower:.2%}, {mc_results.ci_upper:.2%}]")
print(f"Probability of Profit: {mc_results.prob_profit:.2%}")
print(f"Expected Shortfall (95%): {mc_results.cvar_95:.2%}")
```

### Visualize Distribution

```python
import matplotlib.pyplot as plt

# Plot return distribution
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
ax1.hist(mc_results.returns, bins=50, alpha=0.7, edgecolor='black')
ax1.axvline(mc_results.mean_return, color='red', linestyle='--',
            label=f'Mean: {mc_results.mean_return:.2%}')
ax1.axvline(mc_results.ci_lower, color='orange', linestyle='--',
            label=f'5th percentile: {mc_results.ci_lower:.2%}')
ax1.axvline(mc_results.ci_upper, color='orange', linestyle='--',
            label=f'95th percentile: {mc_results.ci_upper:.2%}')
ax1.set_xlabel('Return')
ax1.set_ylabel('Frequency')
ax1.set_title('Monte Carlo Return Distribution')
ax1.legend()
ax1.grid(alpha=0.3)

# Equity curve paths
for i in range(100):  # Plot 100 sample paths
    ax2.plot(mc_results.equity_paths[i], alpha=0.1, color='blue')
ax2.plot(mc_results.equity_paths.mean(axis=0), color='red',
         linewidth=2, label='Mean Path')
ax2.set_xlabel('Time')
ax2.set_ylabel('Equity')
ax2.set_title('Sample Equity Paths')
ax2.legend()
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('docs/images/monte_carlo_results.png', dpi=300)
```

## Optimization

### Grid Search

```python
from itertools import product

def grid_search(strategy_class, data, param_ranges):
    """Optimize strategy parameters using grid search."""
    results = []

    # Generate all parameter combinations
    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())

    for values in product(*param_values):
        params = dict(zip(param_names, values))

        # Run backtest
        strategy = strategy_class(**params)
        backtest_result = engine.run(strategy, data)
        metrics = calculate_metrics(backtest_result)

        results.append({
            'params': params,
            'sharpe_ratio': metrics['sharpe_ratio'],
            'total_return': metrics['total_return'],
            'max_drawdown': metrics['max_drawdown']
        })

    # Find best parameters
    best = max(results, key=lambda x: x['sharpe_ratio'])

    return best, results
```

### Bayesian Optimization

```python
from skopt import gp_minimize
from skopt.space import Real, Integer

def bayesian_optimize(strategy_class, data, param_space, n_calls=50):
    """Optimize strategy parameters using Bayesian optimization."""

    def objective(params):
        """Objective function to minimize (negative Sharpe)."""
        param_dict = {
            'lookback_period': int(params[0]),
            'threshold': params[1],
            'position_pct': params[2]
        }

        strategy = strategy_class(**param_dict)
        results = engine.run(strategy, data)
        metrics = calculate_metrics(results)

        return -metrics['sharpe_ratio']  # Minimize negative Sharpe

    # Run optimization
    result = gp_minimize(
        objective,
        param_space,
        n_calls=n_calls,
        random_state=42,
        verbose=True
    )

    return result
```

## Best Practices

### 1. Avoid Look-Ahead Bias

```python
# BAD: Using future information
signals[i] = 1 if data['close'][i+1] > data['close'][i] else -1

# GOOD: Using only past information
signals[i] = 1 if data['close'][i] > data['close'][i-1] else -1
```

### 2. Use Realistic Transaction Costs

```python
# Include realistic costs
engine = BacktestEngine(
    commission=0.001,      # 0.1% commission
    slippage=0.0005,       # 0.05% slippage
)

# Don't assume zero costs
engine = BacktestEngine(
    commission=0.0,  # Unrealistic
    slippage=0.0     # Unrealistic
)
```

### 3. Out-of-Sample Testing

```python
# Split data
split_idx = int(len(data) * 0.7)
train_data = data[:split_idx]
test_data = data[split_idx:]

# Optimize on training data
best_params, _ = grid_search(strategy_class, train_data, param_ranges)

# Evaluate on test data (out-of-sample)
strategy = strategy_class(**best_params['params'])
test_results = engine.run(strategy, test_data)
```

### 4. Check for Overfitting

```python
# Compare in-sample vs out-of-sample
train_sharpe = train_metrics['sharpe_ratio']
test_sharpe = test_metrics['sharpe_ratio']

degradation = (train_sharpe - test_sharpe) / train_sharpe

if degradation > 0.30:
    print("WARNING: Potential overfitting detected!")
    print(f"Train Sharpe: {train_sharpe:.2f}")
    print(f"Test Sharpe: {test_sharpe:.2f}")
    print(f"Degradation: {degradation:.2%}")
```

### 5. Multiple Timeframes

```python
# Test on different timeframes
timeframes = ['1Day', '1Hour', '5Min']
results = {}

for tf in timeframes:
    data = fetcher.get_bars("AAPL", start, end, timeframe=tf)
    backtest_result = engine.run(strategy, data)
    results[tf] = calculate_metrics(backtest_result)

# Compare consistency
for tf, metrics in results.items():
    print(f"{tf}: Sharpe={metrics['sharpe_ratio']:.2f}")
```

## Next Steps

- [Strategy Development](strategy-development.md) - Build better strategies
- [Performance Metrics](../api/python/backtesting.md) - Detailed metrics reference
- [Monte Carlo Guide](monte-carlo.md) - Advanced risk analysis
- [Deployment Guide](deployment.md) - Deploy tested strategies

---

**Last Updated**: 2025-10-14
