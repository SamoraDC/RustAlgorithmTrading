# Algorithmic Trading Backtesting Best Practices (2025)

## Executive Summary

This document outlines industry best practices for backtesting algorithmic trading strategies, with focus on avoiding common pitfalls and ensuring realistic performance validation.

## Critical Backtesting Biases

### 1. Look-Ahead Bias

**Definition**: Occurs when future information is unknowingly incorporated into historical data, leading to inaccurate backtesting results.

**Common Examples**:
- Using maximal/minimal values that can only be calculated at the end of a time period
- Technical indicators that use future price levels (some moving averages, oscillators)
- Using closing prices to make decisions that would have required intraday information

**Prevention Strategies**:
- Ensure live trading and backtesting employ the same algorithm/code
- Use only data available at the time of testing
- Implement point-in-time data access patterns
- Separate data collection from decision-making logic

### 2. Survivorship Bias

**Definition**: Testing strategies on datasets that only include assets that have "survived" to the current time, excluding delisted, bankrupt, or failed securities.

**Impact Magnitude**:
- **4× less profit** when properly accounting for delisted stocks
- **15% more drawdown** in realistic scenarios
- **Almost half the profit factor** compared to biased testing

**Prevention Strategies**:
- Use point-in-time data that includes both successful and failed assets
- Avoid Yahoo Finance data (NOT survivorship bias free)
- Invest in paid data providers for accurate historical universes
- Test as if you had no knowledge of which assets would succeed

### 3. Optimization Bias (Curve-Fitting)

**Definition**: Over-optimizing parameters to fit historical data, resulting in strategies that fail in live trading.

**Prevention Strategies**:
- Use walk-forward optimization
- Limit the number of parameters
- Employ out-of-sample testing
- Test across multiple market regimes

### 4. Psychological Tolerance Bias

**Definition**: Underestimating the psychological impact of drawdowns and losses in live trading.

**Prevention Strategies**:
- Simulate realistic drawdown scenarios
- Incorporate Monte Carlo simulations for worst-case analysis
- Paper trade before live deployment
- Start with small live allocation

## Multi-Stage Validation Framework

### Stage 1: Design & Backtest (Multiple Years)
- Test on minimum 3-5 years of data
- Include multiple market regimes (bull, bear, sideways)
- Document all assumptions explicitly

### Stage 2: Walk-Forward/Out-of-Sample Testing
- Use 70/30 or 80/20 train/test split
- Roll forward testing windows
- Validate on data not used in optimization

### Stage 3: Paper Trading
- Simulate live order flow
- Test execution logic
- Monitor slippage and fill rates

### Stage 4: Small Live Allocation
- Start with 5-10% of intended capital
- Measure real slippage and costs
- Track performance divergence from backtest

### Stage 5: Scale Methodically
- Only after consistent performance
- Gradual capital increase
- Continuous monitoring

## Realistic Assumptions

### Transaction Costs
- **Commission**: Include all broker fees
- **Slippage**: 0.05-0.10% for liquid stocks, higher for illiquid
- **Market impact**: Significant for larger orders
- **Spread**: Bid-ask spread costs

### Market Conditions
- Test across different volatility regimes
- Include market crashes (2008, 2020, etc.)
- Account for changing correlations

### Data Quality
- Use tick-level data for precision
- Adjust for corporate actions (splits, dividends)
- Include after-hours trading if relevant

## Performance Metrics

### Essential Metrics
- **Sharpe Ratio**: Risk-adjusted returns (>1.0 good, >2.0 excellent)
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss (>1.5 acceptable)
- **Sortino Ratio**: Downside risk-adjusted returns
- **Calmar Ratio**: Return / Maximum drawdown

### Advanced Metrics
- **Value at Risk (VaR)**: Maximum expected loss at confidence level
- **Conditional VaR (CVaR)**: Expected loss beyond VaR
- **Recovery Factor**: Net profit / Maximum drawdown
- **Ulcer Index**: Duration and depth of drawdowns

## Best Practices Checklist

- [ ] Use survivorship-bias-free data
- [ ] Implement point-in-time data access
- [ ] Include realistic transaction costs
- [ ] Test across multiple market regimes
- [ ] Perform walk-forward optimization
- [ ] Use out-of-sample validation
- [ ] Document all assumptions
- [ ] Paper trade before live deployment
- [ ] Start with small capital allocation
- [ ] Monitor live vs backtest performance divergence
- [ ] Use diverse and representative datasets
- [ ] Avoid curve-fitting (limit parameters)
- [ ] Include slippage and market impact
- [ ] Test execution logic separately
- [ ] Implement robust error handling

## Common Pitfalls to Avoid

1. **Unrealistic fill assumptions**: Assuming market orders fill at last price
2. **Ignoring market microstructure**: Order book dynamics, liquidity
3. **Static parameter optimization**: Not adapting to regime changes
4. **Single metric optimization**: Focusing only on returns
5. **Insufficient test data**: Testing on too short period
6. **Lack of stress testing**: Not testing extreme scenarios
7. **Poor risk management**: No position sizing or stop losses

## Recommended Tools & Libraries

### Python Ecosystem
- **backtesting.py**: Fast, simple backtesting framework
- **Backtrader**: Comprehensive backtesting and live trading
- **Zipline**: Realistic institutional-grade backtesting
- **vectorbt**: High-performance vectorized backtesting

### Data Providers (Survivorship-Bias-Free)
- Alpaca Historical API (7+ years)
- QuantConnect Data Library
- Databento
- Polygon.io
- **Avoid**: Yahoo Finance (has survivorship bias)

## References

- QuantStart: Successful Backtesting of Algorithmic Trading Strategies
- AlgoTrading101: Backtesting Biases and Risks
- Medium/Auquan: Backtesting Biases and How To Avoid Them
- TradingShastra: How Backtesting Trading Strategies Actually Work in 2025
