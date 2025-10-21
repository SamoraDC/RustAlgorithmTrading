"""
Python bridge to Rust signal processing components via PyO3.

This module provides a clean Python interface to the high-performance
Rust feature computation engine built with PyO3 bindings.
"""

import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class MarketBar:
    """Market data bar structure matching Rust Bar type."""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int

    def to_rust_bar(self):
        """Convert to Rust Bar object."""
        try:
            from signal_bridge import Bar
            return Bar(
                symbol=self.symbol,
                open=self.open,
                high=self.high,
                low=self.low,
                close=self.close,
                volume=self.volume,
                timestamp=self.timestamp
            )
        except ImportError as e:
            logger.error(f"Failed to import signal_bridge module: {e}")
            logger.warning("Make sure the Rust library is built: cd rust && cargo build --release")
            raise


class RustFeatureComputer:
    """
    Python wrapper for Rust-based feature computation.

    Provides high-performance technical indicator and feature calculation
    using Rust's SIMD-optimized implementations via PyO3 bindings.

    Example:
        >>> computer = RustFeatureComputer()
        >>> bar = MarketBar("AAPL", 150.0, 152.0, 149.0, 151.0, 1000000, 1234567890)
        >>> features = computer.compute_streaming(bar)
        >>> print(f"Computed {len(features)} features")
    """

    def __init__(self):
        """Initialize the Rust feature computer."""
        try:
            from signal_bridge import FeatureComputer
            self._computer = FeatureComputer()
            logger.info("Rust FeatureComputer initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import signal_bridge: {e}")
            logger.error("Please build the Rust library:")
            logger.error("  cd rust")
            logger.error("  cargo build --release --package signal-bridge")
            logger.error("  export PYTHONPATH=$PWD/target/release:$PYTHONPATH")
            raise RuntimeError("Rust signal_bridge module not available") from e

    def compute_streaming(self, bar: MarketBar) -> List[float]:
        """
        Compute features from a single bar (streaming/real-time mode).

        Args:
            bar: Market data bar

        Returns:
            List of feature values (length varies based on available data)

        Features include:
            - Price (close)
            - RSI (14-period)
            - MACD (line, signal, histogram)
            - EMA (fast, slow, spread)
            - SMA (with distance from price)
            - Volume
            - Price range %
        """
        try:
            rust_bar = bar.to_rust_bar()
            features = self._computer.compute_streaming(rust_bar)
            logger.debug(f"Computed {len(features)} streaming features for {bar.symbol}")
            return features
        except Exception as e:
            logger.error(f"Error computing streaming features: {e}")
            raise

    def compute_batch(self, bars: List[MarketBar]) -> List[List[float]]:
        """
        Compute features from a list of bars (batch/historical mode).

        Uses SIMD-accelerated calculations for improved performance.

        Args:
            bars: List of market data bars

        Returns:
            List of feature vectors, one per bar

        Features include:
            - Price (close)
            - Returns (log returns)
            - Momentum (10-period)
            - Volume
            - Price range %
        """
        try:
            rust_bars = [bar.to_rust_bar() for bar in bars]
            features = self._computer.compute_batch(rust_bars)
            logger.debug(f"Computed batch features for {len(bars)} bars")
            return features
        except Exception as e:
            logger.error(f"Error computing batch features: {e}")
            raise

    def compute_microstructure(
        self,
        bid_price: float,
        ask_price: float,
        bid_depth: float,
        ask_depth: float
    ) -> List[float]:
        """
        Compute market microstructure features from order book data.

        Args:
            bid_price: Best bid price
            ask_price: Best ask price
            bid_depth: Total volume at top bid levels
            ask_depth: Total volume at top ask levels

        Returns:
            List containing:
                [spread, spread_bps, depth_imbalance, bid_depth, ask_depth, mid_price]
        """
        try:
            features = self._computer.compute_microstructure(
                bid_price, ask_price, bid_depth, ask_depth
            )
            logger.debug("Computed microstructure features")
            return features
        except Exception as e:
            logger.error(f"Error computing microstructure features: {e}")
            raise


def test_rust_bridge():
    """Test the Rust bridge functionality."""
    logger.info("Testing Rust feature computation bridge...")

    try:
        # Create feature computer
        computer = RustFeatureComputer()

        # Create test bar
        bar = MarketBar(
            symbol="AAPL",
            open=150.0,
            high=152.5,
            low=149.5,
            close=151.0,
            volume=1_000_000.0,
            timestamp=1234567890
        )

        # Test streaming features
        streaming_features = computer.compute_streaming(bar)
        logger.info(f"✓ Streaming features: {len(streaming_features)} values")
        logger.info(f"  First 5 features: {streaming_features[:5]}")

        # Test batch features
        bars = [
            MarketBar("AAPL", 150.0, 151.0, 149.0, 150.5, 1e6, 1234567890 + i)
            for i in range(20)
        ]
        batch_features = computer.compute_batch(bars)
        logger.info(f"✓ Batch features: {len(batch_features)} bars processed")
        logger.info(f"  Features per bar: {len(batch_features[0])}")

        # Test microstructure features
        micro_features = computer.compute_microstructure(
            bid_price=150.95,
            ask_price=151.05,
            bid_depth=10000.0,
            ask_depth=8000.0
        )
        logger.info(f"✓ Microstructure features: {micro_features}")

        logger.info("✅ All Rust bridge tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Rust bridge test failed: {e}")
        return False


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )

    # Run tests
    success = test_rust_bridge()
    sys.exit(0 if success else 1)
