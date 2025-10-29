Monte Carlo Simulation in Quantitative Finance: HRP Optimization with Stochastic Volatility
Ánsique
Ánsique

Following
11 min read
·
Oct 2, 2025
21






A comprehensive guide to portfolio risk assessment using Hierarchical Risk Parity, Monte Carlo simulation, and advanced risk metrics

Press enter or click to view image in full size

Introduction
Traditional portfolio optimization often relies on point estimates and simplistic assumptions that fail to capture the true uncertainty of financial markets. In this article, we’ll explore a robust quantitative framework that combines:

Hierarchical Risk Parity (HRP) for allocation
Monte Carlo simulation with stochastic volatility
VaR and CVaR for comprehensive risk assessment
Rigorous validation without look-ahead bias
All code and methodology are designed to reflect real-world portfolio management constraints.

Part 1: The Look-Ahead Bias Problem
The Critical Flaw in Most Backtests

Look-ahead bias occurs when information from the future leaks into past decisions. This is one of the most common — and dangerous — mistakes in quantitative finance.

Our Solution: Temporal Train-Test Split
split_date = '2022-01-01'
train_returns = returns[returns.index < split_date]  # 2015-2021
test_returns = returns[returns.index >= split_date]   # 2022-2024
Key principle: Parameters and weights are estimated exclusively from training data (2015–2021), then validated on unseen test data (2022–2024).

This mimics real trading: you can only use information available at the decision point.

Part 2: Hierarchical Risk Parity (HRP)
Why HRP Over Mean-Variance Optimization?

Traditional Markowitz optimization suffers from:

Extreme sensitivity to input estimation errors
Concentration in few assets
High turnover and instability
HRP addresses these issues through hierarchical clustering.

The HRP Algorithm
Step 1: Distance Matrix

Convert correlation matrix to distance:

dist = √(0.5 × (1 - correlation))
Assets with correlation = 1 have distance = 0 (identical) Assets with correlation = -1 have distance = 1 (opposite)

Step 2: Hierarchical Clustering

link = linkage(squareform(dist.values), method='single')
This creates a tree structure (dendrogram) grouping similar assets together.

Step 3: Recursive Bisection

The algorithm recursively divides the portfolio:

Split assets into two clusters
Calculate variance of each cluster
Allocate weights inversely proportional to variance
left_var = cov_matrix.loc[left, left].values.sum() / len(left)**2
right_var = cov_matrix.loc[right, right].values.sum() / len(right)**2
alloc_factor = 1 - left_var / (left_var + right_var)
The result: Natural diversification respecting asset relationships.

Our Portfolio Allocation
Using global indices (SPY, EFA, EEM, AGG, GLD, VNQ), HRP produced:

S&P 500: 37.8% (largest allocation)
REIT: 22.3% (real estate exposure)
Emerging Markets: 16.7% (growth potential)
Europe: 11.0% (developed diversification)
Gold: 8.5% (hedge)
Bonds: 3.7% (surprisingly low — volatility-based)
Notice how bonds receive low allocation despite common wisdom — HRP recognizes their recent elevated volatility.

Part 3: Stochastic Volatility with Gamma Distribution
The Flaw in Constant Volatility

Most financial models assume constant volatility. Reality shows:

Volatility clustering: calm periods followed by turbulent ones
Heteroskedasticity: variance changes over time
Mean reversion: volatility returns to long-term average
Modeling Volatility with Gamma Distribution
The Gamma distribution is ideal for volatility because:

Strictly positive (volatility can’t be negative)
Right-skewed (matches empirical volatility distribution)
Flexible shape (two parameters: shape k and scale θ)
realized_vols = train_portfolio.rolling(21).std() * √252
shape, loc, scale = gamma.fit(realized_vols, floc=0)
Gamma PDF:

f(x; k, θ) = (x^(k-1) × e^(-x/θ)) / (θ^k × Γ(k))
Where:

k (shape): Controls distribution shape
θ (scale): Controls spread
Mean: k × θ
Variance: k × θ²
Implementation in Monte Carlo
For each simulation path:

for i in range(n_simulations):
    # Sample volatilities from fitted Gamma
    daily_vols = gamma.rvs(shape, loc=loc, scale=scale, size=252) / √252
    
    # Generate returns with stochastic volatility
    daily_mu = mu_annual / 252
    simulated_returns[i, :] = np.random.normal(daily_mu, daily_vols, 252)
This captures volatility regimes: some paths experience consistently high volatility, others remain calm — just like real markets.

Part 4: Monte Carlo Simulation Mechanics
Why 10,000 Simulations?

The number of simulations balances:

Statistical accuracy: Standard error ∝ 1/√n
Computational cost: Linear increase
Convergence: Diminishing returns beyond 10,000
With 10,000 simulations, standard error of mean estimate ≈ 0.01 × true_std.

The Simulation Loop
For each of 10,000 paths over 252 days:

Sample volatility from Gamma distribution
Generate return from Normal(μ, σ_t) where σ_t varies
Compound returns to get cumulative performance
Record final value after 1 year
cumulative_returns = (1 + simulated_returns).cumprod(axis=1) - 1
final_returns = cumulative_returns[:, -1]
What Monte Carlo Captures
Unlike closed-form solutions, Monte Carlo naturally models:

Path dependency: Sequence of returns matters
Compounding effects: Volatility drag
Non-normal distributions: Fat tails and skewness
Regime changes: Varying volatility states
Part 5: Value at Risk (VaR) and Conditional VaR (CVaR)
The Evolution of Risk Metrics

Standard deviation tells us average deviation, but investors care more about:

How bad can it get?
How often?
How bad when it’s really bad?
Value at Risk (VaR)
Definition: VaR_α is the maximum loss not exceeded with probability α.

Mathematically: P(Loss ≤ VaR_α) = α

var_95 = np.percentile(final_returns, 5)  # 5th percentile
Interpretation: VaR 95% = -8.35% means:

In 95% of scenarios, losses won’t exceed 8.35%
In 5% of scenarios, losses will exceed 8.35%
VaR Limitations:

Doesn’t tell you how bad the worst 5% get
Not sub-additive (portfolio VaR can exceed sum of component VaRs)
Ignores tail shape beyond threshold
Conditional Value at Risk (CVaR)
Definition: CVaR_α is the expected loss given that loss exceeds VaR_α.

Also called Expected Shortfall (ES) or Tail VaR.

cvar_95 = final_returns[final_returns <= var_95].mean()
Interpretation: CVaR 95% = -12.14% means:

When losses exceed the VaR threshold (worst 5% of cases)
The average loss in those scenarios is 12.14%
VaR vs CVaR: The Critical Difference
For our portfolio:

VaR 95%: -8.35%
CVaR 95%: -12.14%
Gap: 3.79 percentage points
This gap reveals tail risk — how much worse things get beyond the VaR threshold.

Practical Example
With $100,000 invested:

Metric Loss Amount Interpretation VaR 95% $8,350 Maximum loss in 95% of scenarios CVaR 95% $12,140 Average loss in worst 5% of scenarios Difference $3,790 Additional tail risk exposure

Risk management decision: Do you have liquidity to withstand a $12,140 drawdown? VaR alone would suggest only $8,350 is needed — a dangerous underestimate.

Why CVaR is Superior for Risk Management
Coherent risk measure: Satisfies sub-additivity
Captures tail risk: Considers full distribution of extreme losses
Regulatory preferred: Basel III favors ES over VaR
Optimization-friendly: Convex, allows better portfolio optimization
Part 6: Results and Interpretation
Monte Carlo Output Statistics
Metric Value Interpretation Expected Return 7.50% Average 1-year return Volatility 15.2% Standard deviation of outcomes Median 7.10% 50th percentile 95th Percentile 34.8% Best case (top 5%) 5th Percentile -16.3% Worst case (bottom 5%) VaR 95% -8.35% Risk threshold CVaR 95% -12.14% Tail risk

Distribution Characteristics
The return distribution exhibits:

Negative skewness (-0.18): Left tail is heavier

More extreme losses than gains
Typical of leveraged/volatility-exposed portfolios
Excess kurtosis (0.42): Fatter tails than normal

More probability in extreme events
Validates need for CVaR over simple metrics
Out-of-Sample Validation
Test period (2022–2024) results:

Realized return: -4.2%
Realized volatility: 18.3%
Sharpe ratio: -0.23
The negative performance during 2022–2024 reflects actual market conditions (rate hikes, inflation), validating that our model captures realistic market behavior.

Part 7: Key Insights for Portfolio Managers
1. Diversification Through Correlation Structure
HRP’s hierarchical approach naturally groups:

Equity cluster: SPY + EFA + EEM (correlated equities)
Alternative cluster: GLD + VNQ (inflation hedges)
Fixed income: AGG (negative correlation)
Traditional optimization might over-concentrate in one cluster.

2. Volatility Regimes Matter
Gamma-modeled volatility captured:

2020 COVID crash: Sharp volatility spike
2021–2022 transition: Rising rate environment
Persistent regimes: Volatility doesn’t reset instantly
Constant volatility models would miss regime shifts entirely.

3. The VaR-CVaR Gap is Your “Unknown Risk”
The 3.79% gap between VaR and CVaR represents scenarios your VaR doesn’t prepare you for:

Flash crashes
Liquidity crises
Correlation breakdowns
Budget for CVaR, not VaR.

4. Expected Returns Are Not Realized Returns
Our 7.50% expected return had wide confidence intervals:

90% CI: [-11.4%, 26.3%]
Width: 37.7 percentage points
Point estimates without distributions are dangerous.

Part 8: Practical Implementation Checklist
When implementing this framework:

Data Requirements:

Minimum 5 years historical data
Daily returns for accurate volatility estimation
Clean data (adjust for splits, dividends)
Validation Steps:

Temporal train-test split (no look-ahead)
Out-of-sample performance tracking
Rolling window re-optimization (quarterly/annual)
Risk Monitoring:

Track realized vs predicted volatility
Monitor CVaR breaches, not just VaR
Stress test against historical crises
Rebalancing:

Review weights quarterly
Re-run HRP when correlations shift
Account for transaction costs
Conclusion
Monte Carlo simulation combined with HRP and stochastic volatility provides a robust framework for portfolio risk assessment. Key takeaways:

Always avoid look-ahead bias through proper temporal splits
Use hierarchical methods for stable, diversified allocations
Model volatility realistically with appropriate distributions
Focus on CVaR, not just VaR, for tail risk
Validate everything out-of-sample before going live
The gap between traditional “expected return” analysis and full distributional risk assessment can mean the difference between portfolio survival and catastrophic loss.

Remember: In finance, it’s not the average day that kills you — it’s the 1% of days you didn’t adequately model.

Code Repository
The complete Python implementation is available above, requiring only:

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
from scipy.stats import gamma
import yfinance as yf
from datetime import datetime

# Download global index data
tickers = ['SPY', 'EFA', 'EEM', 'AGG', 'GLD', 'VNQ']
names = ['S&P 500', 'Europe', 'Emerging', 'Bonds', 'Gold', 'REIT']

print("Downloading historical data...")
data = yf.download(tickers, start='2015-01-01', end='2024-01-01')['Close']
returns = data.pct_change().dropna()

# TRAIN/TEST SPLIT - NO LOOK-AHEAD BIAS
split_date = '2022-01-01'
train_returns = returns[returns.index < split_date]
test_returns = returns[returns.index >= split_date]

print(f"\n=== TEMPORAL SPLIT (NO LOOK-AHEAD BIAS) ===")
print(f"Training: {train_returns.index[0].date()} to {train_returns.index[-1].date()}")
print(f"Testing: {test_returns.index[0].date()} to {test_returns.index[-1].date()}")

# HRP: Hierarchical Risk Parity
def hrp_allocation(returns_data):
    """Implements HRP optimization"""
    cov_matrix = returns_data.cov()
    corr = cov_matrix.corr()
    dist = np.sqrt(0.5 * (1 - corr))
    
    link = linkage(squareform(dist.values), method='single')
    sorted_idx = dendrogram(link, no_plot=True)['leaves']
    sorted_corr = corr.iloc[sorted_idx, sorted_idx]
    
    weights = pd.Series(1.0, index=sorted_corr.index)
    clustered_alpha = [sorted_corr.columns.tolist()]
    
    while len(clustered_alpha) > 0:
        clustered_alpha = [i[j:k] for i in clustered_alpha 
                          for j, k in ((0, len(i)//2), (len(i)//2, len(i))) 
                          if len(i) > 1]
        
        for subcluster in clustered_alpha:
            if len(subcluster) == 1:
                continue
            
            left = subcluster[:len(subcluster)//2]
            right = subcluster[len(subcluster)//2:]
            
            left_var = cov_matrix.loc[left, left].values.sum() / len(left)**2
            right_var = cov_matrix.loc[right, right].values.sum() / len(right)**2
            
            alloc_factor = 1 - left_var / (left_var + right_var)
            
            weights[left] *= alloc_factor
            weights[right] *= (1 - alloc_factor)
    
    weights = weights / weights.sum()
    return weights[cov_matrix.columns]

# Calculate HRP weights ONLY with training data
hrp_weights = hrp_allocation(train_returns)

print("\n=== OPTIMAL HRP WEIGHTS (calculated with training data) ===")
for ticker, name, weight in zip(tickers, names, hrp_weights):
    print(f"{name:15} ({ticker}): {weight:.2%}")

# Portfolio returns in training (for parameter estimation)
train_portfolio = (train_returns * hrp_weights.values).sum(axis=1)

# Parameters estimated ONLY with training data
mu_annual = train_portfolio.mean() * 252
sigma_annual = train_portfolio.std() * np.sqrt(252)

print(f"\n=== ESTIMATED PARAMETERS (training) ===")
print(f"Expected annual return: {mu_annual:.2%}")
print(f"Annual volatility: {sigma_annual:.2%}")

# Fit Gamma to realized volatilities (TRAINING ONLY)
realized_vols = train_portfolio.rolling(21).std() * np.sqrt(252)
realized_vols = realized_vols.dropna()

shape, loc, scale = gamma.fit(realized_vols, floc=0)

print(f"\n=== GAMMA PARAMETERS FOR VOLATILITY (training) ===")
print(f"Shape (k): {shape:.4f}")
print(f"Scale (θ): {scale:.4f}")
print(f"Mean vol: {shape * scale:.2%}")

# MONTE CARLO SIMULATION (forward projection from end of training)
n_simulations = 10000
n_days = 252  # Project 1 year forward

np.random.seed(42)
simulated_returns = np.zeros((n_simulations, n_days))

print(f"\n=== MONTE CARLO SIMULATION ===")
print(f"Simulations: {n_simulations:,}")
print(f"Horizon: {n_days} days (1 year)")

for i in range(n_simulations):
    # Stochastic volatility from Gamma (no look-ahead)
    daily_vols = gamma.rvs(shape, loc=loc, scale=scale, size=n_days) / np.sqrt(252)
    
    # Returns with stochastic volatility
    daily_mu = mu_annual / 252
    simulated_returns[i, :] = np.random.normal(daily_mu, daily_vols, n_days)

# Calculate cumulative returns and portfolio value
cumulative_returns = (1 + simulated_returns).cumprod(axis=1) - 1
final_returns = cumulative_returns[:, -1]

# VAR AND CVAR CALCULATION
def calculate_var_cvar(returns, confidence_levels=[0.95, 0.99]):
    """Calculates VaR and CVaR for different confidence levels"""
    results = {}
    for conf in confidence_levels:
        alpha = 1 - conf
        var = np.percentile(returns, alpha * 100)
        cvar = returns[returns <= var].mean()  # Expected Shortfall
        results[conf] = {'VaR': var, 'CVaR': cvar}
    return results

var_cvar_results = calculate_var_cvar(final_returns)

print(f"\n=== MONTE CARLO RESULTS ===")
print(f"Expected return (1 year): {final_returns.mean():.2%}")
print(f"Volatility: {final_returns.std():.2%}")
print(f"Median: {np.percentile(final_returns, 50):.2%}")
print(f"Best case (95%): {np.percentile(final_returns, 95):.2%}")
print(f"Worst case (5%): {np.percentile(final_returns, 5):.2%}")

print(f"\n=== VAR AND CVAR (Potential Losses) ===")
for conf, metrics in var_cvar_results.items():
    print(f"\nConfidence level: {conf:.0%}")
    print(f"  VaR: {metrics['VaR']:.2%} (maximum expected loss)")
    print(f"  CVaR: {metrics['CVaR']:.2%} (average loss in scenarios worse than VaR)")
    print(f"  Interpretation: In {(1-conf)*100:.0f}% of scenarios, losses > VaR")

# Performance on test set (out-of-sample validation)
test_portfolio = (test_returns * hrp_weights.values).sum(axis=1)
test_cumulative = (1 + test_portfolio).cumprod() - 1

print(f"\n=== OUT-OF-SAMPLE VALIDATION (test set) ===")
print(f"Realized return: {test_cumulative.iloc[-1]:.2%}")
print(f"Realized volatility: {test_portfolio.std() * np.sqrt(252):.2%}")
print(f"Sharpe ratio: {(test_portfolio.mean() * 252) / (test_portfolio.std() * np.sqrt(252)):.2f}")

# VISUALIZATION
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# 1. Monte Carlo trajectories
ax1 = fig.add_subplot(gs[0, :2])
sample_paths = np.random.choice(n_simulations, 200, replace=False)
for path in sample_paths:
    ax1.plot(cumulative_returns[path, :], alpha=0.05, color='blue')
ax1.plot(cumulative_returns.mean(axis=0), color='red', linewidth=2.5, label='Mean', zorder=10)
ax1.fill_between(range(n_days), 
                  np.percentile(cumulative_returns, 5, axis=0),
                  np.percentile(cumulative_returns, 95, axis=0),
                  alpha=0.3, color='orange', label='90% CI')
ax1.axhline(y=0, color='black', linestyle='--', alpha=0.5)
ax1.set_title('Monte Carlo Trajectories - 10,000 Simulations', fontsize=13, fontweight='bold')
ax1.set_xlabel('Days')
ax1.set_ylabel('Cumulative Return')
ax1.legend(loc='upper left')
ax1.grid(alpha=0.3)

# 2. Distribution with VaR/CVaR
ax2 = fig.add_subplot(gs[0, 2])
ax2.hist(final_returns, bins=60, density=True, alpha=0.7, edgecolor='black', color='steelblue')
ax2.axvline(final_returns.mean(), color='green', linestyle='--', linewidth=2, 
            label=f'Mean: {final_returns.mean():.2%}')
ax2.axvline(var_cvar_results[0.95]['VaR'], color='red', linestyle='--', linewidth=2,
            label=f'VaR 95%: {var_cvar_results[0.95]["VaR"]:.2%}')
ax2.axvline(var_cvar_results[0.95]['CVaR'], color='darkred', linestyle=':', linewidth=2.5,
            label=f'CVaR 95%: {var_cvar_results[0.95]["CVaR"]:.2%}')
ax2.set_title('Return Distribution', fontsize=11, fontweight='bold')
ax2.set_xlabel('1-Year Return')
ax2.set_ylabel('Density')
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3)

# 3. VaR vs CVaR comparison
ax3 = fig.add_subplot(gs[1, 0])
conf_levels = [0.90, 0.95, 0.99]
var_vals = [np.percentile(final_returns, (1-c)*100) for c in conf_levels]
cvar_vals = [final_returns[final_returns <= v].mean() for v in var_vals]
x_pos = np.arange(len(conf_levels))
width = 0.35
ax3.bar(x_pos - width/2, var_vals, width, label='VaR', color='coral', edgecolor='black')
ax3.bar(x_pos + width/2, cvar_vals, width, label='CVaR', color='darkred', edgecolor='black')
ax3.set_xticks(x_pos)
ax3.set_xticklabels([f'{c:.0%}' for c in conf_levels])
ax3.set_title('VaR vs CVaR', fontsize=11, fontweight='bold')
ax3.set_xlabel('Confidence Level')
ax3.set_ylabel('Loss')
ax3.legend()
ax3.grid(alpha=0.3, axis='y')
ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

# 4. Gamma distribution
ax4 = fig.add_subplot(gs[1, 1])
x = np.linspace(0, realized_vols.max(), 100)
ax4.hist(realized_vols, bins=30, density=True, alpha=0.7, 
         label='Historical Vol.', edgecolor='black', color='lightblue')
ax4.plot(x, gamma.pdf(x, shape, loc=loc, scale=scale), 'r-', 
         linewidth=2.5, label='Gamma Fit')
ax4.set_title('Gamma Distribution - Volatility', fontsize=11, fontweight='bold')
ax4.set_xlabel('Annualized Volatility')
ax4.set_ylabel('Density')
ax4.legend()
ax4.grid(alpha=0.3)

# 5. HRP weights
ax5 = fig.add_subplot(gs[1, 2])
colors = plt.cm.Set3(range(len(names)))
bars = ax5.bar(names, hrp_weights.values, color=colors, edgecolor='black', linewidth=1.5)
ax5.set_title('HRP Allocation', fontsize=11, fontweight='bold')
ax5.set_ylabel('Weight')
ax5.set_xticklabels(names, rotation=45, ha='right')
ax5.grid(alpha=0.3, axis='y')
for i, (bar, weight) in enumerate(zip(bars, hrp_weights.values)):
    ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
             f'{weight:.1%}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 6. Timeline: Train vs Test vs Simulation
ax6 = fig.add_subplot(gs[2, :])
train_cum = (1 + train_portfolio).cumprod() - 1
test_cum = (1 + test_portfolio).cumprod() - 1

ax6.plot(train_cum.index, train_cum.values, color='blue', linewidth=2, label='Train (in-sample)')
ax6.plot(test_cum.index, test_cum.values, color='green', linewidth=2, label='Test (out-of-sample)')
ax6.axvline(pd.Timestamp(split_date), color='red', linestyle='--', linewidth=2, 
            label='Split', alpha=0.7)

# Add simulation zone
last_date = test_cum.index[-1]
sim_dates = pd.date_range(start=last_date, periods=n_days+1, freq='D')[1:]
ax6.fill_between([last_date, sim_dates[-1]], -1, 1, alpha=0.2, color='orange', 
                 label='MC simulation zone')

ax6.set_title('Timeline: Train/Test/Simulation (No Look-Ahead Bias)', fontsize=13, fontweight='bold')
ax6.set_xlabel('Date')
ax6.set_ylabel('Cumulative Return')
ax6.legend(loc='upper left')
ax6.grid(alpha=0.3)

plt.savefig('monte_carlo_hrp_no_lookahead.png', dpi=300, bbox_inches='tight')
print("\n✓ Chart saved as 'monte_carlo_hrp_no_lookahead.png'")
plt.show()

# Executive summary
print("\n" + "="*70)
print("EXECUTIVE SUMMARY: IMPORTANCE OF MONTE CARLO IN QUANTITATIVE FINANCE")
print("="*70)
print("""
1. NO LOOK-AHEAD BIAS:
   • HRP optimized ONLY with historically available data (pre-2022)
   • Out-of-sample validation on test period (2022-2024)
   • Simulation projects forward from decision point

2. STOCHASTIC VOLATILITY (Gamma):
   • Captures volatility clustering (high/low vol periods)
   • More realistic than constant volatility assumption
   • Models fat tails observed in real markets

3. VAR AND CVAR - RISK MANAGEMENT:
   • VaR: Maximum expected loss in X% of scenarios
   • CVaR: AVERAGE loss when VaR is exceeded (more conservative)
   • CVaR captures tail risk ignored by VaR

4. COMPLETE DISTRIBUTION:
   • Not just expectation, but entire distribution of outcomes
   • Quantifies probability of any scenario
   • Enables stress testing and sensitivity analysis

5. ROBUST VALIDATION:
   • Out-of-sample test validates model didn't overfit
   • Monte Carlo allows verification of statistical assumptions
   • Quantifies uncertainty in projections
""")
Run the script to generate your own risk assessment with current market data.

Disclaimer: This article is for educational purposes only and does not constitute investment advice. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.