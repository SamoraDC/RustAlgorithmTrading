"""
Enhanced Momentum Strategy - Usage Examples

This file demonstrates various usage patterns for the EnhancedMomentumStrategy
including basic usage, advanced configuration, and integration scenarios.

Run with:
    python examples/enhanced_momentum_example.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from src.strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    SignalQuality,
    RiskParameters,
    IndicatorThresholds
)
from src.strategies.base import SignalType


def generate_sample_data(
    symbol: str = "AAPL",
    days: int = 200,
    initial_price: float = 150.0,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Generate realistic sample OHLCV data for testing

    Args:
        symbol: Stock symbol
        days: Number of days of data
        initial_price: Starting price
        volatility: Daily volatility (standard deviation)

    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Generating {days} days of sample data for {symbol}")

    dates = pd.date_range(end=datetime.now(), periods=days, freq='1D')
    np.random.seed(42)

    # Generate realistic price movements with trend
    returns = np.random.normal(0.0005, volatility, days)  # Slight upward bias
    prices = initial_price * np.exp(np.cumsum(returns))

    # Create OHLC with realistic intraday movement
    data = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'high': prices * (1 + np.random.uniform(0.0, 0.02, days)),
        'low': prices * (1 + np.random.uniform(-0.02, 0.0, days)),
        'close': prices,
        'volume': np.random.randint(50_000_000, 150_000_000, days)
    }, index=dates)

    # Ensure high >= open/close and low <= open/close
    data['high'] = data[['high', 'open', 'close']].max(axis=1)
    data['low'] = data[['low', 'open', 'close']].min(axis=1)

    data.attrs['symbol'] = symbol
    return data


def example_1_basic_usage():
    """Example 1: Basic strategy usage with default parameters"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage")
    print("="*80)

    # Create strategy with default parameters
    strategy = EnhancedMomentumStrategy(
        symbols=['AAPL'],
        min_signal_quality=SignalQuality.MODERATE
    )

    # Generate sample data
    data = generate_sample_data('AAPL', days=150)

    # Generate signals
    logger.info("Generating signals...")
    signals = strategy.generate_signals(data)

    # Display results
    print(f"\nGenerated {len(signals)} signals")
    print("\nFirst 5 signals:")
    for i, signal in enumerate(signals[:5], 1):
        print(f"\n{i}. {signal.timestamp.date()} - {signal.signal_type.value.upper()}")
        print(f"   Price: ${signal.price:.2f}")
        print(f"   Quality: {signal.metadata['quality']}")
        print(f"   Confidence: {signal.confidence:.2%}")
        print(f"   Stop Loss: ${signal.metadata['stop_loss']:.2f}")
        print(f"   Take Profit: ${signal.metadata['take_profit']:.2f}")
        print(f"   Risk/Reward: {signal.metadata['risk_reward']:.2f}")

    # Show performance summary
    summary = strategy.get_performance_summary()
    print(f"\nPerformance Summary:")
    print(f"Total Signals: {summary['total_signals']}")
    print(f"Quality Distribution: {summary['signals_by_quality']}")


def example_2_conservative_strategy():
    """Example 2: Conservative strategy configuration"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Conservative Strategy")
    print("="*80)

    # Conservative risk parameters
    conservative_risk = RiskParameters(
        max_position_size=0.10,         # 10% max per position
        risk_per_trade=0.01,            # 1% risk per trade
        max_portfolio_exposure=0.40,    # 40% total exposure
        stop_loss_atr_multiple=3.0,     # Wider stops
        take_profit_atr_multiple=2.0,   # Conservative targets
        min_risk_reward_ratio=1.0       # Any positive R:R
    )

    strategy = EnhancedMomentumStrategy(
        symbols=['SPY'],
        risk_params=conservative_risk,
        min_signal_quality=SignalQuality.STRONG,  # Only best signals
        enable_volume_filter=True,
        enable_trend_filter=True
    )

    data = generate_sample_data('SPY', days=150, initial_price=450.0, volatility=0.015)
    signals = strategy.generate_signals(data)

    print(f"\nConservative Strategy Results:")
    print(f"Total Signals: {len(signals)}")
    print(f"Risk per Trade: {conservative_risk.risk_per_trade:.1%}")
    print(f"Max Position Size: {conservative_risk.max_position_size:.1%}")

    if signals:
        avg_rr = np.mean([s.metadata['risk_reward'] for s in signals])
        print(f"Average Risk/Reward: {avg_rr:.2f}")


def example_3_aggressive_strategy():
    """Example 3: Aggressive strategy for active trading"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Aggressive Strategy")
    print("="*80)

    # Aggressive risk parameters
    aggressive_risk = RiskParameters(
        max_position_size=0.25,         # 25% max per position
        risk_per_trade=0.03,            # 3% risk per trade
        max_portfolio_exposure=0.80,    # 80% total exposure
        stop_loss_atr_multiple=1.5,     # Tighter stops
        take_profit_atr_multiple=4.0,   # Larger targets
        min_risk_reward_ratio=2.0       # Higher R:R requirement
    )

    # More responsive indicator settings
    aggressive_indicators = IndicatorThresholds(
        rsi_period=10,                  # Faster RSI
        rsi_oversold=35,
        rsi_overbought=65,
        macd_fast=8,
        macd_slow=17,
        macd_signal=9,
        ema_fast=12,
        ema_slow=26
    )

    strategy = EnhancedMomentumStrategy(
        symbols=['QQQ'],
        risk_params=aggressive_risk,
        indicator_thresholds=aggressive_indicators,
        min_signal_quality=SignalQuality.MODERATE,
        enable_volume_filter=False,     # More signals
        enable_trend_filter=False       # Trade both directions
    )

    data = generate_sample_data('QQQ', days=150, initial_price=380.0, volatility=0.025)
    signals = strategy.generate_signals(data)

    print(f"\nAggressive Strategy Results:")
    print(f"Total Signals: {len(signals)}")
    print(f"Risk per Trade: {aggressive_risk.risk_per_trade:.1%}")
    print(f"Required R:R: {aggressive_risk.min_risk_reward_ratio:.1f}")

    # Analyze signal distribution
    buy_signals = sum(1 for s in signals if s.signal_type == SignalType.BUY)
    sell_signals = sum(1 for s in signals if s.signal_type == SignalType.SELL)
    print(f"Buy Signals: {buy_signals}")
    print(f"Sell Signals: {sell_signals}")


def example_4_position_sizing():
    """Example 4: Position sizing demonstration"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Position Sizing")
    print("="*80)

    strategy = EnhancedMomentumStrategy(
        symbols=['MSFT'],
        min_signal_quality=SignalQuality.MODERATE
    )

    data = generate_sample_data('MSFT', days=100, initial_price=380.0)
    signals = strategy.generate_signals(data)

    if not signals:
        print("No signals generated for this example")
        return

    # Demonstrate position sizing with different account values
    account_values = [50_000, 100_000, 250_000, 500_000]

    print("\nPosition Sizing for First Signal:")
    signal = signals[0]
    print(f"Signal: {signal.signal_type.value.upper()} @ ${signal.price:.2f}")
    print(f"Stop Loss: ${signal.metadata['stop_loss']:.2f}")
    print(f"Confidence: {signal.confidence:.2%}")

    print("\nPosition Sizes by Account Value:")
    for account_value in account_values:
        position_size = strategy.calculate_position_size(
            signal=signal,
            account_value=account_value
        )

        position_value = position_size * signal.price
        position_pct = position_value / account_value

        risk_per_share = abs(signal.price - signal.metadata['stop_loss'])
        total_risk = position_size * risk_per_share
        risk_pct = total_risk / account_value

        print(f"\nAccount: ${account_value:,}")
        print(f"  Position: {position_size:.0f} shares = ${position_value:,.0f} ({position_pct:.1%})")
        print(f"  Risk: ${total_risk:,.0f} ({risk_pct:.2%})")


def example_5_multi_symbol_analysis():
    """Example 5: Multi-symbol portfolio analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Multi-Symbol Portfolio Analysis")
    print("="*80)

    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
    strategy = EnhancedMomentumStrategy(
        symbols=symbols,
        min_signal_quality=SignalQuality.MODERATE
    )

    all_signals = {}

    for symbol in symbols:
        logger.info(f"Analyzing {symbol}...")
        data = generate_sample_data(symbol, days=150)
        signals = strategy.generate_signals(data)
        all_signals[symbol] = signals

    # Portfolio summary
    print("\nPortfolio Analysis:")
    total_signals = sum(len(signals) for signals in all_signals.values())
    print(f"Total Signals: {total_signals}")

    for symbol, signals in all_signals.items():
        if signals:
            buy_count = sum(1 for s in signals if s.signal_type == SignalType.BUY)
            sell_count = sum(1 for s in signals if s.signal_type == SignalType.SELL)
            avg_confidence = np.mean([s.confidence for s in signals])
            avg_rr = np.mean([s.metadata['risk_reward'] for s in signals])

            print(f"\n{symbol}:")
            print(f"  Signals: {len(signals)} (Buy: {buy_count}, Sell: {sell_count})")
            print(f"  Avg Confidence: {avg_confidence:.2%}")
            print(f"  Avg R:R: {avg_rr:.2f}")


def example_6_signal_quality_analysis():
    """Example 6: Analyze signal quality distribution"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Signal Quality Analysis")
    print("="*80)

    # Create strategies with different quality requirements
    strategies = {
        'Permissive (WEAK+)': EnhancedMomentumStrategy(
            symbols=['AAPL'],
            min_signal_quality=SignalQuality.WEAK
        ),
        'Balanced (MODERATE+)': EnhancedMomentumStrategy(
            symbols=['AAPL'],
            min_signal_quality=SignalQuality.MODERATE
        ),
        'Strict (STRONG only)': EnhancedMomentumStrategy(
            symbols=['AAPL'],
            min_signal_quality=SignalQuality.STRONG
        )
    }

    data = generate_sample_data('AAPL', days=200)

    print("\nComparing Signal Quality Requirements:\n")
    for name, strategy in strategies.items():
        signals = strategy.generate_signals(data)
        summary = strategy.get_performance_summary()

        print(f"{name}:")
        print(f"  Total Signals: {len(signals)}")
        print(f"  Quality Distribution: {summary['signals_by_quality']}")

        if signals:
            avg_confidence = np.mean([s.confidence for s in signals])
            print(f"  Avg Confidence: {avg_confidence:.2%}")
        print()


def main():
    """Run all examples"""
    logger.info("Starting Enhanced Momentum Strategy Examples")

    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Conservative Strategy", example_2_conservative_strategy),
        ("Aggressive Strategy", example_3_aggressive_strategy),
        ("Position Sizing", example_4_position_sizing),
        ("Multi-Symbol Analysis", example_5_multi_symbol_analysis),
        ("Signal Quality Analysis", example_6_signal_quality_analysis),
    ]

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Error in {name}: {e}")

    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
