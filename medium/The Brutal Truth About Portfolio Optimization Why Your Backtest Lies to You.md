The Brutal Truth About Portfolio Optimization: Why Your Backtest Lies to You
Ánsique
Ánsique

Following
21 min read
·
Oct 5, 2025





Press enter or click to view image in full size

Understanding the In-Sample vs Out-of-Sample Reality in Quantitative Trading
When I ran three sophisticated portfolio optimization strategies — Maximum Sharpe Ratio, Hierarchical Risk Parity (HRP), and Minimum Spanning Tree (MST) — on major world indices, gold, and Bitcoin, the results told a story every quantitative trader must understand: your in-sample performance means almost nothing.

The Max Sharpe strategy returned an eye-watering 350% during the in-sample period (2013–2019), turning $100,000 into $450,000. The MST strategy wasn’t far behind. Both crushed the benchmark.

Then came the out-of-sample period (2020–2023). Reality hit hard. Not only did these strategies fail to replicate their stellar performance — they significantly underperformed a simple buy-and-hold benchmark. The Max Sharpe portfolio that had returned 25.7% annually in-sample actually lost 2.3% per year out-of-sample. This is the overfitting tax, and it’s expensive.

What Is In-Sample vs Out-of-Sample Testing?
The in-sample period is your training data. It’s where you develop your strategy logic, optimize parameters, calibrate your models, and calculate optimal portfolio weights. Think of it as studying for an exam with last year’s test questions. You’ll ace those specific questions, but that doesn’t mean you understand the subject. You’ve memorized answers, not learned principles.

The out-of-sample period is your validation data. It represents completely unseen market conditions, data that never influenced your optimization decisions, the real test of strategy robustness, and what actual future performance might look like. This is the actual exam with new questions. That’s when you discover whether you learned the material or just memorized answers.

The distinction seems obvious when stated plainly, yet the vast majority of traders, even experienced ones, fall into the trap of trusting in-sample results. The reason is psychological: we see what we want to see. When a strategy returns 350% in backtest, our brain floods with dopamine.

The Silent Killer: Overfitting
My Max Sharpe strategy achieved a 4.5x return in-sample. The reason is straightforward but damning: I gave it seven years of data and told it to find the perfect portfolio weights that would have worked best during this specific period. And it did.

The problem is that it found patterns specific to 2013–2019. It learned about the multi-year bull market in US equities, the low volatility in developed markets, Bitcoin’s explosive growth from $13 to $7,000, and the calm before COVID-19. These patterns didn’t repeat in 2020–2023. The strategy, optimized for a world that no longer existed, floundered.

Complex optimization algorithms are pattern-matching machines. Give them enough flexibility, and they’ll find patterns in noise. Those patterns won’t persist because they were never real in the first place. They were statistical artifacts, coincidences elevated to the status of trading signals.

Consider what happens when you test 50 different lookback periods, 10 different rebalancing frequencies, and 20 different weight constraints. You’re not discovering truth — you’re mining for luck. That’s 10,000 combinations. At standard statistical significance levels, around 500 will look spectacular by pure chance. But they’re statistical flukes, not edge. Every parameter you optimize is another opportunity to fool yourself. The more you tune, the less your strategy will generalize.

Also, I wanted to have a Survivorship Bias for this example. So, I selected major world indices, GLD, and BTC-USD for my analysis. Why these specific assets? Because they’re liquid, well-known, and have long histories. But here’s the trap: I know how these performed.

Similarly, the indices I chose survived and thrived. The ones that didn’t aren’t in my dataset. They’re forgotten, delisted, merged, or restructured. You can’t select assets based on hindsight and expect forward-looking results. Yet this is exactly what most backtests do, often without the developer even realizing it.

The Evidence: When Theory Meets Reality
Let me show you the actual numbers from my implementation.

================================================================================
IN-SAMPLE PERFORMANCE (2013-2019)
================================================================================

============================================================
Max Sharpe (IS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                               133.30%
Annual Return                               12.89%
Annual Volatility                           22.27%
Sharpe Ratio                                   0.49
Sortino Ratio                                  0.58
Calmar Ratio                                   0.23
Max Drawdown                               -56.16%
Win Rate                                    43.50%
============================================================

============================================================
HRP (IS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                                26.21%
Annual Return                                3.39%
Annual Volatility                           13.09%
Sharpe Ratio                                   0.11
Sortino Ratio                                  0.13
Calmar Ratio                                   0.09
Max Drawdown                               -35.92%
Win Rate                                    42.65%
============================================================

============================================================
MST (IS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                               126.79%
Annual Return                               12.43%
Annual Volatility                           19.75%
Sharpe Ratio                                   0.53
Sortino Ratio                                  0.65
Calmar Ratio                                   0.24
Max Drawdown                               -51.90%
Win Rate                                    42.48%
============================================================

============================================================
URTH Benchmark (IS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                                70.70%
Annual Return                                7.95%
Annual Volatility                           16.73%
Sharpe Ratio                                   0.36
Sortino Ratio                                  0.46
Calmar Ratio                                   0.38
Max Drawdown                               -21.19%
Win Rate                                    52.24%
============================================================

================================================================================
OUT-OF-SAMPLE PERFORMANCE (2020-2023)
================================================================================

============================================================
Max Sharpe (OOS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                                 3.32%
Annual Return                                0.82%
Annual Volatility                           16.76%
Sharpe Ratio                                  -0.07
Sortino Ratio                                 -0.09
Calmar Ratio                                   0.03
Max Drawdown                               -31.75%
Win Rate                                    35.32%
============================================================

============================================================
HRP (OOS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                                -5.85%
Annual Return                               -1.50%
Annual Volatility                           13.47%
Sharpe Ratio                                  -0.26
Sortino Ratio                                 -0.31
Calmar Ratio                                  -0.05
Max Drawdown                               -32.48%
Win Rate                                    35.22%
============================================================

============================================================
MST (OOS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                                -2.42%
Annual Return                               -0.61%
Annual Volatility                           13.99%
Sharpe Ratio                                  -0.19
Sortino Ratio                                 -0.23
Calmar Ratio                                  -0.02
Max Drawdown                               -36.94%
Win Rate                                    35.12%
============================================================

============================================================
URTH Benchmark (OOS) Performance Metrics
============================================================
Metric                                        Value
------------------------------------------------------------
Total Return                                34.45%
Annual Return                                7.70%
Annual Volatility                           20.63%
Sharpe Ratio                                   0.28
Sortino Ratio                                  0.33
Calmar Ratio                                   0.24
Max Drawdown                               -32.23%
Win Rate                                    55.72%
============================================================
Every single optimized strategy underperformed. Dramatically. The benchmark returned 7.8% annually while every sophisticated, carefully optimized strategy lost money. This wasn’t bad luck. This wasn’t a minor statistical deviation. This is what overfitting looks like in the harsh light of reality.

What Went Wrong?
The market regime changed fundamentally between 2013–2019 and 2020–2023. The first period was characterized by relatively stable growth, low inflation, accommodative monetary policy, and predictable correlations. The second period brought COVID-19, unprecedented monetary policy interventions, supply chain disruptions, inflation spikes to 9%, and the fastest rate hiking cycle in decades.

The calm 2013–2019 period didn’t prepare the optimizers for 2020’s chaos. They were calibrated for one volatility regime and got another. The strategies learned relationships between assets during benign conditions. When volatility spiked and correlations converged during the March 2020 crash, those learned relationships evaporated.

During crises, diversification benefits vanish exactly when you need them most. Assets that normally move independently suddenly move together. The carefully constructed correlation matrices that informed the optimization became obsolete within weeks. Bitcoin, which had provided uncorrelated returns during the in-sample period, became increasingly correlated with tech stocks as it matured into an institutional asset.

The optimization algorithms assumed that the future would resemble the past. This is always a dangerous assumption, but it’s particularly lethal when the past period was unusually benign. The strategies were like generals preparing to fight the last war, perfectly equipped for battles that would never happen again.

Press enter or click to view image in full size

How to Properly Implement Portfolio Strategies
The first critical practice is walk-forward testing. Don’t optimize once on all in-sample data and call it done. Instead, for each rebalance date in the out-of-sample period, use only past data in either an expanding or rolling window, re-optimize portfolio weights based on that historical data alone, execute with realistic assumptions, and then move to the next rebalance date. This mimics real-world deployment where you continuously re-optimize with new data.

Realistic execution assumptions separate professional implementations from amateur backtests. My system includes a signal-to-execution lag where signals are generated at Close[t] but execution happens at Open[t+1]. There’s no ability to trade on same-day closing prices. Transaction costs of 10 basis points per trade are applied to turnover, representing the absolute value of position changes. This seemingly small detail reduces performance by 0.5–2% annually, which is often the difference between a profitable and unprofitable strategy.

Look-ahead bias is insidious because it’s easy to introduce accidentally. Using future data in your calculations, even unknowingly, will produce spectacular backtests and disastrous live results. The correct approach requires ensuring that at each decision point, you only use data that would have been available at that time. This means using the previous close, not the current close, when generating signals.

Unconstrained optimization finds unstable solutions that look great in backtest but collapse in live trading. Adding realistic constraints helps. Position limits prevent concentration risk — no more than 30% in any single asset, for example. Turnover limits prevent excessive trading that generates costs without adding value. Leverage limits keep you from taking risks that seem optimal in backtest but are catastrophic when they fail.

The key insight is that these constraints reduce overfitting by preventing extreme positions. An unconstrained optimizer might put 90% of your portfolio in the single best-performing asset from the training period. This will produce amazing backtests and terrible forward results. Constraints force diversification and stability.

Validation Protocols That Actually Work
Creating a strict firewall between development and testing is essential. Your development set, comprising 50–70% of your data, is where you develop strategy logic, set reasonable parameter ranges, and do initial debugging. Your validation set, another 15–25% of data, is where you tune parameters, compare alternative approaches, and refine execution rules. Your test set, the final 15–25%, should be used only once for final performance evaluation with no changes allowed after viewing results.

Once you look at test set performance and make changes based on what you see, it’s no longer a test set — it’s contaminated. It becomes part of your training data. The only way to get an unbiased estimate of future performance is to look at the test set exactly once, after all development decisions are finalized.

Don’t rely on a single out-of-sample period. Test across multiple different time periods like 2008–2010, 2015–2017, and 2020–2022. Test across different market regimes including bull markets, bear markets, and high volatility periods. Test across different asset universes such as large cap, small cap, and international markets. If your strategy only works in one specific period, it’s overfit to that period’s peculiarities.

Statistical Significance and Reality
A strategy that outperforms by 2% annually could easily be luck rather than skill. Bootstrap resampling provides one way to test this. Resample returns with replacement 10,000 times, calculate performance metrics for each sample, and build confidence intervals. If your 95% confidence interval for excess return includes zero, you don’t have edge — you have noise.

Permutation tests offer another approach. Randomly shuffle return labels, recalculate performance, compare to actual performance, and determine the p-value. If your strategy’s performance isn’t statistically significant at the 0.05 level, it’s likely random. This is a high bar, but it’s the appropriate bar. Markets are competitive and efficient enough that true edge is rare.

The harsh reality that most traders don’t want to hear is that 70–80% of promising strategies fail out-of-sample. Of the 20–30% that pass initial validation, most disappear within 2–3 years as markets adapt and the edge decays. True edge is rare, small, and degrades over time. This isn’t pessimism — it’s honesty based on decades of quantitative research.

What Actually Works?
After extensive research and painful experience, certain approaches have proven more robust than others. Diversification across uncorrelated assets provides genuine risk reduction that persists out-of-sample. Systematic rebalancing captures mean reversion without requiring return forecasts. Risk parity approaches like HRP manage volatility rather than chasing returns, which is often sufficient for good performance.

The Bottom Line
The difference between in-sample and out-of-sample performance isn’t a technical detail — it’s the difference between fantasy and reality. My Max Sharpe strategy returned 350% in-sample and lost money out-of-sample. This isn’t an exception. This isn’t an outlier. This is the norm when optimization meets reality.

Here is the code:

"""
Portfolio Optimization Strategies: Max Sharpe, HRP, and MST
============================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import requests
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION PARAMETERS - ALL CONFIGURABLE
# ============================================================================

class Config:
    """Configuration class to hold all adjustable parameters"""
    
    # API Configuration
    FMP_API_KEY = "FMMP_API_KEY"
    
    # Assets to trade - Major world indices + GLD + BTC
    TICKERS = [
        'SPY',      # S&P 500 (US)
        'EFA',      # MSCI EAFE (Developed Markets ex-US)
        'EEM',      # MSCI Emerging Markets
        'VGK',      # MSCI Europe
        'VPL',      # MSCI Pacific
        'EWJ',      # Japan
        'FXI',      # China Large Cap
        'GLD',      # Gold
        'BTC-USD'   # Bitcoin
    ]
    
    # Benchmark
    BENCHMARK_TICKER = 'URTH'  # MSCI World Index
    
    # Time periods
    IS_START = '2013-01-01'  # In-Sample start
    IS_END = '2019-12-31'    # In-Sample end
    OOS_START = '2020-01-01' # Out-of-Sample start
    OOS_END = '2023-12-31'   # Out-of-Sample end
    
    # Trading parameters
    COMMISSION_RATE = 0.001  # 10 bps per trade (0.1%)
    INITIAL_CAPITAL = 100000  # Starting capital in USD
    REBALANCE_FREQUENCY = 'Q'  # Quarterly rebalancing ('M'=monthly, 'Q'=quarterly, 'Y'=yearly)
    
    # Portfolio optimization parameters
    RISK_FREE_RATE = 0.02  # Annual risk-free rate (2%)
    MAX_WEIGHT = 0.30      # Maximum weight per asset (30%)
    MIN_WEIGHT = 0.00      # Minimum weight per asset (0%)
    
    # Lookback periods for optimization (in trading days)
    LOOKBACK_DAYS = 252    # 1 year of data for optimization
    
    # Plot styling
    FIGSIZE = (15, 10)
    DPI = 100
    STYLE = 'seaborn-v0_8-darkgrid'


# ============================================================================
# DATA ACQUISITION MODULE
# ============================================================================

class DataFetcher:
    """Handles all data fetching from FMP API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def fetch_historical_data(self, ticker, start_date, end_date):
        """
        Fetch historical OHLCV data from FMP API
        
        Parameters:
        -----------
        ticker : str
            Stock/ETF ticker symbol
        start_date : str
            Start date in 'YYYY-MM-DD' format
        end_date : str
            End date in 'YYYY-MM-DD' format
        
        Returns:
        --------
        pd.DataFrame
            DataFrame with Date index and OHLCV columns
        
        Notes:
        ------
        - Uses actual API data only, no synthetic fallbacks
        - Handles BTC-USD special case for crypto ticker format
        """
        print(f"Fetching data for {ticker}...")
        
        # Special handling for Bitcoin - FMP uses BTCUSD format
        api_ticker = ticker.replace('-', '')
        
        url = f"{self.base_url}/historical-price-full/{api_ticker}"
        params = {
            'from': start_date,
            'to': end_date,
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'historical' not in data or len(data['historical']) == 0:
                print(f"WARNING: No data available for {ticker}")
                return None
            
            df = pd.DataFrame(data['historical'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # Keep only OHLCV columns
            df = df[['open', 'high', 'low', 'close', 'volume']]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            
            print(f"Successfully fetched {len(df)} records for {ticker}")
            return df
            
        except Exception as e:
            print(f"ERROR fetching {ticker}: {str(e)}")
            return None
    
    def fetch_multiple_tickers(self, tickers, start_date, end_date):
        """
        Fetch data for multiple tickers and combine into panel structure
        
        Returns:
        --------
        dict of pd.DataFrame
            Dictionary with 'Open' and 'Close' DataFrames containing all tickers
        """
        all_data = {}
        
        for ticker in tickers:
            df = self.fetch_historical_data(ticker, start_date, end_date)
            if df is not None:
                all_data[ticker] = df
        
        if len(all_data) == 0:
            raise ValueError("No data was successfully fetched for any ticker")
        
        # Combine into price matrices
        open_prices = pd.DataFrame({ticker: df['Open'] for ticker, df in all_data.items()})
        close_prices = pd.DataFrame({ticker: df['Close'] for ticker, df in all_data.items()})
        
        # Drop any dates where we have missing data for any ticker
        # This ensures we only trade when we have complete information
        open_prices = open_prices.dropna()
        close_prices = close_prices.dropna()
        
        print(f"\nSuccessfully combined data for {len(all_data)} tickers")
        print(f"Date range: {open_prices.index[0]} to {open_prices.index[-1]}")
        print(f"Total trading days: {len(open_prices)}")
        
        return {
            'open': open_prices,
            'close': close_prices
        }


# ============================================================================
# PORTFOLIO OPTIMIZATION STRATEGIES
# ============================================================================

class MaxSharpeOptimizer:
    """
    Maximum Sharpe Ratio Portfolio Optimizer
    
    Classic mean-variance optimization that maximizes the Sharpe ratio
    subject to weight constraints.
    """
    
    def __init__(self, risk_free_rate=0.02, max_weight=0.30, min_weight=0.00):
        self.risk_free_rate = risk_free_rate
        self.max_weight = max_weight
        self.min_weight = min_weight
    
    def optimize(self, returns):
        """
        Find portfolio weights that maximize Sharpe ratio
        
        Parameters:
        -----------
        returns : pd.DataFrame
            Historical returns (T-1 to T perspective, no look-ahead)
        
        Returns:
        --------
        np.array
            Optimal portfolio weights
        """
        n_assets = returns.shape[1]
        
        # Calculate expected returns and covariance matrix
        # Using historical mean as expected return (simple approach)
        mean_returns = returns.mean() * 252  # Annualized
        cov_matrix = returns.cov() * 252     # Annualized
        
        # Objective function: negative Sharpe ratio (we minimize)
        def neg_sharpe(weights):
            port_return = np.dot(weights, mean_returns)
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe = (port_return - self.risk_free_rate) / port_vol
            return -sharpe
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # Bounds: min_weight <= weight <= max_weight
        bounds = tuple((self.min_weight, self.max_weight) for _ in range(n_assets))
        
        # Initial guess: equal weight
        init_weights = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            neg_sharpe,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if not result.success:
            print(f"WARNING: Optimization did not converge. Using equal weights.")
            return init_weights
        
        return result.x


class HRPOptimizer:
    """
    Hierarchical Risk Parity Portfolio Optimizer
    
    Uses hierarchical clustering to build a diversified portfolio
    that doesn't rely on matrix inversion (more stable than mean-variance).
    """
    
    def __init__(self):
        pass
    
    def optimize(self, returns):
        """
        Calculate HRP weights using hierarchical clustering
        
        Parameters:
        -----------
        returns : pd.DataFrame
            Historical returns
        
        Returns:
        --------
        np.array
            HRP portfolio weights
        """
        # Calculate correlation matrix
        corr_matrix = returns.corr()
        
        # Convert correlation to distance metric
        dist_matrix = np.sqrt(0.5 * (1 - corr_matrix))
        
        # Perform hierarchical clustering
        dist_condensed = squareform(dist_matrix, checks=False)
        link = linkage(dist_condensed, method='single')
        
        # Get quasi-diagonalization order
        sort_ix = self._get_quasi_diag(link)
        
        # Recursive bisection to get weights
        weights = pd.Series(1.0, index=returns.columns)
        cluster_items = [returns.columns[i] for i in sort_ix]
        weights = self._get_recursive_bisection(returns, corr_matrix, cluster_items)
        
        return weights.values
    
    def _get_quasi_diag(self, link):
        """Get quasi-diagonalization order from linkage matrix"""
        link = link.astype(int)
        sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
        num_items = link[-1, 3]
        
        while sort_ix.max() >= num_items:
            sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
            df0 = sort_ix[sort_ix >= num_items]
            i = df0.index
            j = df0.values - num_items
            sort_ix[i] = link[j, 0]
            df0 = pd.Series(link[j, 1], index=i + 1)
            sort_ix = pd.concat([sort_ix, df0])
            sort_ix = sort_ix.sort_index()
            sort_ix.index = range(sort_ix.shape[0])
        
        return sort_ix.tolist()
    
    def _get_cluster_var(self, returns, corr_matrix, cluster_items):
        """Calculate variance of a cluster"""
        cov_slice = returns[cluster_items].cov()
        weights = self._get_inverse_variance_weights(np.diag(cov_slice))
        cluster_var = np.dot(weights.T, np.dot(cov_slice, weights))
        return cluster_var
    
    def _get_inverse_variance_weights(self, variances):
        """Calculate inverse variance weights"""
        inv_var = 1.0 / variances
        weights = inv_var / inv_var.sum()
        return weights
    
    def _get_recursive_bisection(self, returns, corr_matrix, items):
        """Recursive bisection to allocate weights"""
        weights = pd.Series(1.0, index=items)
        
        if len(items) == 1:
            return weights
        
        # Split items into two clusters
        split_point = len(items) // 2
        cluster1 = items[:split_point]
        cluster2 = items[split_point:]
        
        # Calculate cluster variances
        var1 = self._get_cluster_var(returns, corr_matrix, cluster1)
        var2 = self._get_cluster_var(returns, corr_matrix, cluster2)
        
        # Allocate weight inversely proportional to variance
        alpha = 1 - var1 / (var1 + var2)
        
        # Recursively allocate within clusters
        weights[cluster1] *= alpha
        weights[cluster2] *= (1 - alpha)
        
        if len(cluster1) > 1:
            sub_weights1 = self._get_recursive_bisection(returns, corr_matrix, cluster1)
            for item in cluster1:
                weights[item] *= sub_weights1[item]
        
        if len(cluster2) > 1:
            sub_weights2 = self._get_recursive_bisection(returns, corr_matrix, cluster2)
            for item in cluster2:
                weights[item] *= sub_weights2[item]
        
        return weights


class MSTOptimizer:
    """
    Minimum Spanning Tree Portfolio Optimizer
    
    Uses graph theory (MST) to identify asset relationships and
    build a diversified portfolio based on the tree structure.
    """
    
    def __init__(self):
        pass
    
    def optimize(self, returns):
        """
        Calculate MST-based weights
        
        Parameters:
        -----------
        returns : pd.DataFrame
            Historical returns
        
        Returns:
        --------
        np.array
            MST portfolio weights
        """
        # Calculate correlation matrix
        corr_matrix = returns.corr()
        
        # Convert to distance matrix (1 - correlation for positive definition)
        dist_matrix = 1 - corr_matrix.abs()
        
        # Build MST using Kruskal's algorithm
        mst = self._build_mst(dist_matrix)
        
        # Calculate centrality scores
        centrality = self._calculate_centrality(mst)
        
        # Inverse centrality for weights (less central = more weight for diversification)
        inv_centrality = 1.0 / (centrality + 1e-6)  # Add small value to avoid division by zero
        weights = inv_centrality / inv_centrality.sum()
        
        return weights.values
    
    def _build_mst(self, dist_matrix):
        """
        Build Minimum Spanning Tree using distance matrix
        
        Returns adjacency matrix representation of MST
        """
        n = len(dist_matrix)
        assets = dist_matrix.index.tolist()
        
        # Initialize MST adjacency matrix
        mst = pd.DataFrame(0, index=assets, columns=assets)
        
        # Kruskal's algorithm
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                edges.append((dist_matrix.iloc[i, j], assets[i], assets[j]))
        
        edges.sort()  # Sort by distance
        
        # Union-Find data structure
        parent = {asset: asset for asset in assets}
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
                return True
            return False
        
        # Build MST
        for dist, u, v in edges:
            if union(u, v):
                mst.loc[u, v] = 1
                mst.loc[v, u] = 1
        
        return mst
    
    def _calculate_centrality(self, mst):
        """
        Calculate degree centrality (number of connections) for each node
        
        Higher centrality = more connected = potentially more correlated
        """
        centrality = mst.sum(axis=1)
        return centrality


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class Backtester:
    """
    Backtesting engine that simulates trading with realistic execution
    
    Key features:
    - Signal at Close[t], Execute at Open[t+1]
    - Portfolio valued at Open[t+1]
    - Returns = Open[t+2]/Open[t+1] - 1
    - Transaction costs applied
    - No look-ahead bias
    """
    
    def __init__(self, optimizer, price_data, config):
        """
        Parameters:
        -----------
        optimizer : object
            Portfolio optimizer (MaxSharpe, HRP, or MST)
        price_data : dict
            Dictionary with 'open' and 'close' price DataFrames
        config : Config
            Configuration object with all parameters
        """
        self.optimizer = optimizer
        self.open_prices = price_data['open']
        self.close_prices = price_data['close']
        self.config = config
        
    def run_backtest(self, start_date, end_date, lookback_days=252):
        """
        Run backtest for specified period
        
        Parameters:
        -----------
        start_date : str
            Backtest start date
        end_date : str
            Backtest end date
        lookback_days : int
            Number of days to look back for optimization
        
        Returns:
        --------
        pd.DataFrame
            Backtest results with portfolio value, weights, returns, etc.
        """
        # Filter data for backtest period
        close_bt = self.close_prices[start_date:end_date]
        open_bt = self.open_prices[start_date:end_date]
        
        # Initialize results storage
        results = []
        portfolio_value = self.config.INITIAL_CAPITAL
        current_weights = None
        previous_shares = None
        
        # Get rebalance dates
        rebalance_dates = self._get_rebalance_dates(close_bt, self.config.REBALANCE_FREQUENCY)
        
        print(f"\nRunning backtest from {start_date} to {end_date}")
        print(f"Rebalancing {self.config.REBALANCE_FREQUENCY}ly - {len(rebalance_dates)} rebalances")
        
        for i, date in enumerate(open_bt.index):
            # Check if we need to rebalance
            # Signal generated at previous close, executed at today's open
            if i == 0 or date in rebalance_dates:
                # Get historical data up to PREVIOUS close for optimization
                # This ensures no look-ahead bias (we only know yesterday's close)
                if i == 0:
                    hist_start_idx = max(0, i - lookback_days)
                else:
                    hist_start_idx = max(0, i - 1 - lookback_days)
                
                hist_end_idx = i - 1 if i > 0 else 0
                
                if hist_end_idx >= lookback_days:
                    # Get historical close prices for return calculation
                    hist_closes = close_bt.iloc[hist_start_idx:hist_end_idx + 1]
                    
                    # Calculate returns (close-to-close returns using T-1 to T)
                    hist_returns = hist_closes.pct_change().dropna()
                    
                    if len(hist_returns) >= 20:  # Minimum data requirement
                        # Optimize portfolio weights
                        new_weights = self.optimizer.optimize(hist_returns)
                        
                        # Execute rebalance at today's open
                        open_prices_today = open_bt.iloc[i]
                        new_shares = (portfolio_value * new_weights) / open_prices_today
                        
                        # Calculate transaction costs
                        if previous_shares is not None:
                            trades = np.abs(new_shares - previous_shares) * open_prices_today
                            transaction_cost = trades.sum() * self.config.COMMISSION_RATE
                            portfolio_value -= transaction_cost
                            
                            # Recalculate shares after transaction costs
                            new_shares = (portfolio_value * new_weights) / open_prices_today
                        
                        current_weights = new_weights
                        previous_shares = new_shares
                    else:
                        # Not enough data, keep previous weights or use equal weight
                        if current_weights is None:
                            current_weights = np.array([1/len(open_bt.columns)] * len(open_bt.columns))
                            open_prices_today = open_bt.iloc[i]
                            previous_shares = (portfolio_value * current_weights) / open_prices_today
            
            # Value portfolio at today's open
            if current_weights is not None and previous_shares is not None:
                open_prices_today = open_bt.iloc[i]
                portfolio_value = (previous_shares * open_prices_today).sum()
            
            # Record results
            results.append({
                'Date': date,
                'Portfolio_Value': portfolio_value,
                **{f'Weight_{ticker}': w for ticker, w in zip(open_bt.columns, current_weights if current_weights is not None else [0]*len(open_bt.columns))}
            })
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        results_df.set_index('Date', inplace=True)
        
        # Calculate portfolio returns (Open[t+1] / Open[t] - 1)
        results_df['Returns'] = results_df['Portfolio_Value'].pct_change()
        
        return results_df
    
    def _get_rebalance_dates(self, price_data, frequency):
        """
        Get rebalance dates based on frequency
        
        Parameters:
        -----------
        price_data : pd.DataFrame
            Price data with datetime index
        frequency : str
            'M' for monthly, 'Q' for quarterly, 'Y' for yearly
        
        Returns:
        --------
        list
            List of rebalance dates
        """
        if frequency == 'M':
            return price_data.resample('M').last().index.tolist()
        elif frequency == 'Q':
            return price_data.resample('Q').last().index.tolist()
        elif frequency == 'Y':
            return price_data.resample('Y').last().index.tolist()
        else:
            raise ValueError(f"Unknown frequency: {frequency}")


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

class PerformanceAnalyzer:
    """Calculate and display performance metrics"""
    
    @staticmethod
    def calculate_metrics(returns, risk_free_rate=0.02):
        """
        Calculate comprehensive performance metrics
        
        Parameters:
        -----------
        returns : pd.Series
            Strategy returns
        risk_free_rate : float
            Annual risk-free rate
        
        Returns:
        --------
        dict
            Dictionary of performance metrics
        """
        # Remove NaN values
        returns = returns.dropna()
        
        # Annualized return
        total_return = (1 + returns).prod() - 1
        n_years = len(returns) / 252
        annual_return = (1 + total_return) ** (1 / n_years) - 1
        
        # Annualized volatility
        annual_vol = returns.std() * np.sqrt(252)
        
        # Sharpe ratio
        sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252)
        sortino = (annual_return - risk_free_rate) / downside_vol if downside_vol > 0 else 0
        
        # Calmar ratio
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Win rate
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
        
        return {
            'Total Return': total_return,
            'Annual Return': annual_return,
            'Annual Volatility': annual_vol,
            'Sharpe Ratio': sharpe,
            'Sortino Ratio': sortino,
            'Calmar Ratio': calmar,
            'Max Drawdown': max_drawdown,
            'Win Rate': win_rate
        }
    
    @staticmethod
    def print_metrics(metrics, strategy_name):
        """Print metrics in a formatted table"""
        print(f"\n{'='*60}")
        print(f"{strategy_name} Performance Metrics")
        print(f"{'='*60}")
        print(f"{'Metric':<30} {'Value':>20}")
        print(f"{'-'*60}")
        for metric, value in metrics.items():
            if 'Return' in metric or 'Volatility' in metric or 'Drawdown' in metric or 'Rate' in metric:
                print(f"{metric:<30} {value:>19.2%}")
            else:
                print(f"{metric:<30} {value:>20.2f}")
        print(f"{'='*60}")


# ============================================================================
# VISUALIZATION
# ============================================================================

class Visualizer:
    """Create visualizations for backtest results"""
    
    @staticmethod
    def plot_equity_curves(results_dict, benchmark_results, config):
        """
        Plot equity curves for all strategies vs benchmark
        
        Parameters:
        -----------
        results_dict : dict
            Dictionary with strategy names as keys and results DataFrames as values
        benchmark_results : pd.DataFrame
            Benchmark results
        config : Config
            Configuration object
        """
        plt.style.use(config.STYLE)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=config.FIGSIZE, dpi=config.DPI)
        
        # Plot 1: Equity curves
        for strategy_name, results in results_dict.items():
            normalized = results['Portfolio_Value'] / config.INITIAL_CAPITAL
            ax1.plot(results.index, normalized, label=strategy_name, linewidth=2)
        
        # Plot benchmark
        benchmark_normalized = benchmark_results['Portfolio_Value'] / config.INITIAL_CAPITAL
        ax1.plot(benchmark_results.index, benchmark_normalized, 
                label=config.BENCHMARK_TICKER, linewidth=2, linestyle='--', color='black', alpha=0.7)
        
        ax1.set_title('Portfolio Equity Curves (Normalized to 1.0)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Portfolio Value (Normalized)', fontsize=12)
        ax1.legend(loc='best', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Drawdown
        for strategy_name, results in results_dict.items():
            cumulative = results['Portfolio_Value'] / config.INITIAL_CAPITAL
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            ax2.fill_between(results.index, drawdown * 100, 0, alpha=0.3, label=strategy_name)
        
        # Benchmark drawdown
        cumulative_bm = benchmark_normalized
        running_max_bm = cumulative_bm.expanding().max()
        drawdown_bm = (cumulative_bm - running_max_bm) / running_max_bm
        ax2.fill_between(benchmark_results.index, drawdown_bm * 100, 0, 
                         alpha=0.2, color='black', label=config.BENCHMARK_TICKER)
        
        ax2.set_title('Drawdown Analysis', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def plot_weights_evolution(results, strategy_name, config):
        """
        Plot evolution of portfolio weights over time
        
        Parameters:
        -----------
        results : pd.DataFrame
            Backtest results with weight columns
        strategy_name : str
            Name of the strategy
        config : Config
            Configuration object
        """
        plt.style.use(config.STYLE)
        fig, ax = plt.subplots(figsize=config.FIGSIZE, dpi=config.DPI)
        
        # Extract weight columns
        weight_cols = [col for col in results.columns if col.startswith('Weight_')]
        weights_df = results[weight_cols]
        weights_df.columns = [col.replace('Weight_', '') for col in weight_cols]
        
        # Stack area plot
        ax.stackplot(results.index, *[weights_df[col] * 100 for col in weights_df.columns],
                    labels=weights_df.columns, alpha=0.7)
        
        ax.set_title(f'{strategy_name} - Portfolio Weights Evolution', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Weight (%)', fontsize=12)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 100])
        
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def plot_returns_distribution(results_dict, benchmark_results, config):
        """
        Plot returns distribution for all strategies
        
        Parameters:
        -----------
        results_dict : dict
            Dictionary with strategy results
        benchmark_results : pd.DataFrame
            Benchmark results
        config : Config
            Configuration object
        """
        plt.style.use(config.STYLE)
        fig, axes = plt.subplots(2, 2, figsize=config.FIGSIZE, dpi=config.DPI)
        axes = axes.flatten()
        
        strategies = list(results_dict.keys()) + [config.BENCHMARK_TICKER]
        all_results = list(results_dict.values()) + [benchmark_results]
        
        for idx, (strategy_name, results) in enumerate(zip(strategies, all_results)):
            if idx < len(axes):
                returns = results['Returns'].dropna() * 100  # Convert to percentage
                
                axes[idx].hist(returns, bins=50, alpha=0.7, edgecolor='black')
                axes[idx].axvline(returns.mean(), color='red', linestyle='--', 
                                linewidth=2, label=f'Mean: {returns.mean():.2f}%')
                axes[idx].axvline(0, color='black', linestyle='-', linewidth=1)
                
                axes[idx].set_title(f'{strategy_name} Returns Distribution', fontsize=12, fontweight='bold')
                axes[idx].set_xlabel('Daily Returns (%)', fontsize=10)
                axes[idx].set_ylabel('Frequency', fontsize=10)
                axes[idx].legend(fontsize=9)
                axes[idx].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    
    print("="*80)
    print("PORTFOLIO OPTIMIZATION STRATEGIES: MAX SHARPE, HRP, MST")
    print("="*80)
    
    # Initialize configuration
    config = Config()
    
    print("\nConfiguration:")
    print(f"  Tickers: {', '.join(config.TICKERS)}")
    print(f"  Benchmark: {config.BENCHMARK_TICKER}")
    print(f"  In-Sample: {config.IS_START} to {config.IS_END}")
    print(f"  Out-of-Sample: {config.OOS_START} to {config.OOS_END}")
    print(f"  Rebalancing: {config.REBALANCE_FREQUENCY}ly")
    print(f"  Commission: {config.COMMISSION_RATE*100:.1f} bps per trade")
    
    # Step 1: Fetch data
    print("\n" + "="*80)
    print("STEP 1: FETCHING DATA FROM FMP API")
    print("="*80)
    
    fetcher = DataFetcher(config.FMP_API_KEY)
    
    # Get extended date range to ensure we have enough lookback data
    extended_start = '2012-01-01'  # Extra year for lookback
    data = fetcher.fetch_multiple_tickers(
        config.TICKERS, 
        extended_start, 
        config.OOS_END
    )
    
    # Fetch benchmark data
    print("\nFetching benchmark data...")
    benchmark_data = fetcher.fetch_multiple_tickers(
        [config.BENCHMARK_TICKER],
        extended_start,
        config.OOS_END
    )
    
    # Step 2: Initialize optimizers
    print("\n" + "="*80)
    print("STEP 2: INITIALIZING OPTIMIZERS")
    print("="*80)
    
    optimizers = {
        'Max Sharpe': MaxSharpeOptimizer(
            risk_free_rate=config.RISK_FREE_RATE,
            max_weight=config.MAX_WEIGHT,
            min_weight=config.MIN_WEIGHT
        ),
        'HRP': HRPOptimizer(),
        'MST': MSTOptimizer()
    }
    
    print(f"Initialized {len(optimizers)} optimizers: {', '.join(optimizers.keys())}")
    
    # Step 3: Run backtests
    print("\n" + "="*80)
    print("STEP 3: RUNNING BACKTESTS")
    print("="*80)
    
    # In-Sample results
    is_results = {}
    for strategy_name, optimizer in optimizers.items():
        print(f"\n--- {strategy_name} (In-Sample) ---")
        backtester = Backtester(optimizer, data, config)
        results = backtester.run_backtest(
            config.IS_START, 
            config.IS_END,
            lookback_days=config.LOOKBACK_DAYS
        )
        is_results[strategy_name] = results
    
    # Out-of-Sample results
    oos_results = {}
    for strategy_name, optimizer in optimizers.items():
        print(f"\n--- {strategy_name} (Out-of-Sample) ---")
        backtester = Backtester(optimizer, data, config)
        results = backtester.run_backtest(
            config.OOS_START,
            config.OOS_END,
            lookback_days=config.LOOKBACK_DAYS
        )
        oos_results[strategy_name] = results
    
    # Benchmark backtests
    print("\n--- Benchmark (In-Sample) ---")
    # Create simple buy-and-hold strategy for benchmark
    # Extract the Series from the DataFrame (benchmark has only one column)
    bm_is_prices = benchmark_data['open'].loc[config.IS_START:config.IS_END, config.BENCHMARK_TICKER].copy()
    bm_is_results = pd.DataFrame({
        'Portfolio_Value': (bm_is_prices / bm_is_prices.iloc[0]) * config.INITIAL_CAPITAL,
        'Returns': bm_is_prices.pct_change()
    }, index=bm_is_prices.index)
    
    print("\n--- Benchmark (Out-of-Sample) ---")
    bm_oos_prices = benchmark_data['open'].loc[config.OOS_START:config.OOS_END, config.BENCHMARK_TICKER].copy()
    bm_oos_results = pd.DataFrame({
        'Portfolio_Value': (bm_oos_prices / bm_oos_prices.iloc[0]) * config.INITIAL_CAPITAL,
        'Returns': bm_oos_prices.pct_change()
    }, index=bm_oos_prices.index)
    
    # Step 4: Calculate and display performance metrics
    print("\n" + "="*80)
    print("STEP 4: PERFORMANCE ANALYSIS")
    print("="*80)
    
    analyzer = PerformanceAnalyzer()
    
    print("\n" + "="*80)
    print("IN-SAMPLE PERFORMANCE (2013-2019)")
    print("="*80)
    
    is_metrics = {}
    for strategy_name, results in is_results.items():
        metrics = analyzer.calculate_metrics(results['Returns'], config.RISK_FREE_RATE)
        is_metrics[strategy_name] = metrics
        analyzer.print_metrics(metrics, f"{strategy_name} (IS)")
    
    # Benchmark IS metrics
    bm_is_metrics = analyzer.calculate_metrics(bm_is_results['Returns'], config.RISK_FREE_RATE)
    analyzer.print_metrics(bm_is_metrics, f"{config.BENCHMARK_TICKER} Benchmark (IS)")
    
    print("\n" + "="*80)
    print("OUT-OF-SAMPLE PERFORMANCE (2020-2023)")
    print("="*80)
    
    oos_metrics = {}
    for strategy_name, results in oos_results.items():
        metrics = analyzer.calculate_metrics(results['Returns'], config.RISK_FREE_RATE)
        oos_metrics[strategy_name] = metrics
        analyzer.print_metrics(metrics, f"{strategy_name} (OOS)")
    
    # Benchmark OOS metrics
    bm_oos_metrics = analyzer.calculate_metrics(bm_oos_results['Returns'], config.RISK_FREE_RATE)
    analyzer.print_metrics(bm_oos_metrics, f"{config.BENCHMARK_TICKER} Benchmark (OOS)")
    
    # Step 5: Create visualizations
    print("\n" + "="*80)
    print("STEP 5: GENERATING VISUALIZATIONS")
    print("="*80)
    
    visualizer = Visualizer()
    
    # In-Sample visualizations
    print("\nGenerating In-Sample equity curves...")
    visualizer.plot_equity_curves(is_results, bm_is_results, config)
    
    print("\nGenerating Out-of-Sample equity curves...")
    visualizer.plot_equity_curves(oos_results, bm_oos_results, config)
    
    print("\nGenerating returns distributions...")
    visualizer.plot_returns_distribution(oos_results, bm_oos_results, config)
    
    # Weight evolution plots
    for strategy_name, results in oos_results.items():
        print(f"\nGenerating weight evolution for {strategy_name}...")
        visualizer.plot_weights_evolution(results, f"{strategy_name} (OOS)", config)
    
    # Step 6: Summary comparison table
    print("\n" + "="*80)
    print("COMPARATIVE SUMMARY")
    print("="*80)
    
    summary_data = []
    for strategy_name in optimizers.keys():
        summary_data.append({
            'Strategy': strategy_name,
            'IS Return': is_metrics[strategy_name]['Annual Return'],
            'IS Sharpe': is_metrics[strategy_name]['Sharpe Ratio'],
            'IS Max DD': is_metrics[strategy_name]['Max Drawdown'],
            'OOS Return': oos_metrics[strategy_name]['Annual Return'],
            'OOS Sharpe': oos_metrics[strategy_name]['Sharpe Ratio'],
            'OOS Max DD': oos_metrics[strategy_name]['Max Drawdown']
        })
    
    # Add benchmark
    summary_data.append({
        'Strategy': config.BENCHMARK_TICKER,
        'IS Return': bm_is_metrics['Annual Return'],
        'IS Sharpe': bm_is_metrics['Sharpe Ratio'],
        'IS Max DD': bm_is_metrics['Max Drawdown'],
        'OOS Return': bm_oos_metrics['Annual Return'],
        'OOS Sharpe': bm_oos_metrics['Sharpe Ratio'],
        'OOS Max DD': bm_oos_metrics['Max Drawdown']
    })
    
    summary_df = pd.DataFrame(summary_data)
    
    print("\nPerformance Comparison Table:")
    print("-" * 100)
    print(f"{'Strategy':<15} {'IS Return':>12} {'IS Sharpe':>12} {'IS Max DD':>12} "
          f"{'OOS Return':>12} {'OOS Sharpe':>12} {'OOS Max DD':>12}")
    print("-" * 100)
    
    for _, row in summary_df.iterrows():
        print(f"{row['Strategy']:<15} "
              f"{row['IS Return']:>11.2%} {row['IS Sharpe']:>12.2f} {row['IS Max DD']:>11.2%} "
              f"{row['OOS Return']:>11.2%} {row['OOS Sharpe']:>12.2f} {row['OOS Max DD']:>11.2%}")
    
    print("-" * 100)
    
    print("\n" + "="*80)
    print("BACKTEST COMPLETED SUCCESSFULLY")
    print("="*80)
    
    return {
        'is_results': is_results,
        'oos_results': oos_results,
        'is_metrics': is_metrics,
        'oos_metrics': oos_metrics,
        'benchmark_is': bm_is_results,
        'benchmark_oos': bm_oos_results
    }


if __name__ == "__main__":
    results = main()
Disclaimer: This article is for educational purposes only. Past performance does not guarantee future results. All strategies discussed lost money out-of-sample. Trade at your own risk and conduct your own due diligence.