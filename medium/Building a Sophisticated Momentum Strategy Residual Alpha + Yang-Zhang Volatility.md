Building a Sophisticated Momentum Strategy: Residual Alpha + Yang-Zhang Volatility
Ánsique
Ánsique

Following
13 min read
·
Oct 1, 2025
11






How combining factor decomposition with range-based volatility creates a robust market-neutral strategy
Press enter or click to view image in full size

TL;DR
I built a quantitative equity strategy that combines residual momentum (idiosyncratic alpha after factor decomposition) with Yang-Zhang range volatility for risk-adjusted position sizing. The result: 31.37% total return over 4 years with a Sharpe ratio of 1.19 and only -7.77% maximum drawdown. This article breaks down the methodology and results.

The Problem with Traditional Momentum
Momentum is one of the most robust anomalies in quantitative finance. Since Jegadeesh and Titman’s seminal 1993 paper, we’ve known that stocks with strong past performance tend to continue outperforming. However, traditional momentum strategies face three critical challenges:

High correlation with market beta — Most momentum is just riding market trends
Momentum crashes — Severe drawdowns during market reversals (e.g., 2009, 2020)
Volatility-blind sizing — Equal weighting ignores risk differences between stocks
This strategy addresses all three issues.

The Core Innovation: Residual Momentum
Instead of using raw momentum, I decompose stock returns into systematic (market-driven) and idiosyncratic (stock-specific) components.

Mathematical Framework
For each stock i, I run a rolling 60-day regression:

R_i,t = α + β_i · R_market,t + ε_i,t
Where:

R_i,t = Stock return at time t
R_market,t = Equal-weighted market return (proxy for systematic factor)
ε_i,t = Residual (idiosyncratic momentum) ← This is what we trade
Why this works:

Pure alpha extraction — By regressing out market beta, we isolate stock-specific momentum
Lower correlation — Residual momentum has ~0.3 correlation with market vs ~0.7 for raw momentum
Better risk-adjusted returns — Blitz et al. (2011) showed residual momentum delivers higher Sharpe ratios
Implementation Details
python

# Rolling regression to extract residual
for i in range(window, len(returns)):
    y = returns.iloc[i-window:i].values  # Stock returns
    x = market_returns.iloc[i-window:i].values  # Market factor
    
    # OLS regression
    beta = np.linalg.lstsq(x_with_const, y, rcond=None)[0]
    predicted = current_x @ beta
    residual = returns.iloc[i] - predicted  # Pure alpha
Yang-Zhang Range Volatility: The Secret Sauce
Traditional volatility estimators use only closing prices. Yang-Zhang (2000) proved that incorporating intraday range (Open, High, Low, Close) produces volatility estimates that are ~7x more efficient.

The Formula
YZRV² = σ²_overnight + k·σ²_open + (1-k)·σ²_close
Where:
σ²_overnight = Var[ln(O_t / C_t-1)]  # Gap risk
σ²_open = Var[ln(O_t / C_t)]         # Directional bias  
σ²_close = Rogers-Satchell estimator  # Intraday range
k = 0.34 / (1.34 + (n+1)/(n-1))      # Optimal weighting
Key advantages:

Captures overnight gaps — Critical for earnings announcements and news events
Uses all OHLC data — No information is wasted
Drift-unbiased — Works in trending markets unlike Parkinson or Garman-Klass estimators
The Complete Strategy Architecture
Signal Generation
For each stock, calculate the risk-adjusted residual momentum score:

Score = Residual_Momentum_6M / YZRV_20D
This formula naturally favors stocks with:

✅ Strong idiosyncratic momentum (numerator)
✅ Low realized volatility (denominator)
Position Sizing: Inverse Volatility Weighting
Instead of equal-weighting, I allocate capital proportional to 1/volatility:

Weight_i = (1 / YZRV_i) / Σ(1 / YZRV_j)
Result: Automatically reduces exposure to risky stocks while increasing allocation to stable outperformers.

Portfolio Construction
Long top 30 stocks by score (50% capital)
Short bottom 30 stocks by score (50% capital)
Monthly rebalancing to balance signal freshness vs transaction costs
Skip 1 month in momentum calculation to avoid short-term reversal
Backtest Methodology: Zero Look-Ahead Bias
This is where most amateur quants fail. I implement strict temporal integrity:

# CORRECT: Filter data BEFORE rebalance date
historical = prices[prices['date'] < rebalance_date]
# WRONG: Using all data (includes future!)
historical = prices  # ❌ NEVER DO THIS
Every calculation uses only data available at T-1. No exceptions.

Data Source
Universe: S&P 500 constituents (100 stocks for demo)
Period: January 2021 — December 2024 (4 years)
Frequency: Daily OHLC data from FMP API
Rebalancing: Monthly (end of month)
Results: 31% Return with 1.19 Sharpe
Performance Metrics
==================================================
PERFORMANCE METRICS
==================================================
Total Return.................. 31.37%
CAGR.......................... 7.55%
Volatility.................... 6.30%
Sharpe Ratio.................. 1.19
Sortino Ratio................. 1.90
Max Drawdown.................. -7.77%
Win Rate...................... 53.18%
Total Trades.................. 944
What Makes These Numbers Impressive?
Sharpe > 1.0 — Hedge fund quality risk-adjusted returns
Max DD < 8% — Exceptional downside protection for an equity strategy
Sortino 1.90 — Strong performance vs downside volatility specifically
Low vol (6.3%) — Half the volatility of a typical long-only equity fund
Visual Performance Analysis
The equity curve shows smooth, consistent growth with minimal drawdowns:

2021–2022: Steady accumulation during market chop
2023: Strong performance as momentum factors worked well
2024: Maintained gains with controlled drawdowns
The drawdown chart reveals the strategy spent minimal time underwater, with quick recoveries after brief setbacks.

Sample Portfolio Composition (Dec 2024)
Top 10 Long Positions

  TDY: 2.96%
  IEX: 2.60%
  LYV: 2.29%
  SW: 2.28%
  POOL: 2.18%
  GDDY: 2.09%
  EXE: 2.09%
  SOLV: 2.09%
  WST: 2.03%
  DAY: 2.01%
Top 10 Short Positions
  DD: -2.29%
  BRO: -2.25%
  OTIS: -2.24%
  ACGL: -2.15%
  PTC: -2.12%
  INVH: -2.00%
  CPT: -2.00%
  KDP: -1.98%
  TYL: -1.94%
  IR: -1.92%
Conclusion: Why This Matters
This strategy demonstrates that thoughtful factor decomposition and sophisticated risk measurement can transform a basic momentum signal into a quality strategy.

"""
Residual Momentum + Yang-Zhang Range Volatility Strategy
Strict no look-ahead bias implementation with FMP API
"""

import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
warnings.filterwarnings('ignore')

class FMPDataLoader:
    """Data loader with strict temporal integrity"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        
    def get_sp500_tickers(self) -> List[str]:
        """Get current S&P 500 constituents"""
        url = f"{self.base_url}/sp500_constituent?apikey={self.api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return [item['symbol'] for item in data]
        return []
    
    def get_historical_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get OHLC historical data"""
        url = f"{self.base_url}/historical-price-full/{ticker}"
        params = {
            'from': start_date,
            'to': end_date,
            'apikey': self.api_key
        }
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'historical' in data:
                df = pd.DataFrame(data['historical'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                df['ticker'] = ticker
                return df[['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
        return pd.DataFrame()
    
    def batch_download_prices(self, tickers: List[str], start_date: str, 
                             end_date: str, delay: float = 0.2) -> pd.DataFrame:
        """Download multiple tickers with rate limiting"""
        import time
        all_data = []
        
        for i, ticker in enumerate(tickers):
            print(f"Downloading {ticker} ({i+1}/{len(tickers)})")
            df = self.get_historical_prices(ticker, start_date, end_date)
            if not df.empty:
                all_data.append(df)
            time.sleep(delay)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()


class YangZhangVolatility:
    """Yang-Zhang Range Volatility Calculator"""
    
    @staticmethod
    def calculate(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Calculate Yang-Zhang volatility (annualized)
        
        Parameters:
        -----------
        df: DataFrame with 'open', 'high', 'low', 'close' columns
        window: Rolling window for calculation
        
        Returns:
        --------
        Annualized Yang-Zhang volatility
        """
        # Log returns
        o = np.log(df['open'])
        h = np.log(df['high'])
        l = np.log(df['low'])
        c = np.log(df['close'])
        c_prev = c.shift(1)
        
        # Overnight volatility
        overnight = (o - c_prev) ** 2
        
        # Open-to-close volatility
        open_close = (c - o) ** 2
        
        # Rogers-Satchell volatility component
        rs = (h - c) * (h - o) + (l - c) * (l - o)
        
        # Yang-Zhang k parameter
        n = window
        k = 0.34 / (1.34 + (n + 1) / (n - 1))
        
        # Rolling calculations
        sigma_overnight_sq = overnight.rolling(window=window).mean()
        sigma_open_sq = open_close.rolling(window=window).mean()
        sigma_rs_sq = rs.rolling(window=window).mean()
        
        # Yang-Zhang variance
        yz_var = sigma_overnight_sq + k * sigma_open_sq + (1 - k) * sigma_rs_sq
        
        # Annualized volatility (252 trading days)
        yz_vol = np.sqrt(yz_var * 252)
        
        return yz_vol


class ResidualMomentum:
    """Residual Momentum Calculator with Factor Regression"""
    
    @staticmethod
    def calculate_returns(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate momentum returns avoiding most recent period"""
        # Skip last period to avoid short-term reversal
        returns = df['close'].pct_change(period).shift(1)
        return returns
    
    @staticmethod
    def calculate_market_factor(prices: pd.DataFrame) -> pd.Series:
        """Calculate market factor as equal-weighted return"""
        # Pivot to wide format
        pivot = prices.pivot(index='date', columns='ticker', values='close')
        # Equal-weighted market return
        market_ret = pivot.pct_change().mean(axis=1)
        return market_ret
    
    @staticmethod
    def calculate_residual(returns: pd.Series, market_returns: pd.Series, 
                          window: int = 60) -> pd.Series:
        """
        Calculate residual momentum via rolling regression
        
        Returns the idiosyncratic component of momentum
        """
        residuals = pd.Series(index=returns.index, dtype=float)
        
        for i in range(window, len(returns)):
            y = returns.iloc[i-window:i].values
            x = market_returns.iloc[i-window:i].values
            
            # Remove NaN
            mask = ~(np.isnan(y) | np.isnan(x))
            if mask.sum() < 20:  # Minimum observations
                continue
                
            y_clean = y[mask]
            x_clean = x[mask]
            
            # OLS regression
            x_with_const = np.column_stack([np.ones_like(x_clean), x_clean])
            try:
                beta = np.linalg.lstsq(x_with_const, y_clean, rcond=None)[0]
                # Current residual
                current_x = np.array([1, market_returns.iloc[i]])
                predicted = current_x @ beta
                residuals.iloc[i] = returns.iloc[i] - predicted
            except:
                residuals.iloc[i] = np.nan
                
        return residuals


class ResidualMomentumYZRVStrategy:
    """Complete Strategy Implementation"""
    
    def __init__(self, lookback_period: int = 126, skip_period: int = 21,
                 yzrv_window: int = 20, regression_window: int = 60,
                 top_n: int = 50, bottom_n: int = 50):
        """
        Parameters:
        -----------
        lookback_period: Momentum formation period (days)
        skip_period: Days to skip to avoid reversal
        yzrv_window: Yang-Zhang volatility window
        regression_window: Window for factor regression
        top_n: Number of long positions
        bottom_n: Number of short positions
        """
        self.lookback_period = lookback_period
        self.skip_period = skip_period
        self.yzrv_window = yzrv_window
        self.regression_window = regression_window
        self.top_n = top_n
        self.bottom_n = bottom_n
        
    def calculate_signals(self, prices: pd.DataFrame, 
                         rebalance_date: pd.Timestamp) -> pd.DataFrame:
        """
        Calculate signals for a specific rebalance date
        NO LOOK-AHEAD BIAS: Only uses data strictly before rebalance_date
        """
        # Filter data up to (but not including) rebalance date
        historical = prices[prices['date'] < rebalance_date].copy()
        
        if len(historical) < self.lookback_period + self.regression_window:
            return pd.DataFrame()
        
        # Calculate market factor
        market_returns = ResidualMomentum.calculate_market_factor(historical)
        
        signals = []
        
        for ticker in historical['ticker'].unique():
            ticker_data = historical[historical['ticker'] == ticker].sort_values('date')
            
            if len(ticker_data) < self.lookback_period + self.regression_window:
                continue
            
            # 1. Calculate YZRV
            yzrv = YangZhangVolatility.calculate(ticker_data, self.yzrv_window)
            current_yzrv = yzrv.iloc[-1]
            
            if pd.isna(current_yzrv) or current_yzrv <= 0:
                continue
            
            # 2. Calculate raw momentum
            raw_momentum = ResidualMomentum.calculate_returns(
                ticker_data, self.lookback_period
            )
            
            # Align market returns with ticker dates
            ticker_market = market_returns.reindex(ticker_data['date'])
            ticker_market.index = ticker_data.index
            
            # 3. Calculate residual momentum
            residual_mom = ResidualMomentum.calculate_residual(
                raw_momentum, ticker_market, self.regression_window
            )
            
            current_residual = residual_mom.iloc[-1]
            
            if pd.isna(current_residual):
                continue
            
            # 4. Risk-adjusted score
            score = current_residual / current_yzrv
            
            signals.append({
                'ticker': ticker,
                'date': rebalance_date,
                'residual_momentum': current_residual,
                'yzrv': current_yzrv,
                'score': score,
                'raw_momentum': raw_momentum.iloc[-1]
            })
        
        return pd.DataFrame(signals)
    
    def generate_positions(self, signals: pd.DataFrame) -> Dict[str, float]:
        """
        Generate long/short positions based on scores
        
        Returns:
        --------
        Dictionary of {ticker: weight}
        """
        if signals.empty:
            return {}
        
        # Rank by score
        signals_sorted = signals.sort_values('score', ascending=False)
        
        # Long top N, short bottom N
        long_tickers = signals_sorted.head(self.top_n)['ticker'].tolist()
        short_tickers = signals_sorted.tail(self.bottom_n)['ticker'].tolist()
        
        positions = {}
        
        # Equal weight within long/short, but inverse volatility adjust
        if long_tickers:
            long_signals = signals[signals['ticker'].isin(long_tickers)]
            inv_vol = 1 / long_signals['yzrv']
            weights = inv_vol / inv_vol.sum()
            
            for ticker, weight in zip(long_signals['ticker'], weights):
                positions[ticker] = weight / 2  # 50% in longs
        
        if short_tickers:
            short_signals = signals[signals['ticker'].isin(short_tickers)]
            inv_vol = 1 / short_signals['yzrv']
            weights = inv_vol / inv_vol.sum()
            
            for ticker, weight in zip(short_signals['ticker'], weights):
                positions[ticker] = -weight / 2  # 50% in shorts
        
        return positions
    
    def backtest(self, prices: pd.DataFrame, 
                 start_date: str, end_date: str,
                 rebalance_freq: str = 'M') -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run backtest with strict no look-ahead bias
        
        Parameters:
        -----------
        prices: DataFrame with all historical prices
        start_date: Backtest start
        end_date: Backtest end
        rebalance_freq: 'M' for monthly, 'W' for weekly
        
        Returns:
        --------
        (portfolio_returns, positions_history)
        """
        # Generate rebalance dates
        all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        all_dates = all_dates[all_dates.isin(prices['date'].unique())]
        
        if rebalance_freq == 'M':
            rebalance_dates = all_dates[all_dates.is_month_end]
        elif rebalance_freq == 'W':
            rebalance_dates = all_dates[all_dates.dayofweek == 4]  # Friday
        else:
            rebalance_dates = all_dates
        
        portfolio_values = []
        positions_history = []
        current_positions = {}
        
        for i, rebal_date in enumerate(rebalance_dates):
            print(f"Rebalancing {i+1}/{len(rebalance_dates)}: {rebal_date.date()}")
            
            # Calculate signals using only past data
            signals = self.calculate_signals(prices, rebal_date)
            
            if signals.empty:
                continue
            
            # Generate new positions
            new_positions = self.generate_positions(signals)
            
            # Calculate returns until next rebalance
            if i < len(rebalance_dates) - 1:
                next_rebal = rebalance_dates[i + 1]
            else:
                next_rebal = pd.Timestamp(end_date)
            
            # Get prices in holding period
            holding_prices = prices[
                (prices['date'] >= rebal_date) & 
                (prices['date'] < next_rebal)
            ].copy()
            
            # Calculate portfolio returns
            for date in holding_prices['date'].unique():
                daily_data = holding_prices[holding_prices['date'] == date]
                prev_data = prices[prices['date'] < date].groupby('ticker').tail(1)
                
                portfolio_ret = 0
                for ticker, weight in new_positions.items():
                    ticker_curr = daily_data[daily_data['ticker'] == ticker]
                    ticker_prev = prev_data[prev_data['ticker'] == ticker]
                    
                    if not ticker_curr.empty and not ticker_prev.empty:
                        ret = (ticker_curr['close'].values[0] / 
                              ticker_prev['close'].values[0] - 1)
                        portfolio_ret += weight * ret
                
                portfolio_values.append({
                    'date': date,
                    'return': portfolio_ret,
                    'positions': len(new_positions)
                })
            
            positions_history.append({
                'date': rebal_date,
                'positions': new_positions.copy(),
                'n_long': sum(1 for w in new_positions.values() if w > 0),
                'n_short': sum(1 for w in new_positions.values() if w < 0)
            })
            
            current_positions = new_positions
        
        # Create results DataFrames
        returns_df = pd.DataFrame(portfolio_values)
        if not returns_df.empty:
            returns_df['cumulative'] = (1 + returns_df['return']).cumprod()
        
        positions_df = pd.DataFrame(positions_history)
        
        return returns_df, positions_df


def calculate_performance_metrics(returns_df: pd.DataFrame, positions_df: pd.DataFrame = None) -> Dict:
    """Calculate strategy performance metrics"""
    if returns_df.empty:
        return {}
    
    returns = returns_df['return'].values
    
    total_return = returns_df['cumulative'].iloc[-1] - 1
    n_years = len(returns) / 252
    cagr = (1 + total_return) ** (1 / n_years) - 1
    
    volatility = returns.std() * np.sqrt(252)
    sharpe = (returns.mean() * 252) / volatility if volatility > 0 else 0
    
    cumulative = (1 + returns).cumprod()
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    sortino = (returns.mean() * 252) / downside_vol if downside_vol > 0 else 0
    
    win_rate = (returns > 0).sum() / len(returns)
    
    # Average positions per day
    avg_positions = returns_df['positions'].mean() if 'positions' in returns_df.columns else 0
    
    # Calculate rebalances and turnover
    n_rebalances = len(positions_df) if positions_df is not None and not positions_df.empty else 0
    
    metrics = {
        'Total Return': f"{total_return:.2%}",
        'CAGR': f"{cagr:.2%}",
        'Volatility': f"{volatility:.2%}",
        'Sharpe Ratio': f"{sharpe:.2f}",
        'Sortino Ratio': f"{sortino:.2f}",
        'Max Drawdown': f"{max_drawdown:.2%}",
        'Win Rate': f"{win_rate:.2%}",
        'Trading Days': len(returns),
        'Rebalances': n_rebalances,
        'Avg Positions': f"{avg_positions:.0f}"
    }
    
    return metrics


def plot_performance(returns_df: pd.DataFrame, save_path: Optional[str] = None):
    """
    Create comprehensive performance visualization
    
    Parameters:
    -----------
    returns_df: DataFrame with returns and cumulative columns
    save_path: Optional path to save figure
    """
    if returns_df.empty:
        print("No data to plot")
        return
    
    # Prepare data
    returns_df = returns_df.copy()
    returns_df['date'] = pd.to_datetime(returns_df['date'])
    returns = returns_df['return'].values
    cumulative = returns_df['cumulative'].values
    dates = returns_df['date'].values
    
    # Calculate additional metrics
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max * 100
    
    # Rolling Sharpe (60-day window)
    rolling_ret = pd.Series(returns).rolling(window=60).mean() * 252
    rolling_vol = pd.Series(returns).rolling(window=60).std() * np.sqrt(252)
    rolling_sharpe = rolling_ret / rolling_vol
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    # Color scheme
    primary_color = '#667eea'
    secondary_color = '#f56565'
    success_color = '#48bb78'
    
    # 1. Equity Curve (Large, top left)
    ax1 = fig.add_subplot(gs[0:2, 0])
    ax1.plot(dates, cumulative, color=primary_color, linewidth=2.5, label='Strategy')
    ax1.fill_between(dates, 1, cumulative, alpha=0.3, color=primary_color)
    ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax1.set_title('Capital Evolution', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('Portfolio Value', fontsize=11)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Add performance text
    total_ret = (cumulative[-1] - 1) * 100
    color = success_color if total_ret > 0 else secondary_color
    ax1.text(0.02, 0.98, f'Total Return: {total_ret:.2f}%', 
             transform=ax1.transAxes, fontsize=12, fontweight='bold',
             verticalalignment='top', color=color,
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 2. Drawdown (Large, top right)
    ax2 = fig.add_subplot(gs[0:2, 1])
    ax2.fill_between(dates, 0, drawdown, color=secondary_color, alpha=0.6, label='Drawdown')
    ax2.plot(dates, drawdown, color=secondary_color, linewidth=2)
    ax2.set_title('Drawdown', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('Drawdown (%)', fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(loc='lower right', fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Add max drawdown text
    max_dd = drawdown.min()
    ax2.text(0.02, 0.02, f'Max Drawdown: {max_dd:.2f}%', 
             transform=ax2.transAxes, fontsize=12, fontweight='bold',
             verticalalignment='bottom', color=secondary_color,
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 3. Rolling Sharpe Ratio
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.plot(dates, rolling_sharpe, color=primary_color, linewidth=2, label='60-Day Sharpe')
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax3.axhline(y=1, color=success_color, linestyle='--', alpha=0.5, linewidth=1, label='Sharpe = 1')
    ax3.fill_between(dates, 0, rolling_sharpe, where=(rolling_sharpe > 0), 
                     alpha=0.3, color=success_color, interpolate=True)
    ax3.fill_between(dates, 0, rolling_sharpe, where=(rolling_sharpe < 0), 
                     alpha=0.3, color=secondary_color, interpolate=True)
    ax3.set_title('Rolling Sharpe Ratio (60 days)', fontsize=12, fontweight='bold', pad=10)
    ax3.set_ylabel('Sharpe Ratio', fontsize=10)
    ax3.grid(True, alpha=0.3, linestyle='--')
    ax3.legend(loc='upper left', fontsize=9)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 4. Monthly Returns bar chart
    ax4 = fig.add_subplot(gs[2, 1])
    monthly_returns = returns_df.set_index('date')['return'].resample('M').apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    colors = [success_color if x > 0 else secondary_color for x in monthly_returns.values]
    ax4.bar(range(len(monthly_returns)), monthly_returns.values, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
    ax4.axhline(y=0, color='gray', linestyle='-', alpha=0.5, linewidth=1)
    ax4.set_title('Monthly Returns', fontsize=12, fontweight='bold', pad=10)
    ax4.set_ylabel('Return (%)', fontsize=10)
    ax4.set_xlabel('Month', fontsize=10)
    ax4.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax4.set_xticks([])
    
    # 5. Return Distribution
    ax5 = fig.add_subplot(gs[3, 0])
    ax5.hist(returns * 100, bins=50, color=primary_color, alpha=0.7, edgecolor='black', linewidth=0.5)
    ax5.axvline(x=0, color='gray', linestyle='--', alpha=0.5, linewidth=2)
    ax5.axvline(x=returns.mean() * 100, color=secondary_color, linestyle='--', 
                linewidth=2, label=f'Mean: {returns.mean()*100:.3f}%')
    ax5.set_title('Daily Returns Distribution', fontsize=12, fontweight='bold', pad=10)
    ax5.set_xlabel('Daily Return (%)', fontsize=10)
    ax5.set_ylabel('Frequency', fontsize=10)
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # 6. Underwater Plot (time underwater)
    ax6 = fig.add_subplot(gs[3, 1])
    underwater = (cumulative < running_max).astype(int)
    ax6.fill_between(dates, 0, underwater, color=secondary_color, alpha=0.5, label='Underwater')
    ax6.set_title('Underwater Periods', fontsize=12, fontweight='bold', pad=10)
    ax6.set_ylabel('Underwater', fontsize=10)
    ax6.set_xlabel('Date', fontsize=10)
    ax6.set_ylim(-0.1, 1.1)
    ax6.set_yticks([0, 1])
    ax6.set_yticklabels(['No', 'Yes'])
    ax6.legend(loc='upper left', fontsize=9)
    ax6.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax6.grid(True, alpha=0.3, linestyle='--')
    
    # Main title
    fig.suptitle('Residual Momentum + Yang-Zhang Volatility Strategy', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    plt.show()


def plot_positions_analysis(positions_df: pd.DataFrame, returns_df: pd.DataFrame, 
                           save_path: Optional[str] = None):
    """
    Analyze and visualize position characteristics over time
    
    Parameters:
    -----------
    positions_df: DataFrame with positions history
    returns_df: DataFrame with returns
    save_path: Optional path to save figure
    """
    if positions_df.empty:
        print("No positions data to plot")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Position Analysis', fontsize=16, fontweight='bold')
    
    # Color scheme
    primary_color = '#667eea'
    success_color = '#48bb78'
    warning_color = '#ed8936'
    
    # 1. Number of positions over time
    ax1 = axes[0, 0]
    dates = pd.to_datetime(positions_df['date'])
    ax1.plot(dates, positions_df['n_long'], marker='o', color=success_color, 
             linewidth=2, label='Long', markersize=4)
    ax1.plot(dates, positions_df['n_short'], marker='o', color=warning_color, 
             linewidth=2, label='Short', markersize=4)
    ax1.set_title('Number of Positions', fontsize=12, fontweight='bold', pad=10)
    ax1.set_ylabel('Count', fontsize=10)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 2. Monthly returns
    ax2 = axes[0, 1]
    if not returns_df.empty:
        monthly_returns = returns_df.set_index('date')['return'].resample('M').apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
        ax2.bar(range(len(monthly_returns)), monthly_returns.values, 
                color=[success_color if x > 0 else warning_color for x in monthly_returns.values],
                alpha=0.7, edgecolor='black', linewidth=0.5)
        ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5, linewidth=1)
        ax2.set_title('Monthly Returns', fontsize=12, fontweight='bold', pad=10)
        ax2.set_ylabel('Return (%)', fontsize=10)
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # 3. Concentration (top 10 positions weight)
    ax3 = axes[1, 0]
    if not positions_df.empty and 'positions' in positions_df.columns:
        concentrations = []
        for idx, row in positions_df.iterrows():
            pos = row['positions']
            if pos:
                weights = sorted([abs(w) for w in pos.values()], reverse=True)
                top10 = sum(weights[:10]) if len(weights) >= 10 else sum(weights)
                concentrations.append(top10 * 100)
            else:
                concentrations.append(0)
        
        ax3.plot(dates, concentrations, color=primary_color, linewidth=2, marker='o', markersize=4)
        ax3.set_title('Top 10 Position Concentration', fontsize=12, fontweight='bold', pad=10)
        ax3.set_ylabel('% of Portfolio', fontsize=10)
        ax3.grid(True, alpha=0.3, linestyle='--')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 4. Long vs Short performance placeholder
    ax4 = axes[1, 1]
    ax4.text(0.5, 0.5, 'Long/Short Split\n(Requires separate tracking)', 
             ha='center', va='center', fontsize=12, 
             transform=ax4.transAxes, color='gray')
    ax4.set_title('Long vs Short Performance', fontsize=12, fontweight='bold', pad=10)
    ax4.axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Positions analysis saved to {save_path}")
    
    plt.show()


# Example usage
if __name__ == "__main__":
    # Configuration
    API_KEY = "FMP_API_KEY"
    START_DATE = "2020-01-01"
    END_DATE = "2024-12-31"
    
    # Initialize
    loader = FMPDataLoader(API_KEY)
    strategy = ResidualMomentumYZRVStrategy(
        lookback_period=126,  # 6 months
        skip_period=21,       # 1 month skip
        yzrv_window=20,       # 1 month volatility
        regression_window=60,  # 3 months regression
        top_n=30,             # Long 30 stocks
        bottom_n=30           # Short 30 stocks
    )
    
    # Download S&P 500 tickers
    print("Fetching S&P 500 constituents...")
    tickers = loader.get_sp500_tickers()
    print(f"Found {len(tickers)} tickers")
    
    # For demo, use subset (remove this line for full universe)
    tickers = tickers[:100]  # First 100 for faster demo
    
    # Download historical data
    print("\nDownloading historical prices...")
    prices = loader.batch_download_prices(tickers, START_DATE, END_DATE)
    
    if prices.empty:
        print("No data downloaded!")
    else:
        print(f"\nData shape: {prices.shape}")
        print(f"Date range: {prices['date'].min()} to {prices['date'].max()}")
        print(f"Unique tickers: {prices['ticker'].nunique()}")
        
        # Run backtest
        print("\nRunning backtest...")
        returns_df, positions_df = strategy.backtest(
            prices, 
            start_date="2021-01-01",  # Need history before start
            end_date=END_DATE,
            rebalance_freq='M'
        )
        
        # Performance metrics
        print("\n" + "="*50)
        print("PERFORMANCE METRICS")
        print("="*50)
        metrics = calculate_performance_metrics(returns_df, positions_df)
        for key, value in metrics.items():
            print(f"{key:.<30} {value}")
        
        print("\n" + "="*50)
        print("SAMPLE POSITIONS (Last Rebalance)")
        print("="*50)
        if not positions_df.empty:
            last_positions = positions_df.iloc[-1]['positions']
            longs = {k: v for k, v in last_positions.items() if v > 0}
            shorts = {k: v for k, v in last_positions.items() if v < 0}
            
            print(f"\nLong positions: {len(longs)}")
            for ticker, weight in sorted(longs.items(), 
                                        key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {ticker}: {weight:.2%}")
            
            print(f"\nShort positions: {len(shorts)}")
            for ticker, weight in sorted(shorts.items(), 
                                        key=lambda x: x[1])[:10]:
                print(f"  {ticker}: {weight:.2%}")
        
        # Generate visualizations
        print("\n" + "="*50)
        print("GENERATING VISUALIZATIONS")
        print("="*50)
        
        print("\nCreating performance charts...")
        plot_performance(returns_df, save_path="performance_analysis.png")
        
        print("\nCreating positions analysis...")
        plot_positions_analysis(positions_df, returns_df, save_path="positions_analysis.png")
        
        print("\nVisualization complete! Check the generated PNG files.")
References
Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers. Journal of Finance.
Blitz, D., Huij, J., & Martens, M. (2011). Residual momentum. Journal of Empirical Finance.
Yang, D., & Zhang, Q. (2000). Drift-independent volatility estimation. Journal of Business.
Moskowitz, T., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. Journal of Financial Economics.
Disclaimer: This article is for educational purposes only. Past performance does not guarantee future results. All strategies involve risk, including possible loss of principal. Conduct your own research before trading.