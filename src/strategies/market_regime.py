"""
Market Regime Detection Module

Identifies market conditions to route to optimal strategy:
- TRENDING: Strong directional movement (use Trend Following)
- RANGING: Sideways consolidation (use Mean Reversion)
- VOLATILE: High volatility, uncertain direction (use Momentum with caution)
"""

from enum import Enum
from typing import Dict, Any
import pandas as pd
import numpy as np
from loguru import logger


class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class RegimeDetector:
    """
    Detects market regime using multiple indicators:
    - ADX: Trend strength
    - ATR: Volatility level
    - Bollinger Band Width: Range vs trend
    - Price action: Linear regression fit
    """

    def __init__(
        self,
        adx_period: int = 14,
        atr_period: int = 14,
        bb_period: int = 20,
        lookback: int = 50,
    ):
        """
        Initialize regime detector

        Args:
            adx_period: ADX calculation period
            atr_period: ATR calculation period
            bb_period: Bollinger Bands period
            lookback: Lookback period for regime analysis
        """
        self.adx_period = adx_period
        self.atr_period = atr_period
        self.bb_period = bb_period
        self.lookback = lookback

    def calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX (Average Directional Index)"""
        df = data.copy()

        # True Range
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)

        # Directional Movement
        df['dm_plus'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0),
            0
        )
        df['dm_minus'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0),
            0
        )

        # Smoothed values
        df['tr_smooth'] = df['tr'].rolling(window=period).sum()
        df['dm_plus_smooth'] = df['dm_plus'].rolling(window=period).sum()
        df['dm_minus_smooth'] = df['dm_minus'].rolling(window=period).sum()

        # Directional Indicators
        df['di_plus'] = 100 * (df['dm_plus_smooth'] / df['tr_smooth'])
        df['di_minus'] = 100 * (df['dm_minus_smooth'] / df['tr_smooth'])

        # DX and ADX
        df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
        df['adx'] = df['dx'].rolling(window=period).mean()

        return df['adx']

    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR (Average True Range)"""
        df = data.copy()

        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=period).mean()

        return df['atr']

    def calculate_bb_width(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Bollinger Band Width (normalized)"""
        sma = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()
        bb_width = (2 * std) / sma  # Normalized width
        return bb_width

    def detect_regime(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect current market regime

        Returns:
            Dictionary with:
                - regime: MarketRegime enum
                - confidence: float (0-1)
                - metrics: dict with ADX, ATR, BB_width values
                - recommendation: str
        """
        if len(data) < self.lookback:
            return {
                'regime': MarketRegime.UNKNOWN,
                'confidence': 0.0,
                'metrics': {},
                'recommendation': "Insufficient data for regime detection"
            }

        # Calculate indicators
        adx = self.calculate_adx(data, self.adx_period)
        atr = self.calculate_atr(data, self.atr_period)
        bb_width = self.calculate_bb_width(data, self.bb_period)

        # Get recent values
        recent_data = data.tail(self.lookback)
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
        current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
        current_bb_width = bb_width.iloc[-1] if not pd.isna(bb_width.iloc[-1]) else 0

        # Calculate normalized ATR (ATR / price)
        normalized_atr = current_atr / data['close'].iloc[-1] if data['close'].iloc[-1] > 0 else 0

        # Linear regression fit (R² score)
        recent_prices = recent_data['close'].values
        x = np.arange(len(recent_prices))
        coeffs = np.polyfit(x, recent_prices, 1)
        poly = np.poly1d(coeffs)
        fitted = poly(x)
        r_squared = 1 - (np.sum((recent_prices - fitted) ** 2) / np.sum((recent_prices - np.mean(recent_prices)) ** 2))

        # Regime detection logic
        regime = MarketRegime.UNKNOWN
        confidence = 0.0
        recommendation = ""

        # TRENDING: High ADX + Good linear fit + Moderate BB width
        if current_adx > 25 and r_squared > 0.7:
            regime = MarketRegime.TRENDING
            confidence = min((current_adx - 25) / 25, 1.0) * r_squared
            recommendation = "Use Trend Following strategy"

        # RANGING: Low ADX + Narrow BB width + Poor linear fit
        elif current_adx < 20 and current_bb_width < 0.05 and r_squared < 0.5:
            regime = MarketRegime.RANGING
            confidence = (20 - current_adx) / 20 * (1 - r_squared)
            recommendation = "Use Mean Reversion strategy"

        # VOLATILE: High ATR + Wide BB width + Any ADX
        elif normalized_atr > 0.03 or current_bb_width > 0.08:
            regime = MarketRegime.VOLATILE
            confidence = min(normalized_atr / 0.05, current_bb_width / 0.1)
            recommendation = "Use Momentum strategy with reduced position size"

        # DEFAULT: Mixed signals - use momentum
        else:
            regime = MarketRegime.VOLATILE
            confidence = 0.5
            recommendation = "Mixed signals - use Momentum strategy"

        logger.info(
            f"Market Regime: {regime.value.upper()} (confidence: {confidence:.2f}) | "
            f"ADX={current_adx:.1f}, ATR={normalized_atr:.3f}, BB_width={current_bb_width:.3f}, R²={r_squared:.3f}"
        )

        return {
            'regime': regime,
            'confidence': float(confidence),
            'metrics': {
                'adx': float(current_adx),
                'atr': float(current_atr),
                'normalized_atr': float(normalized_atr),
                'bb_width': float(current_bb_width),
                'r_squared': float(r_squared),
            },
            'recommendation': recommendation
        }

    def get_optimal_strategy(self, regime: MarketRegime) -> str:
        """
        Get optimal strategy name for given regime

        Args:
            regime: MarketRegime enum

        Returns:
            Strategy class name
        """
        strategy_map = {
            MarketRegime.TRENDING: "TrendFollowing",
            MarketRegime.RANGING: "MeanReversion",
            MarketRegime.VOLATILE: "SimplifiedMomentumStrategy",
            MarketRegime.UNKNOWN: "SimplifiedMomentumStrategy",  # Default
        }
        return strategy_map[regime]
