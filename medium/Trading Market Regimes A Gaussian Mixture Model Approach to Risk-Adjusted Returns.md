Trading Market Regimes: A Gaussian Mixture Model Approach to Risk-Adjusted Returns
Ánsique
Ánsique

Following
27 min read
·
Oct 10, 2025
202


2





How machine learning regime detection achieved a 1.00 Sharpe ratio with half the drawdown of buy-and-hold
Press enter or click to view image in full size

In the world of quantitative trading, one of the most persistent challenges is understanding when market dynamics shift. Are we in a bull market? A correction? A period of high volatility that requires caution? Rather than trying to predict these shifts after the fact, what if we could systematically detect regime changes in real-time and adjust our positions accordingly?

This is the premise behind regime-switching strategies, and today I’m sharing the results of a production-level implementation using Gaussian Mixture Models (GMM) that achieved compelling risk-adjusted returns over a 5-year period.

The Core Insight: Markets Have Distinct “Regimes”
Markets don’t behave uniformly over time. Some periods are characterized by steady upward momentum with low volatility. Others exhibit choppy, range-bound behaviour. And occasionally, we experience sharp selloffs with elevated volatility.

The key insight is this: if we can systematically identify which regime we’re in, we can adjust our exposure accordingly — going long during favourable conditions and moving to cash during unfavourable ones.

The Strategy Architecture
Feature Engineering: What Defines a Regime?
Rather than using arbitrary technical indicators, I focused on two fundamental characteristics that capture market state:

1. Yang-Zhang Volatility (20-day window)

Unlike simple historical volatility that only uses closing prices, the Yang-Zhang estimator is a sophisticated range-based measure that incorporates:

Overnight gaps (Open vs previous Close)
Intraday movement (High-Low ranges)
Open-to-Close dynamics
The formula combines three components:

σ²_YZ = σ²_overnight + k·σ²_open_close + (1-k)·σ²_Rogers_Satchell
This gives us a more comprehensive view of realized volatility, capturing information that close-to-close calculations miss. Why it matters: Bullish regimes typically show higher volatility (counterintuitively), while choppy markets show moderate volatility.

2. SMA 20 vs 50 Crossover (Normalized)

Instead of a binary crossover signal, I use a continuous normalized difference:

Signal = (SMA_20 - SMA_50) / SMA_50
This captures both the direction and magnitude of trend strength. Positive values indicate bullish momentum, negative values indicate bearish momentum, and the magnitude tells us how strong that momentum is. Normalization makes it scale-invariant — it works the same whether SPY is at $300 or $600.

Critical: Both features are lagged by 1 day to prevent look-ahead bias. When we generate a signal at Close[t], we use features from t-1.

The Algorithm: Gaussian Mixture Models
Why GMM Instead of HMM?
While Hidden Markov Models (HMMs) are popular for regime detection, I chose Gaussian Mixture Models for several reasons:

Simplicity: GMM assumes features come from a mixture of Gaussian distributions without modelling temporal transitions
Interpretability: Each cluster centre represents a distinct market state
Robustness: No need to model transition probabilities, which can be unstable
Speed: Faster training and convergence
GMM works by assuming our 2D feature space (volatility × momentum) contains K=3 clusters representing Bearish, Neutral, and Bullish regimes. The algorithm finds:

Cluster centres: The “typical” feature values for each regime
Covariances: How features vary within each regime
Mixing weights: How common each regime is
Walk-Forward Validation: Preventing Overfitting
Here’s where most backtests fail: they use future data to make past decisions.

This strategy uses strict walk-forward validation:

Expanding window training: Start with 252 days (1 year) of data
Fit models: Train StandardScaler → GMM on historical data only
Create regime mapping: Analyse which clusters had positive forward returns in the training period
Freeze models: Lock scaler, GMM, and regime labels
Predict forward: Use frozen models for next 63 days (1 quarter)
Refit: Expand window and repeat
This resulted in 20 refits over the backtest period, with all clusters remaining sufficiently populated (≥10 samples).

Regime Assignment Logic:

Calculate forward returns for each cluster in training data
Sort clusters by mean forward return
Assign: Lowest → Bearish, Middle → Neutral, Highest → Bullish
This ensures regime labels reflect actual future returns, not arbitrary technical criteria.

Trading Logic: When to Be Long
The strategy employs a long-only approach:

Long: When in Bullish regime (407 days, 27.9%)
Cash: When in Neutral (555 days, 38.0%) or Bearish (246 days, 16.8%)
Execution mechanics:

Signal generated at Close[t] based on current regime
Execution at Open[t+1] (realistic slippage)
Portfolio marked-to-market at Close[t+1]
All returns calculated Close-to-Close for consistency
Commission: 0.1% per trade (10 bps)
With only 38 trades over 5+ years (19 buys, 19 sells), the strategy shows remarkably low turnover, minimizing transaction costs and taxes.

Results: Superior Risk-Adjusted Performance
Performance Metrics (March 2019 — December 2024)
----------------------------------------------------------------------------------------------------
PERFORMANCE ANALYSIS
----------------------------------------------------------------------------------------------------

====================================================================================================
PERFORMANCE METRICS (WALK-FORWARD VALIDATED - NO LOOK-AHEAD BIAS)
====================================================================================================

Strategy:
  Total Return:        107.01%
  CAGR:                 13.39%
  Volatility:           11.25%
  Sharpe Ratio:           1.00
  Max Drawdown:        -14.68%
  Win Rate:             16.45%
  Final Value:      $207,011.99

SPY:
  Total Return:        108.70%
  CAGR:                 13.55%
  Volatility:           20.08%
  Sharpe Ratio:           0.63
  Max Drawdown:        -34.10%
  Final Value:      $208,493.98

URTH:
  Total Return:         75.57%
  CAGR:                 10.21%
  Volatility:           19.46%
  Sharpe Ratio:           0.49
  Max Drawdown:        -34.01%
  Final Value:      $175,394.79

Relative to URTH (Global Benchmark):
  Excess Return:        31.44%
  Excess CAGR:           3.18%
  Sharpe Advantage:       0.50

Relative to SPY:
  Excess Return:        -1.69%
  Excess CAGR:          -0.16%
  Sharpe Advantage:       0.36
====================================================================================================
Key Takeaways
1. Comparable Returns, Half the Risk

The strategy delivered 107% returns, nearly matching SPY’s 109%. But here’s the critical difference: it achieved this with 11.25% volatility vs SPY’s 20.08%. That’s a 44% reduction in volatility.

2. Exceptional Risk-Adjusted Performance

The Sharpe ratio of 1.00 vs SPY’s 0.63 represents a 59% improvement. For every unit of risk taken, the strategy generated substantially more return.

3. Dramatically Reduced Drawdowns

Maximum drawdown of -14.68% vs -34.10% for SPY. During the 2020 COVID crash and 2022 bear market, the strategy’s regime detection moved to cash, avoiding the worst declines.

4. Outperformance vs Global Equities

Against URTH (global benchmark), the strategy showed clear alpha:

Excess return: +31.44%
Excess CAGR: +3.18%
Sharpe advantage: +0.50
Limitations and Considerations
1. Sample Period Matters
The backtest period (2019–2024) included:

The 2020 COVID crash (regime detection worked well)
The 2022 bear market (moved to cash appropriately)
Multiple regime transitions
Limited to one business cycle
Caveat: Performance in prolonged sideways markets (e.g., 2000s) remains untested.

2. Regime Detection Lag
The strategy detects regime changes but doesn’t predict them. There’s an inherent lag:

We observe feature changes
GMM classifies current state
We act on classification
This means we might miss the first few days of a new regime or hold slightly too long.

3. Opportunity Cost in Bull Markets
Being in cash 55% of the time means missing gains during:

Neutral regime rallies
Early stage recoveries before Bullish classification
In strong bull markets (e.g., 2023–2024), buy-and-hold would outperform. This is a feature, not a bug — we accept lower returns in exchange for dramatically reduced risk.

4. Three-Regime Framework
The K=3 cluster assumption is somewhat arbitrary. Markets might have:

More than 3 distinct regimes
Overlapping regime characteristics
Regime subtypes (e.g., “low-vol bullish” vs “high-vol bullish”)
However, increasing K introduces complexity and risks overfitting.

5. Parameter Sensitivity
Key parameters that could affect performance:

SMA windows (20 vs 50)
Yang-Zhang window (20 days)
Refit frequency (63 days)
Minimum cluster samples (10)
While these were chosen based on theory and common practice, they weren’t exhaustively optimized (by design, to avoid overfitting).

Extensions and Future Work
Several promising directions to explore:

1. Multi-Asset Regime Detection
Apply the same framework to:

International equities (EEM, EFA)
Fixed income (TLT, IEF)
Commodities (GLD, DBC)
Crypto (BTC, ETH)
Different assets might exhibit different regime structures.

2. Dynamic Position Sizing
Instead of binary long/cash:

100% long in Bullish
50% long in Neutral
0% long in Bearish
This could capture some upside in neutral regimes while maintaining risk control.

3. Regime-Based Portfolio Allocation
Use regime detection for:

Stocks vs bonds allocation
Risk-on vs risk-off positioning
Factor rotation (value vs growth)
4. Incorporate Additional Features
Potential regime indicators:

Credit spreads (HYG vs LQD)
Term structure (2Y-10Y spread)
Put/call ratios
Market breadth (AD line)
Sentiment indicators
5. Long/Short Implementation
Enable short positions in Bearish regimes:

Long in Bullish
Cash in Neutral
Short in Bearish
This could enhance returns but adds complexity and risk.

Conclusion: The Case for Regime-Aware Investing
The results speak for themselves: matching market returns with half the volatility and less than half the drawdown.

But beyond the numbers, this strategy represents a fundamentally different approach to investing. Rather than being fully invested at all times (traditional buy-and-hold) or trying to time the market based on predictions (tactical trading), regime detection offers a middle path:

Respond to observable market conditions, don’t predict the future.

When volatility and momentum characteristics suggest favourable conditions, be long. When they don’t, step aside. It’s that simple.

The financial industry has long recognized that returns are non-stationary — volatility clusters, trends persist, correlations break down. Yet most retail investors are told to “stay invested” regardless of conditions. Regime-switching strategies acknowledge that not all market environments are created equal.

For investors willing to accept lower returns in raging bull markets in exchange for sleeping soundly during crashes, regime detection strategies deserve serious consideration.

Implementation
The complete strategy code is available with:

Full walk-forward validation
Benchmark comparisons
Visualization tools
Export functionality
Key files generated:

gmm_walkforward_results_*.csv - Full backtest results
gmm_walkforward_trades_*.csv - All executed trades
gmm_walkforward_folds_*.csv - Refit metadata for validation
All code is production-ready with:

Comprehensive error handling
Data validation
Non-negativity guards
Robust cluster handling
Proper short mechanics (if enabled)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import requests
import warnings
from typing import Dict, Tuple, Optional, List
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

class StrategyConfig:
    """
    Centralized configuration for all strategy parameters.
    
    All parameters are configurable to allow easy experimentation and optimization.
    No hardcoded values in the main logic - everything flows from this config.
    """
    
    # API Configuration
    FMP_API_KEY = "FMP_API_KEY"
    
    # Date Range - 5 years of data for realistic backtest
    START_DATE = "2019-01-01"
    END_DATE = "2024-12-31"
    
    # Trading Parameters
    INITIAL_CAPITAL = 100000.0  # Starting capital in USD
    COMMISSION_RATE = 0.001      # 0.1% per trade (realistic for retail/institutional)
    
    # Tickers
    MAIN_TICKER = "SPY"                    # Primary trading instrument
    BENCHMARK_TICKER = "URTH"              # Global equity benchmark
    
    # Feature Engineering Parameters
    SMA_SHORT = 20      # Short-term moving average window
    SMA_LONG = 50       # Long-term moving average window
    YZ_WINDOW = 20      # Yang-Zhang volatility estimation window
    
    # GMM Parameters
    GMM_N_COMPONENTS = 3           # Number of regimes (Bearish, Neutral, Bullish)
    GMM_COVARIANCE_TYPE = "full"   # Covariance type: 'full', 'tied', 'diag', 'spherical'
    GMM_MAX_ITER = 100             # Maximum iterations for EM algorithm
    GMM_N_INIT = 10                # Number of initializations (best is kept)
    GMM_RANDOM_STATE = 42          # For reproducibility
    
    # Walk-Forward Parameters
    MIN_TRAINING_DAYS = 252        # 1 year minimum before first prediction
    REFIT_FREQUENCY = 63           # Refit every quarter (63 trading days ~= 3 months)
    MIN_CLUSTER_SAMPLES = 10       # Minimum samples per cluster for valid regime mapping
    
    # Regime Trading Logic
    LONG_REGIME = "Bullish"        # Which regime to be long in
    SHORT_REGIME = None            # Which regime to be short in (None = cash instead)
    # Examples: 
    # - Long only: LONG_REGIME="Bullish", SHORT_REGIME=None
    # - Long/Short: LONG_REGIME="Bullish", SHORT_REGIME="Bearish"
    # - Long/Flat: LONG_REGIME="Bullish", SHORT_REGIME=None


# ============================================================================
# DATA ACQUISITION
# ============================================================================

class DataFetcher:
    """
    Handles all data acquisition from FMP API.
    
    Key principles:
    - No data imputation (no bfill/ffill)
    - Direct API calls only
    - Proper error handling
    - Data validation
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
    
    def fetch_historical_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from FMP API.
        
        Parameters:
        -----------
        ticker : str
            Stock ticker symbol
        start_date : str
            Start date in YYYY-MM-DD format
        end_date : str
            End date in YYYY-MM-DD format
        
        Returns:
        --------
        pd.DataFrame with columns: Date, Open, High, Low, Close, Volume
        
        Critical: NO data filling - missing data stays missing and will be handled
        downstream through proper NaN handling in feature engineering.
        """
        url = f"{self.base_url}/historical-price-full/{ticker}"
        params = {"from": start_date, "to": end_date, "apikey": self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "historical" not in data:
                raise ValueError(f"No data returned for {ticker}")
            
            df = pd.DataFrame(data["historical"])
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            
            # Standardize column names
            df = df.rename(columns={
                "date": "Date", "open": "Open", "high": "High",
                "low": "Low", "close": "Close", "volume": "Volume"
            })
            
            # Keep only necessary columns
            df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
            
            print(f"✓ Fetched {len(df)} records for {ticker} ({df['Date'].min().date()} to {df['Date'].max().date()})")
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Network error fetching data for {ticker}: {str(e)}")
            raise
        except Exception as e:
            print(f"✗ Error processing data for {ticker}: {str(e)}")
            raise


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

class FeatureEngine:
    """
    Calculates technical features with strict look-ahead bias prevention.
    
    All features are lagged by 1 day to ensure T-1 data is used for T predictions.
    This is CRITICAL for walk-forward validation integrity.
    """
    
    @staticmethod
    def calculate_yang_zhang_volatility(df: pd.DataFrame, window: int) -> pd.Series:
        """
        Calculate Yang-Zhang volatility estimator with non-negativity guard.
        
        The Yang-Zhang estimator is a range-based volatility measure that combines:
        - Overnight volatility: (Open[t] / Close[t-1])
        - Open-to-Close volatility: (Close[t] / Open[t])
        - High-Low range: Rogers-Satchell component
        
        Formula:
        σ²_YZ = σ²_overnight + k·σ²_open_close + (1-k)·σ²_RS
        
        where:
        - σ²_overnight = Var(ln(O[t]/C[t-1]))
        - σ²_open_close = Var(ln(C[t]/O[t]))
        - σ²_RS = Rogers-Satchell = E[ln(H/C)·ln(H/O) + ln(L/C)·ln(L/O)]
        - k = weighting factor ≈ 0.34 (standard value)
        
        IMPROVEMENT: Added np.clip to ensure variance is non-negative before sqrt
        to handle edge cases where floating point errors could produce tiny negative values.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Must contain Open, High, Low, Close columns
        window : int
            Rolling window size for volatility estimation
        
        Returns:
        --------
        pd.Series : Annualized Yang-Zhang volatility (always non-negative)
        """
        # Overnight component: ln(Open[t] / Close[t-1])
        overnight = np.log(df["Open"] / df["Close"].shift(1))
        overnight_var = overnight.rolling(window=window, min_periods=window).var()
        
        # Open-to-Close component: ln(Close[t] / Open[t])
        open_close = np.log(df["Close"] / df["Open"])
        open_close_var = open_close.rolling(window=window, min_periods=window).var()
        
        # Rogers-Satchell component
        # RS = E[ln(H/C)·ln(H/O) + ln(L/C)·ln(L/O)]
        high_close = np.log(df["High"] / df["Close"])
        high_open = np.log(df["High"] / df["Open"])
        low_close = np.log(df["Low"] / df["Close"])
        low_open = np.log(df["Low"] / df["Open"])
        
        rs_component = high_close * high_open + low_close * low_open
        rs_var = rs_component.rolling(window=window, min_periods=window).mean()
        
        # Combine components with k = 0.34 (standard weighting)
        k = 0.34
        yang_zhang_var = overnight_var + k * open_close_var + (1 - k) * rs_var
        
        # CRITICAL: Clip variance to ensure non-negativity before sqrt
        # This prevents NaN from sporadic floating point errors that could produce
        # tiny negative variances (e.g., -1e-16)
        yang_zhang_var_clipped = np.clip(yang_zhang_var, 0, np.inf)
        
        # Convert to annualized standard deviation
        yang_zhang_vol = np.sqrt(yang_zhang_var_clipped * 252)
        
        return yang_zhang_vol
    
    @staticmethod
    def calculate_sma_crossover_normalized(close: pd.Series, short_window: int, 
                                          long_window: int) -> pd.Series:
        """
        Calculate normalized SMA crossover signal.
        
        Instead of binary crossover (1/-1), we use continuous normalized difference:
        Signal = (SMA_short - SMA_long) / SMA_long
        
        This captures:
        - Positive values: Short MA above long MA (bullish momentum)
        - Negative values: Short MA below long MA (bearish momentum)
        - Magnitude: Strength of trend
        
        Normalization by SMA_long makes the signal scale-invariant (works across
        different price levels and assets).
        
        Parameters:
        -----------
        close : pd.Series
            Close prices
        short_window : int
            Short moving average window
        long_window : int
            Long moving average window
        
        Returns:
        --------
        pd.Series : Normalized crossover signal (continuous, typically in [-0.1, 0.1])
        """
        # Calculate moving averages with minimum periods = window
        # This ensures we don't have incomplete averages at the start
        sma_short = close.rolling(window=short_window, min_periods=short_window).mean()
        sma_long = close.rolling(window=long_window, min_periods=long_window).mean()
        
        # Normalized difference: percentage above/below long MA
        # Dividing by sma_long makes it scale-invariant
        crossover_signal = (sma_short - sma_long) / sma_long
        
        return crossover_signal
    
    @staticmethod
    def prepare_features(df_main: pd.DataFrame, config: StrategyConfig) -> pd.DataFrame:
        """
        Prepare all features with proper lagging to prevent look-ahead bias.
        
        CRITICAL LOOK-AHEAD PREVENTION:
        1. Calculate features using only past data (rolling windows)
        2. Lag ALL features by 1 day: feature[t-1] predicts returns[t]
        3. This ensures when we generate signal at Close[t], we're using data available at t
        
        Feature Flow:
        - Raw data at t-1 → Feature calculation → Feature[t-1] → Signal[t-1] → Execute[t]
        
        Parameters:
        -----------
        df_main : pd.DataFrame
            Main price data (SPY)
        config : StrategyConfig
            Configuration object with all parameters
        
        Returns:
        --------
        pd.DataFrame with lagged features and returns
        """
        df = df_main.copy()
        
        print("\nCalculating features...")
        
        # ===== RETURN CALCULATIONS =====
        # CONSISTENT Close-to-Close returns for all daily calculations
        # This ensures strategy and benchmarks are on the same basis
        df["Returns_CC"] = df["Close"].pct_change()
        
        # Open-to-Open returns: only used for regime mapping (forward returns)
        df["Returns_OO"] = df["Open"].pct_change()
        
        # ===== FEATURE 1: Yang-Zhang Volatility =====
        # More sophisticated than simple volatility, uses full OHLC information
        df["YangZhang_Vol"] = FeatureEngine.calculate_yang_zhang_volatility(
            df, config.YZ_WINDOW
        )
        print(f"✓ Yang-Zhang volatility calculated (window={config.YZ_WINDOW})")
        
        # ===== FEATURE 2: SMA Crossover (Normalized) =====
        # Continuous momentum signal, not binary
        df["SMA_Cross_Norm"] = FeatureEngine.calculate_sma_crossover_normalized(
            df["Close"], config.SMA_SHORT, config.SMA_LONG
        )
        print(f"✓ SMA crossover calculated (SMA{config.SMA_SHORT} vs SMA{config.SMA_LONG})")
        
        # ===== CRITICAL: LAG ALL FEATURES BY 1 DAY =====
        # This is THE key step to prevent look-ahead bias
        # When we predict regime at Close[t], we use features from t-1
        feature_cols = ["YangZhang_Vol", "SMA_Cross_Norm"]
        for col in feature_cols:
            df[f"{col}_lag"] = df[col].shift(1)
        
        print("✓ Features lagged by 1 day to prevent look-ahead bias")
        
        # Show feature statistics
        lagged_features = [f"{col}_lag" for col in feature_cols]
        valid_data = df[lagged_features].dropna()
        
        if len(valid_data) > 0:
            print(f"\nFeature statistics (after lagging):")
            print(f"  Valid observations: {len(valid_data)}")
            for col in lagged_features:
                print(f"  {col}: mean={valid_data[col].mean():.4f}, std={valid_data[col].std():.4f}")
        
        return df


# ============================================================================
# WALK-FORWARD GMM REGIME DETECTOR
# ============================================================================

@dataclass
class RegimeMapping:
    """
    Stores regime mapping from training period.
    
    This mapping is FROZEN for the prediction period to prevent look-ahead bias.
    The mapping tells us which GMM cluster corresponds to which economic regime
    (Bearish/Neutral/Bullish) based on PAST forward returns.
    """
    cluster_to_regime: Dict[int, str]      # Maps cluster ID → regime name
    mean_returns: Dict[int, float]         # Mean forward returns per cluster
    cluster_counts: Dict[int, int]         # Number of samples per cluster
    training_end_date: pd.Timestamp        # Last date of training data used
    is_valid: bool                         # Whether mapping has sufficient samples


class WalkForwardGMMRegimeDetector:
    """
    GMM Regime Detector with STRICT walk-forward validation.
    
    GMM (Gaussian Mixture Model) vs HMM:
    - GMM: Assumes features come from mixture of Gaussian distributions
    - No temporal dependencies (unlike HMM)
    - Simpler, faster, often more robust
    - Good for regime detection when temporal transition probabilities not important
    
    WALK-FORWARD PROCESS (NO LOOK-AHEAD):
    =====================================
    For each prediction window:
    
    1. TRAIN SCALER: Fit StandardScaler on expanding training window
       → Learn mean/std of features from past data only
    
    2. TRAIN GMM: Fit GaussianMixture on normalized training features
       → Learn cluster centers and covariances from past data
    
    3. CREATE REGIME MAPPING: Analyze forward returns in training period
       → Determine which cluster = Bearish, Neutral, Bullish
       → CRITICAL: Use only training period forward returns
       → ROBUST: Handle underpopulated clusters (min sample threshold)
    
    4. FREEZE MODELS: Lock scaler, GMM, and regime mapping
    
    5. PREDICT: Use frozen models to predict regime for next period
    
    6. REFIT: After N days, repeat process with expanded training set
    
    This ensures predictions at time T use ONLY information available at T-1.
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        # Feature columns to use (already lagged in feature engineering step)
        self.feature_cols = ["YangZhang_Vol_lag", "SMA_Cross_Norm_lag"]
        self.previous_mapping = None  # Store last valid mapping for fallback
        
    def create_regime_mapping(self, X_train: np.ndarray, gmm_model: GaussianMixture,
                             returns_forward: np.ndarray, train_end_date: pd.Timestamp) -> RegimeMapping:
        """
        Create regime mapping with robust cluster handling.
        
        IMPROVEMENTS:
        1. Clean slicing: Remove last observation before analysis (no forward return)
        2. Minimum sample enforcement: Require MIN_CLUSTER_SAMPLES per cluster
        3. NaN for empty clusters: Don't use 0.0 fallback
        4. Fallback mechanism: Use previous valid mapping if current is invalid
        
        Parameters:
        -----------
        X_train : np.ndarray
            Training features
        gmm_model : GaussianMixture
            Fitted GMM model
        returns_forward : np.ndarray
            Forward returns (already shifted)
        train_end_date : pd.Timestamp
            End date of training period
        
        Returns:
        --------
        RegimeMapping object with cluster→regime mapping
        """
        # Predict clusters for training period
        clusters_all = gmm_model.predict(X_train)
        
        # CLEAN SLICING: Remove last observation (no forward return available)
        # This is cleaner than manual mask[-1] = False
        clusters_train = clusters_all[:-1]
        returns_train = returns_forward[:-1]
        
        # Analyze each cluster
        cluster_returns = {}
        cluster_counts = {}
        
        for cluster_id in range(self.config.GMM_N_COMPONENTS):
            mask = clusters_train == cluster_id
            count = mask.sum()
            cluster_counts[cluster_id] = count
            
            if count >= self.config.MIN_CLUSTER_SAMPLES:
                # Sufficient samples: calculate mean return
                cluster_returns[cluster_id] = returns_train[mask].mean()
            else:
                # Insufficient samples: use NaN (not 0.0)
                # This signals that the cluster is unreliable
                cluster_returns[cluster_id] = np.nan
        
        # Check if mapping is valid (all clusters have sufficient samples)
        valid_clusters = [cid for cid, ret in cluster_returns.items() if not np.isnan(ret)]
        is_valid = len(valid_clusters) == self.config.GMM_N_COMPONENTS
        
        if is_valid:
            # Sort by returns to assign regime labels
            sorted_clusters = sorted(cluster_returns.items(), key=lambda x: x[1])
            cluster_to_regime = {
                sorted_clusters[0][0]: "Bearish",
                sorted_clusters[1][0]: "Neutral",
                sorted_clusters[2][0]: "Bullish"
            }
            
            print(f"✓ Valid regime mapping created:")
            for cluster_id, regime in cluster_to_regime.items():
                print(f"  Cluster {cluster_id} → {regime}: "
                      f"{cluster_counts[cluster_id]} obs, "
                      f"avg forward return: {cluster_returns[cluster_id]:.6f}")
        else:
            # Invalid mapping: try to use previous valid mapping
            if self.previous_mapping is not None and self.previous_mapping.is_valid:
                print(f"⚠ Some clusters underpopulated, using previous fold's mapping")
                cluster_to_regime = self.previous_mapping.cluster_to_regime
                print(f"  Carried forward mapping from {self.previous_mapping.training_end_date.date()}")
            else:
                # No previous mapping available: assign default ordering
                print(f"⚠ Some clusters underpopulated and no previous mapping available")
                print(f"  Using default cluster→regime assignment (0→Bearish, 1→Neutral, 2→Bullish)")
                cluster_to_regime = {
                    0: "Bearish",
                    1: "Neutral",
                    2: "Bullish"
                }
            
            # Show which clusters are problematic
            for cluster_id, count in cluster_counts.items():
                status = "OK" if count >= self.config.MIN_CLUSTER_SAMPLES else "UNDERPOPULATED"
                ret_str = f"{cluster_returns[cluster_id]:.6f}" if not np.isnan(cluster_returns[cluster_id]) else "NaN"
                print(f"  Cluster {cluster_id}: {count} obs, return: {ret_str} [{status}]")
        
        mapping = RegimeMapping(
            cluster_to_regime=cluster_to_regime,
            mean_returns=cluster_returns,
            cluster_counts=cluster_counts,
            training_end_date=train_end_date,
            is_valid=is_valid
        )
        
        # Update previous mapping if current is valid
        if is_valid:
            self.previous_mapping = mapping
        
        return mapping
        
    def walk_forward_predict(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Perform walk-forward regime prediction with NO look-ahead bias.
        
        Returns:
        --------
        Tuple of:
        - df_clean: DataFrame with regime predictions
        - folds_executed: List of dictionaries with fold metadata for validation
        """
        print("\n" + "="*80)
        print("WALK-FORWARD GMM REGIME DETECTION (NO LOOK-AHEAD BIAS)")
        print("="*80)
        
        # ===== DATA CLEANING =====
        # Drop rows where features are NaN (e.g., initial period before windows fill)
        df_clean = df.dropna(subset=self.feature_cols).copy().reset_index(drop=True)
        print(f"\nTotal observations after cleaning: {len(df_clean)}")
        print(f"Date range: {df_clean['Date'].min().date()} to {df_clean['Date'].max().date()}")
        
        # Initialize result columns
        df_clean["Regime_Cluster"] = np.nan  # GMM cluster ID (0, 1, 2)
        df_clean["Regime"] = None             # Economic label (Bearish, Neutral, Bullish)
        
        # ===== WALK-FORWARD SETUP =====
        min_train = self.config.MIN_TRAINING_DAYS
        refit_freq = self.config.REFIT_FREQUENCY
        
        print(f"\nWalk-forward configuration:")
        print(f"  Minimum training: {min_train} days")
        print(f"  Refit frequency: {refit_freq} days")
        print(f"  Min cluster samples: {self.config.MIN_CLUSTER_SAMPLES}")
        print(f"  Total predictions needed: {len(df_clean) - min_train}")
        
        # Track all folds for validation
        folds_executed = []
        
        # Initialize model objects
        last_refit_idx = min_train
        scaler = None
        gmm_model = None
        regime_mapping = None
        
        fold_num = 0
        
        # ===== MAIN WALK-FORWARD LOOP =====
        for i in range(min_train, len(df_clean)):
            days_since_refit = i - last_refit_idx
            
            # ===== CHECK IF REFIT NEEDED =====
            if (scaler is None) or (days_since_refit >= refit_freq):
                fold_num += 1
                train_start = 0           # Expanding window: always start from beginning
                train_end = i             # End at current position
                
                print(f"\n{'='*80}")
                print(f"FOLD {fold_num}: Refitting models")
                print(f"{'='*80}")
                print(f"Training window: index {train_start} to {train_end-1}")
                print(f"Training dates: {df_clean.loc[train_start, 'Date'].date()} to "
                      f"{df_clean.loc[train_end-1, 'Date'].date()}")
                print(f"Training size: {train_end - train_start} days")
                
                # ===== STEP 1: FIT SCALER =====
                # Extract raw features from training window
                X_train_raw = df_clean.loc[train_start:train_end-1, self.feature_cols].values
                
                # Fit StandardScaler: learns mean and std from training data
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train_raw)
                
                print(f"✓ Scaler fitted on {len(X_train_scaled)} training observations")
                
                # ===== STEP 2: FIT GMM =====
                # GaussianMixture finds K clusters in feature space
                gmm_model = GaussianMixture(
                    n_components=self.config.GMM_N_COMPONENTS,
                    covariance_type=self.config.GMM_COVARIANCE_TYPE,
                    max_iter=self.config.GMM_MAX_ITER,
                    n_init=self.config.GMM_N_INIT,
                    random_state=self.config.GMM_RANDOM_STATE
                )
                gmm_model.fit(X_train_scaled)
                
                print(f"✓ GMM fitted (converged: {gmm_model.converged_})")
                
                # ===== STEP 3: CREATE REGIME MAPPING =====
                # Get forward returns for training period
                returns_forward_train = df_clean.loc[train_start:train_end-1, "Returns_OO"].shift(-1).values
                
                # Create mapping with robust cluster handling
                regime_mapping = self.create_regime_mapping(
                    X_train_scaled, 
                    gmm_model, 
                    returns_forward_train,
                    df_clean.loc[train_end-1, "Date"]
                )
                
                # Update refit tracker
                last_refit_idx = i
                
                # ===== STORE FOLD METADATA =====
                folds_executed.append({
                    'fold': fold_num,
                    'train_start': train_start,
                    'train_end': train_end,
                    'train_start_date': df_clean.loc[train_start, 'Date'],
                    'train_end_date': df_clean.loc[train_end-1, 'Date'],
                    'regime_mapping': regime_mapping.cluster_to_regime.copy(),
                    'mean_returns': regime_mapping.mean_returns.copy(),
                    'cluster_counts': regime_mapping.cluster_counts.copy(),
                    'is_valid': regime_mapping.is_valid
                })
            
            # ===== STEP 4: PREDICT CURRENT OBSERVATION =====
            # Use FROZEN models (scaler, GMM, mapping) to predict regime
            
            # Extract current observation features
            X_current_raw = df_clean.loc[i:i, self.feature_cols].values
            
            # Transform using frozen scaler
            X_current_scaled = scaler.transform(X_current_raw)
            
            # Predict cluster using frozen GMM
            cluster_pred = gmm_model.predict(X_current_scaled)[0]
            
            # Map to regime using frozen mapping
            regime_pred = regime_mapping.cluster_to_regime[cluster_pred]
            
            # Store predictions
            df_clean.loc[i, "Regime_Cluster"] = cluster_pred
            df_clean.loc[i, "Regime"] = regime_pred
        
        # ===== VALIDATION SUMMARY =====
        print(f"\n{'='*80}")
        print(f"WALK-FORWARD COMPLETE")
        print(f"{'='*80}")
        print(f"Total folds executed: {len(folds_executed)}")
        valid_folds = sum(1 for f in folds_executed if f['is_valid'])
        print(f"Valid folds (all clusters sufficiently populated): {valid_folds}/{len(folds_executed)}")
        print(f"Predictions generated: {df_clean['Regime'].notna().sum()}")
        
        # Show final regime distribution
        regime_counts = df_clean["Regime"].value_counts()
        print(f"\nFinal regime distribution:")
        for regime in ["Bearish", "Neutral", "Bullish"]:
            count = regime_counts.get(regime, 0)
            pct = count / len(df_clean) * 100 if len(df_clean) > 0 else 0
            print(f"  {regime}: {count} days ({pct:.1f}%)")
        
        return df_clean, folds_executed


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class BacktestEngine:
    """
    Production-level backtesting engine with proper long/short handling.
    
    EXECUTION LOGIC:
    ===============
    1. Signal generated at Close[t] based on regime
    2. Execution happens at Open[t+1]
    3. Portfolio marked-to-market at Close[t+1]
    4. Returns = Close[t+1] / Close[t] - 1 (CONSISTENT for strategy and benchmarks)
    
    POSITION STATES:
    - Position = 1: Long (positive shares)
    - Position = 0: Flat (cash)
    - Position = -1: Short (negative shares, borrowed stock)
    
    SHORT MECHANICS:
    - Borrow shares and sell them (receive cash + commission)
    - Mark-to-market: Holdings = -shares * Close (negative value)
    - Cover: Buy back shares (pay cash + commission)
    - PnL: Profit when price falls, loss when price rises
    """
    
    def __init__(self, initial_capital: float, commission_rate: float):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.trades = []  # Store all executed trades for analysis
    
    def run_backtest(self, df: pd.DataFrame, long_regime: str, 
                    short_regime: Optional[str] = None) -> pd.DataFrame:
        """
        Execute backtest with proper long/short/flat handling.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Data with Regime column
        long_regime : str
            Which regime to go long (e.g., "Bullish")
        short_regime : str or None
            Which regime to go short (None = cash instead)
        
        Returns:
        --------
        pd.DataFrame with backtest results
        """
        results = df.reset_index(drop=True).copy()
        
        print("\n" + "-"*80)
        print("EXECUTING BACKTEST")
        print("-"*80)
        
        # ===== GENERATE SIGNALS =====
        # Signal at Close[t] determines position for next day
        results["Signal"] = 0  # Default: cash (flat)
        
        if long_regime:
            results.loc[results["Regime"] == long_regime, "Signal"] = 1
            print(f"Long signal: {long_regime} regime")
        
        if short_regime:
            results.loc[results["Regime"] == short_regime, "Signal"] = -1
            print(f"Short signal: {short_regime} regime")
        else:
            print(f"Short signal: None (cash instead)")
        
        # ===== INITIALIZE TRACKING =====
        results["Position"] = 0       # 1=long, 0=flat, -1=short
        results["Cash"] = 0.0
        results["Holdings"] = 0.0     # Can be negative for shorts
        results["Portfolio_Value"] = 0.0
        results["Strategy_Returns"] = 0.0
        results["Trades"] = ""
        
        # Starting state
        cash = self.initial_capital
        shares = 0  # Can be negative for shorts
        
        results.loc[0, "Cash"] = cash
        results.loc[0, "Portfolio_Value"] = cash
        
        # ===== MAIN BACKTEST LOOP =====
        for i in range(1, len(results)):
            # Desired position based on yesterday's signal
            desired_position = int(results.loc[i-1, "Signal"])
            current_position = int(results.loc[i-1, "Position"])
            
            # Check if we need to trade
            if desired_position != current_position:
                # Execute at Open[i]
                execution_price = results.loc[i, "Open"]
                
                # ===== BRANCH 1: OPENING LONG POSITION =====
                if desired_position == 1 and current_position == 0:
                    # Buy shares with available cash
                    shares = cash / (execution_price * (1 + self.commission_rate))
                    commission = shares * execution_price * self.commission_rate
                    cash = 0  # All cash deployed
                    
                    self.trades.append({
                        "Date": results.loc[i, "Date"],
                        "Type": "BUY",
                        "Price": execution_price,
                        "Shares": shares,
                        "Commission": commission,
                        "Regime": results.loc[i-1, "Regime"]
                    })
                    results.loc[i, "Trades"] = "BUY"
                
                # ===== BRANCH 2: CLOSING LONG POSITION =====
                elif desired_position == 0 and current_position == 1:
                    # Sell all shares
                    commission = shares * execution_price * self.commission_rate
                    cash = shares * execution_price - commission
                    shares = 0
                    
                    self.trades.append({
                        "Date": results.loc[i, "Date"],
                        "Type": "SELL",
                        "Price": execution_price,
                        "Shares": shares,
                        "Commission": commission,
                        "Regime": results.loc[i-1, "Regime"]
                    })
                    results.loc[i, "Trades"] = "SELL"
                
                # ===== BRANCH 3: OPENING SHORT POSITION =====
                elif desired_position == -1 and current_position == 0:
                    # Short: Borrow and sell shares
                    # Receive cash from sale minus commission
                    shares_to_short = cash / (execution_price * (1 - self.commission_rate))
                    commission = shares_to_short * execution_price * self.commission_rate
                    cash = cash + shares_to_short * execution_price - commission
                    shares = -shares_to_short  # Negative shares = short position
                    
                    self.trades.append({
                        "Date": results.loc[i, "Date"],
                        "Type": "SHORT",
                        "Price": execution_price,
                        "Shares": shares_to_short,  # Store as positive for clarity
                        "Commission": commission,
                        "Regime": results.loc[i-1, "Regime"]
                    })
                    results.loc[i, "Trades"] = "SHORT"
                
                # ===== BRANCH 4: CLOSING SHORT POSITION =====
                elif desired_position == 0 and current_position == -1:
                    # Cover: Buy back borrowed shares
                    shares_to_cover = abs(shares)
                    commission = shares_to_cover * execution_price * self.commission_rate
                    cash = cash - shares_to_cover * execution_price - commission
                    shares = 0
                    
                    self.trades.append({
                        "Date": results.loc[i, "Date"],
                        "Type": "COVER",
                        "Price": execution_price,
                        "Shares": shares_to_cover,
                        "Commission": commission,
                        "Regime": results.loc[i-1, "Regime"]
                    })
                    results.loc[i, "Trades"] = "COVER"
                
                # ===== BRANCH 5: LONG TO SHORT =====
                elif desired_position == -1 and current_position == 1:
                    # Close long first
                    commission_sell = shares * execution_price * self.commission_rate
                    cash = shares * execution_price - commission_sell
                    
                    # Then open short
                    shares_to_short = cash / (execution_price * (1 - self.commission_rate))
                    commission_short = shares_to_short * execution_price * self.commission_rate
                    cash = cash + shares_to_short * execution_price - commission_short
                    shares = -shares_to_short
                    
                    total_commission = commission_sell + commission_short
                    
                    self.trades.append({
                        "Date": results.loc[i, "Date"],
                        "Type": "SELL+SHORT",
                        "Price": execution_price,
                        "Shares": shares_to_short,
                        "Commission": total_commission,
                        "Regime": results.loc[i-1, "Regime"]
                    })
                    results.loc[i, "Trades"] = "SELL+SHORT"
                
                # ===== BRANCH 6: SHORT TO LONG =====
                elif desired_position == 1 and current_position == -1:
                    # Cover short first
                    shares_to_cover = abs(shares)
                    commission_cover = shares_to_cover * execution_price * self.commission_rate
                    cash = cash - shares_to_cover * execution_price - commission_cover
                    
                    # Then go long
                    shares_to_buy = cash / (execution_price * (1 + self.commission_rate))
                    commission_buy = shares_to_buy * execution_price * self.commission_rate
                    cash = 0
                    shares = shares_to_buy
                    
                    total_commission = commission_cover + commission_buy
                    
                    self.trades.append({
                        "Date": results.loc[i, "Date"],
                        "Type": "COVER+BUY",
                        "Price": execution_price,
                        "Shares": shares_to_buy,
                        "Commission": total_commission,
                        "Regime": results.loc[i-1, "Regime"]
                    })
                    results.loc[i, "Trades"] = "COVER+BUY"
            
            # ===== UPDATE PORTFOLIO STATE =====
            # Position: 1 if long, -1 if short, 0 if flat
            if shares > 0:
                results.loc[i, "Position"] = 1
            elif shares < 0:
                results.loc[i, "Position"] = -1
            else:
                results.loc[i, "Position"] = 0
            
            results.loc[i, "Cash"] = cash
            
            # Mark-to-market at Close (CONSISTENT valuation basis)
            # For shorts: holdings are negative (liability)
            results.loc[i, "Holdings"] = shares * results.loc[i, "Close"]
            
            # Total portfolio value = cash + holdings
            # For shorts: holdings < 0, so portfolio value decreases as price rises
            results.loc[i, "Portfolio_Value"] = cash + shares * results.loc[i, "Close"]
        
        # ===== CALCULATE RETURNS =====
        # Close-to-Close percentage change (CONSISTENT with benchmarks)
        results["Strategy_Returns"] = results["Portfolio_Value"].pct_change()
        
        # Cumulative returns (compound growth)
        results["Cumulative_Returns"] = (1 + results["Strategy_Returns"]).cumprod()
        
        # ===== SUMMARY =====
        total_trades = len(self.trades)
        trade_types = {}
        for t in self.trades:
            trade_types[t["Type"]] = trade_types.get(t["Type"], 0) + 1
        
        print(f"\n✓ Backtest completed")
        print(f"  Total trades: {total_trades}")
        for trade_type, count in trade_types.items():
            print(f"    {trade_type}: {count}")
        print(f"  Initial capital: ${self.initial_capital:,.2f}")
        print(f"  Final value: ${results.iloc[-1]['Portfolio_Value']:,.2f}")
        print(f"  Total return: {(results.iloc[-1]['Portfolio_Value'] / self.initial_capital - 1) * 100:.2f}%")
        
        return results
    
    def add_buy_hold_benchmark(self, results: pd.DataFrame, price_df: pd.DataFrame, 
                              ticker_name: str) -> pd.DataFrame:
        """
        Add buy-and-hold benchmark with hardened data validation.
        
        IMPROVEMENTS:
        1. Inner join to ensure date alignment
        2. Validate that benchmark data exists before computing
        3. Assert non-NaN prices before calculations
        4. Consistent Close-to-Close returns
        
        Parameters:
        -----------
        results : pd.DataFrame
            Main results dataframe
        price_df : pd.DataFrame
            Benchmark price data
        ticker_name : str
            Name for the benchmark (e.g., 'SPY', 'URTH')
        
        Returns:
        --------
        pd.DataFrame with benchmark columns added
        """
        print(f"\nAdding {ticker_name} buy-and-hold benchmark...")
        
        # ===== HARDENED MERGE: INNER JOIN =====
        # Only keep dates that exist in both datasets
        price_aligned = price_df[["Date", "Open", "Close"]].rename(
            columns={"Open": f"{ticker_name}_Open", "Close": f"{ticker_name}_Close"}
        )
        
        # Merge with inner join to intersect dates
        results_orig_len = len(results)
        results = results.merge(price_aligned, on="Date", how="inner")
        results_new_len = len(results)
        
        if results_new_len < results_orig_len:
            print(f"⚠ Inner join reduced data from {results_orig_len} to {results_new_len} rows")
        
        # ===== VALIDATE DATA EXISTS =====
        # Drop initial rows where benchmark data is NaN
        bench_open_col = f"{ticker_name}_Open"
        bench_close_col = f"{ticker_name}_Close"
        
        initial_len = len(results)
        results = results.dropna(subset=[bench_open_col, bench_close_col]).reset_index(drop=True)
        dropped = initial_len - len(results)
        
        if dropped > 0:
            print(f"⚠ Dropped {dropped} rows with missing benchmark data")
        
        if len(results) == 0:
            raise ValueError(f"No valid data after merging {ticker_name} benchmark")
        
        # ===== VALIDATE FIRST PRICES =====
        first_open = results.loc[0, bench_open_col]
        first_close = results.loc[0, bench_close_col]
        
        # Assert non-NaN before proceeding
        assert not np.isnan(first_open), f"First Open price is NaN for {ticker_name}"
        assert not np.isnan(first_close), f"First Close price is NaN for {ticker_name}"
        assert first_open > 0, f"First Open price is non-positive for {ticker_name}"
        assert first_close > 0, f"First Close price is non-positive for {ticker_name}"
        
        print(f"✓ Benchmark data validated: {len(results)} rows, first Open=${first_open:.2f}, first Close=${first_close:.2f}")
        
        # ===== CALCULATE BENCHMARK PORTFOLIO =====
        # Buy at first Open with commission
        shares = self.initial_capital / (first_open * (1 + self.commission_rate))
        commission_buy = shares * first_open * self.commission_rate
        
        # Portfolio value during holding: mark-to-market at Close (CONSISTENT)
        col_prefix = f"{ticker_name}_BH"
        results[f"{col_prefix}_Value"] = shares * results[bench_close_col]
        
        # Adjust first day for buy commission
        results.loc[0, f"{col_prefix}_Value"] = self.initial_capital - commission_buy
        
        # Adjust last day for sell commission (if sold at Close)
        last_idx = len(results) - 1
        last_close = results.loc[last_idx, bench_close_col]
        commission_sell = shares * last_close * self.commission_rate
        results.loc[last_idx, f"{col_prefix}_Value"] = shares * last_close - commission_sell
        
        # Calculate returns (Close-to-Close, CONSISTENT)
        results[f"{col_prefix}_Returns"] = results[bench_close_col].pct_change()
        results[f"{col_prefix}_Cumulative"] = (1 + results[f"{col_prefix}_Returns"]).cumprod()
        
        # ===== SUMMARY =====
        final_value = results.loc[last_idx, f"{col_prefix}_Value"]
        total_return = (final_value / self.initial_capital - 1) * 100
        
        print(f"✓ {ticker_name} benchmark added:")
        print(f"  Final value: ${final_value:,.2f}")
        print(f"  Total return: {total_return:.2f}%")
        
        return results


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

class PerformanceMetrics:
    """
    Calculate comprehensive performance metrics.
    
    All metrics calculated on Close-to-Close returns for consistency.
    """
    
    @staticmethod
    def calculate_all_metrics(results: pd.DataFrame, rf_rate: float = 0.02) -> Dict:
        """
        Calculate metrics for strategy and all benchmarks.
        
        Parameters:
        -----------
        results : pd.DataFrame
            Backtest results with returns
        rf_rate : float
            Risk-free rate for Sharpe calculation (default 2% = US Treasury)
        
        Returns:
        --------
        Dict with metrics for each strategy/benchmark
        """
        metrics = {}
        
        # ===== STRATEGY METRICS =====
        strategy_returns = results["Strategy_Returns"].dropna()
        n_years = len(strategy_returns) / 252  # Convert trading days to years
        
        # Calculate max drawdown
        cumulative = (strategy_returns + 1).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative / running_max - 1)
        max_dd = drawdown.min()
        
        metrics["Strategy"] = {
            "Total Return": (results.iloc[-1]["Portfolio_Value"] / results.iloc[0]["Portfolio_Value"]) - 1,
            "CAGR": ((results.iloc[-1]["Portfolio_Value"] / results.iloc[0]["Portfolio_Value"]) ** (1/n_years) - 1) if n_years > 0 else 0,
            "Volatility": strategy_returns.std() * np.sqrt(252),
            "Sharpe": np.sqrt(252) * (strategy_returns.mean() - rf_rate/252) / strategy_returns.std() if strategy_returns.std() > 0 else 0,
            "Max Drawdown": max_dd,
            "Win Rate": (strategy_returns > 0).sum() / len(strategy_returns),
            "Final Value": results.iloc[-1]["Portfolio_Value"]
        }
        
        # ===== BENCHMARK METRICS =====
        for col_prefix in ["SPY_BH", "URTH_BH"]:
            if f"{col_prefix}_Returns" in results.columns:
                bench_returns = results[f"{col_prefix}_Returns"].dropna()
                bench_cumulative = (bench_returns + 1).cumprod()
                bench_running_max = bench_cumulative.expanding().max()
                bench_drawdown = (bench_cumulative / bench_running_max - 1)
                bench_max_dd = bench_drawdown.min()
                
                metrics[col_prefix.replace("_BH", "")] = {
                    "Total Return": (results.iloc[-1][f"{col_prefix}_Value"] / results.iloc[0][f"{col_prefix}_Value"]) - 1,
                    "CAGR": ((results.iloc[-1][f"{col_prefix}_Value"] / results.iloc[0][f"{col_prefix}_Value"]) ** (1/n_years) - 1) if n_years > 0 else 0,
                    "Volatility": bench_returns.std() * np.sqrt(252),
                    "Sharpe": np.sqrt(252) * (bench_returns.mean() - rf_rate/252) / bench_returns.std() if bench_returns.std() > 0 else 0,
                    "Max Drawdown": bench_max_dd,
                    "Final Value": results.iloc[-1][f"{col_prefix}_Value"]
                }
        
        return metrics
    
    @staticmethod
    def print_metrics(metrics: Dict):
        """Print formatted metrics table."""
        print("\n" + "="*100)
        print("PERFORMANCE METRICS (WALK-FORWARD VALIDATED - NO LOOK-AHEAD BIAS)")
        print("="*100)
        
        # Print each strategy/benchmark
        for name, m in metrics.items():
            print(f"\n{name}:")
            print(f"  Total Return:     {m['Total Return']:>10.2%}")
            print(f"  CAGR:             {m['CAGR']:>10.2%}")
            print(f"  Volatility:       {m['Volatility']:>10.2%}")
            print(f"  Sharpe Ratio:     {m['Sharpe']:>10.2f}")
            print(f"  Max Drawdown:     {m['Max Drawdown']:>10.2%}")
            if 'Win Rate' in m:
                print(f"  Win Rate:         {m['Win Rate']:>10.2%}")
            print(f"  Final Value:      ${m['Final Value']:>10,.2f}")
        
        # ===== COMPARATIVE METRICS =====
        if "Strategy" in metrics and "URTH" in metrics:
            print(f"\nRelative to URTH (Global Benchmark):")
            print(f"  Excess Return:    {metrics['Strategy']['Total Return'] - metrics['URTH']['Total Return']:>10.2%}")
            print(f"  Excess CAGR:      {metrics['Strategy']['CAGR'] - metrics['URTH']['CAGR']:>10.2%}")
            print(f"  Sharpe Advantage: {metrics['Strategy']['Sharpe'] - metrics['URTH']['Sharpe']:>10.2f}")
        
        if "Strategy" in metrics and "SPY" in metrics:
            print(f"\nRelative to SPY:")
            print(f"  Excess Return:    {metrics['Strategy']['Total Return'] - metrics['SPY']['Total Return']:>10.2%}")
            print(f"  Excess CAGR:      {metrics['Strategy']['CAGR'] - metrics['SPY']['CAGR']:>10.2%}")
            print(f"  Sharpe Advantage: {metrics['Strategy']['Sharpe'] - metrics['SPY']['Sharpe']:>10.2f}")
        
        print("="*100 + "\n")


# ============================================================================
# VISUALIZATION
# ============================================================================

def plot_results(results: pd.DataFrame, config: StrategyConfig):
    """
    Create comprehensive visualization of backtest results.
    
    Three subplots:
    1. Price with regime coloring
    2. Cumulative returns comparison
    3. Strategy drawdown
    """
    fig, axes = plt.subplots(3, 1, figsize=(15, 12))
    
    # ===== PLOT 1: REGIME SCATTER =====
    regime_colors = {"Bearish": "red", "Neutral": "gray", "Bullish": "green"}
    
    for regime, color in regime_colors.items():
        mask = results["Regime"] == regime
        if mask.sum() > 0:
            axes[0].scatter(
                results.loc[mask, "Date"], 
                results.loc[mask, "Close"],
                c=color, 
                label=regime, 
                alpha=0.6, 
                s=10
            )
    
    axes[0].set_ylabel("Price ($)", fontsize=12)
    axes[0].set_title(
        f"{config.MAIN_TICKER} Price with GMM Regimes (Walk-Forward Validated)", 
        fontsize=14, 
        fontweight="bold"
    )
    axes[0].legend(loc="best")
    axes[0].grid(alpha=0.3)
    
    # ===== PLOT 2: CUMULATIVE RETURNS =====
    axes[1].plot(
        results["Date"], 
        100 * results["Cumulative_Returns"],
        label="GMM Strategy", 
        linewidth=2, 
        color="blue"
    )
    
    if "SPY_BH_Cumulative" in results.columns:
        axes[1].plot(
            results["Date"], 
            100 * results["SPY_BH_Cumulative"],
            label="SPY Buy & Hold", 
            linewidth=2, 
            alpha=0.7, 
            color="orange"
        )
    
    if "URTH_BH_Cumulative" in results.columns:
        axes[1].plot(
            results["Date"], 
            100 * results["URTH_BH_Cumulative"],
            label="URTH Buy & Hold", 
            linewidth=2, 
            alpha=0.7, 
            color="purple"
        )
    
    axes[1].set_ylabel("Cumulative Returns (Base 100)", fontsize=12)
    axes[1].set_title("Strategy Performance vs Benchmarks (Close-to-Close Returns)", fontsize=14, fontweight="bold")
    axes[1].legend(loc="best")
    axes[1].grid(alpha=0.3)
    
    # ===== PLOT 3: DRAWDOWN =====
    strategy_cum = (1 + results["Strategy_Returns"]).cumprod()
    strategy_dd = (strategy_cum / strategy_cum.expanding().max() - 1) * 100
    
    axes[2].fill_between(
        results["Date"], 
        strategy_dd, 
        0, 
        alpha=0.3, 
        color="red",
        label="Drawdown"
    )
    axes[2].plot(
        results["Date"], 
        strategy_dd, 
        color="darkred", 
        linewidth=1
    )
    
    axes[2].set_xlabel("Date", fontsize=12)
    axes[2].set_ylabel("Drawdown (%)", fontsize=12)
    axes[2].set_title("Strategy Drawdown", fontsize=14, fontweight="bold")
    axes[2].grid(alpha=0.3)
    axes[2].legend(loc="best")
    
    plt.tight_layout()
    plt.show()


def plot_regime_characteristics(results: pd.DataFrame, config: StrategyConfig):
    """
    Plot regime characteristics to understand what each regime captures.
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    df_analysis = results.dropna(subset=["Regime"])
    
    regime_order = ["Bearish", "Neutral", "Bullish"]
    colors = ["red", "gray", "green"]
    
    # ===== PLOT 1: YANG-ZHANG VOLATILITY BY REGIME =====
    for i, regime in enumerate(regime_order):
        mask = df_analysis["Regime"] == regime
        if mask.sum() > 0:
            data = df_analysis.loc[mask, "YangZhang_Vol"]
            axes[0, 0].hist(
                data, 
                bins=30, 
                alpha=0.6, 
                label=regime, 
                color=colors[i]
            )
    
    axes[0, 0].set_xlabel("Yang-Zhang Volatility", fontsize=11)
    axes[0, 0].set_ylabel("Frequency", fontsize=11)
    axes[0, 0].set_title("Volatility Distribution by Regime", fontsize=12, fontweight="bold")
    axes[0, 0].legend()
    axes[0, 0].grid(alpha=0.3)
    
    # ===== PLOT 2: SMA CROSSOVER BY REGIME =====
    for i, regime in enumerate(regime_order):
        mask = df_analysis["Regime"] == regime
        if mask.sum() > 0:
            data = df_analysis.loc[mask, "SMA_Cross_Norm"]
            axes[0, 1].hist(
                data, 
                bins=30, 
                alpha=0.6, 
                label=regime, 
                color=colors[i]
            )
    
    axes[0, 1].set_xlabel("SMA Crossover (Normalized)", fontsize=11)
    axes[0, 1].set_ylabel("Frequency", fontsize=11)
    axes[0, 1].set_title("SMA Crossover Distribution by Regime", fontsize=12, fontweight="bold")
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.3)
    
    # ===== PLOT 3: DAILY RETURNS BY REGIME =====
    regime_returns = []
    
    for regime in regime_order:
        mask = df_analysis["Regime"] == regime
        if mask.sum() > 0:
            regime_returns.append(df_analysis.loc[mask, "Returns_CC"].dropna())
    
    bp = axes[1, 0].boxplot(
        regime_returns, 
        labels=regime_order,
        patch_artist=True
    )
    
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    axes[1, 0].set_ylabel("Daily Returns", fontsize=11)
    axes[1, 0].set_title("Daily Return Distribution by Regime", fontsize=12, fontweight="bold")
    axes[1, 0].grid(alpha=0.3, axis='y')
    axes[1, 0].axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    
    # ===== PLOT 4: REGIME TRANSITIONS =====
    regime_transitions = pd.crosstab(
        df_analysis["Regime"], 
        df_analysis["Regime"].shift(-1),
        normalize="index"
    )
    
    for regime in regime_order:
        if regime not in regime_transitions.index:
            regime_transitions.loc[regime] = 0
        if regime not in regime_transitions.columns:
            regime_transitions[regime] = 0
    
    regime_transitions = regime_transitions.loc[regime_order, regime_order]
    
    sns.heatmap(
        regime_transitions,
        annot=True,
        fmt=".2f",
        cmap="YlOrRd",
        ax=axes[1, 1],
        cbar_kws={"label": "Transition Probability"}
    )
    
    axes[1, 1].set_xlabel("Next Regime", fontsize=11)
    axes[1, 1].set_ylabel("Current Regime", fontsize=11)
    axes[1, 1].set_title("Regime Transition Matrix", fontsize=12, fontweight="bold")
    
    plt.tight_layout()
    plt.show()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function with complete walk-forward validation pipeline.
    """
    
    print("\n" + "="*100)
    print("GMM REGIME DETECTION STRATEGY - PRODUCTION-LEVEL IMPLEMENTATION")
    print("="*100)
    
    # ===== INITIALIZE CONFIGURATION =====
    config = StrategyConfig()
    
    print(f"\nConfiguration:")
    print(f"  Date Range: {config.START_DATE} to {config.END_DATE}")
    print(f"  Ticker: {config.MAIN_TICKER}")
    print(f"  Benchmark: {config.BENCHMARK_TICKER}")
    print(f"  Initial Capital: ${config.INITIAL_CAPITAL:,.0f}")
    print(f"  Commission Rate: {config.COMMISSION_RATE:.3%}")
    print(f"\n  Features:")
    print(f"    - SMA {config.SMA_SHORT} vs {config.SMA_LONG} (normalized)")
    print(f"    - Yang-Zhang volatility (window={config.YZ_WINDOW})")
    print(f"\n  GMM Parameters:")
    print(f"    - Components: {config.GMM_N_COMPONENTS}")
    print(f"    - Covariance: {config.GMM_COVARIANCE_TYPE}")
    print(f"    - Min cluster samples: {config.MIN_CLUSTER_SAMPLES}")
    print(f"\n  Walk-Forward:")
    print(f"    - Min training: {config.MIN_TRAINING_DAYS} days")
    print(f"    - Refit frequency: {config.REFIT_FREQUENCY} days")
    print(f"\n  Trading Logic:")
    print(f"    - Long regime: {config.LONG_REGIME}")
    print(f"    - Short regime: {config.SHORT_REGIME if config.SHORT_REGIME else 'None (cash)'}")
    
    # ===== DATA ACQUISITION =====
    print("\n" + "-"*100)
    print("DATA ACQUISITION")
    print("-"*100)
    
    fetcher = DataFetcher(config.FMP_API_KEY)
    
    df_spy = fetcher.fetch_historical_data(
        config.MAIN_TICKER, 
        config.START_DATE, 
        config.END_DATE
    )
    
    df_urth = fetcher.fetch_historical_data(
        config.BENCHMARK_TICKER, 
        config.START_DATE, 
        config.END_DATE
    )
    
    # ===== FEATURE ENGINEERING =====
    print("\n" + "-"*100)
    print("FEATURE ENGINEERING")
    print("-"*100)
    
    df_features = FeatureEngine.prepare_features(df_spy, config)
    
    # ===== WALK-FORWARD REGIME DETECTION =====
    detector = WalkForwardGMMRegimeDetector(config)
    df_regimes, folds = detector.walk_forward_predict(df_features)
    
    # ===== BACKTESTING =====
    print("\n" + "-"*100)
    print("BACKTESTING")
    print("-"*100)
    
    engine = BacktestEngine(config.INITIAL_CAPITAL, config.COMMISSION_RATE)
    
    results = engine.run_backtest(
        df_regimes,
        long_regime=config.LONG_REGIME,
        short_regime=config.SHORT_REGIME
    )
    
    # ===== ADD BENCHMARKS =====
    print("\nAdding benchmarks...")
    
    # SPY benchmark
    results = engine.add_buy_hold_benchmark(results, df_regimes, "SPY")
    
    # URTH benchmark
    results = engine.add_buy_hold_benchmark(results, df_urth, "URTH")
    
    # ===== PERFORMANCE ANALYSIS =====
    print("\n" + "-"*100)
    print("PERFORMANCE ANALYSIS")
    print("-"*100)
    
    metrics = PerformanceMetrics.calculate_all_metrics(results)
    PerformanceMetrics.print_metrics(metrics)
    
    # ===== REGIME ANALYSIS =====
    print("\n" + "-"*100)
    print("REGIME STATISTICS")
    print("-"*100)
    
    regime_stats = results.groupby("Regime").agg({
        "Returns_CC": ["count", "mean", "std"],
        "YangZhang_Vol": "mean",
        "SMA_Cross_Norm": "mean"
    }).round(4)
    
    print("\nRegime characteristics:")
    print(regime_stats)
    
    # ===== VISUALIZATIONS =====
    print("\n" + "-"*100)
    print("GENERATING VISUALIZATIONS")
    print("-"*100)
    
    plot_results(results, config)
    plot_regime_characteristics(results, config)
    
    # ===== EXPORT RESULTS =====
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    results.to_csv(f"gmm_walkforward_results_{timestamp}.csv", index=False)
    pd.DataFrame(engine.trades).to_csv(f"gmm_walkforward_trades_{timestamp}.csv", index=False)
    pd.DataFrame(folds).to_csv(f"gmm_walkforward_folds_{timestamp}.csv", index=False)
    
    print(f"\n✓ Results exported with timestamp {timestamp}")
    
    # ===== FINAL SUMMARY =====
    print("\n" + "="*100)
    print("EXECUTION COMPLETE - PRODUCTION-READY")
    print("="*100)
    
    print(f"\nKey Results:")
    print(f"  Strategy Return: {metrics['Strategy']['Total Return']:.2%}")
    print(f"  Strategy CAGR: {metrics['Strategy']['CAGR']:.2%}")
    print(f"  Strategy Sharpe: {metrics['Strategy']['Sharpe']:.2f}")
    
    if "URTH" in metrics:
        print(f"  URTH Return: {metrics['URTH']['Total Return']:.2%}")
        print(f"  URTH CAGR: {metrics['URTH']['CAGR']:.2%}")
        print(f"  Excess Return: {metrics['Strategy']['Total Return'] - metrics['URTH']['Total Return']:.2%}")
    
    print("\n" + "="*100 + "\n")
    
    return results, metrics, folds


if __name__ == "__main__":
    results, metrics, folds = main()
Final Thoughts
In an era of increasing market volatility and uncertainty, strategies that dynamically adjust risk exposure will likely outperform static approaches on a risk-adjusted basis.

The 1.00 Sharpe ratio achieved here isn’t magic — it’s the result of:

Sound feature engineering (volatility + momentum)
Appropriate algorithm selection (GMM)
Rigorous validation (walk-forward)
Disciplined execution (systematic rules)
As more investors embrace quantitative approaches, the key differentiator won’t be finding alpha (increasingly difficult) but managing risk intelligently.

Regime detection is one powerful tool in that arsenal.

Disclaimer: This article is for educational purposes only and does not constitute investment advice. Past performance does not guarantee future results. All trading involves risk of loss.