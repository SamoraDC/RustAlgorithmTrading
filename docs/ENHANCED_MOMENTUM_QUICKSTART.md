# Enhanced Momentum Strategy - Quick Start Guide

## Installation

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt
```

## Basic Usage

```python
from src.strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    SignalQuality
)
import pandas as pd

# Create strategy
strategy = EnhancedMomentumStrategy(
    symbols=['AAPL'],
    min_signal_quality=SignalQuality.MODERATE
)

# Load your data (must have OHLCV columns)
data = pd.read_csv('market_data.csv', parse_dates=['timestamp'], index_col='timestamp')
data.attrs['symbol'] = 'AAPL'

# Generate signals
signals = strategy.generate_signals(data)

# Use signals
for signal in signals:
    print(f"{signal.timestamp}: {signal.signal_type.value.upper()} @ ${signal.price:.2f}")
    print(f"  Quality: {signal.metadata['quality']}")
    print(f"  Confidence: {signal.confidence:.2%}")
    print(f"  Stop Loss: ${signal.metadata['stop_loss']:.2f}")
    print(f"  Take Profit: ${signal.metadata['take_profit']:.2f}")
```

## Configuration Presets

### Conservative (Low Risk)
```python
from src.strategies.enhanced_momentum import RiskParameters

conservative = RiskParameters(
    max_position_size=0.10,      # 10% max per position
    risk_per_trade=0.01,         # 1% risk
    stop_loss_atr_multiple=3.0   # Wide stops
)

strategy = EnhancedMomentumStrategy(
    symbols=['SPY'],
    risk_params=conservative,
    min_signal_quality=SignalQuality.STRONG
)
```

### Balanced (Medium Risk)
```python
balanced = RiskParameters(
    max_position_size=0.15,      # 15% max per position
    risk_per_trade=0.02,         # 2% risk
    stop_loss_atr_multiple=2.0   # Standard stops
)

strategy = EnhancedMomentumStrategy(
    symbols=['AAPL', 'MSFT'],
    risk_params=balanced,
    min_signal_quality=SignalQuality.MODERATE
)
```

### Aggressive (High Risk)
```python
aggressive = RiskParameters(
    max_position_size=0.25,      # 25% max per position
    risk_per_trade=0.03,         # 3% risk
    stop_loss_atr_multiple=1.5   # Tight stops
)

strategy = EnhancedMomentumStrategy(
    symbols=['QQQ'],
    risk_params=aggressive,
    min_signal_quality=SignalQuality.MODERATE,
    enable_trend_filter=False    # More signals
)
```

## Position Sizing

```python
from src.strategies.base import Signal, SignalType
from datetime import datetime

# After generating signals
signal = signals[0]  # Get first signal

# Calculate position size
account_value = 100000  # $100k account
position_size = strategy.calculate_position_size(
    signal=signal,
    account_value=account_value
)

print(f"Buy {position_size:.0f} shares @ ${signal.price:.2f}")
print(f"Position Value: ${position_size * signal.price:,.2f}")
print(f"Stop Loss: ${signal.metadata['stop_loss']:.2f}")
```

## Performance Monitoring

```python
# After running strategy
summary = strategy.get_performance_summary()

print(f"Total Signals: {summary['total_signals']}")
print(f"Quality Distribution:")
for quality, count in summary['signals_by_quality'].items():
    print(f"  {quality}: {count}")
```

## Common Patterns

### Multi-Symbol Portfolio
```python
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
strategy = EnhancedMomentumStrategy(
    symbols=symbols,
    min_signal_quality=SignalQuality.MODERATE
)

all_signals = {}
for symbol in symbols:
    data = load_data(symbol)  # Your data loading function
    data.attrs['symbol'] = symbol
    all_signals[symbol] = strategy.generate_signals(data)
```

### With Volume Filter
```python
strategy = EnhancedMomentumStrategy(
    symbols=['AAPL'],
    enable_volume_filter=True,     # Require 1.5x avg volume
    enable_trend_filter=True,      # Only trade with trend
    min_signal_quality=SignalQuality.MODERATE
)
```

### Custom Indicators
```python
from src.strategies.enhanced_momentum import IndicatorThresholds

custom_indicators = IndicatorThresholds(
    rsi_period=21,           # Longer RSI
    rsi_oversold=25,         # More extreme
    rsi_overbought=75,
    macd_fast=8,
    macd_slow=21
)

strategy = EnhancedMomentumStrategy(
    symbols=['AAPL'],
    indicator_thresholds=custom_indicators
)
```

## Signal Metadata

Each signal includes comprehensive metadata:

```python
signal.metadata = {
    'quality': 'strong',           # Signal quality tier
    'rsi': 32.45,                  # RSI value
    'macd': 0.0234,                # MACD value
    'macd_histogram': 0.0156,      # MACD histogram
    'trend': 'bullish',            # Trend direction
    'volume_ratio': 1.85,          # Volume vs average
    'atr': 2.34,                   # Current ATR
    'stop_loss': 98.32,            # Stop loss price
    'take_profit': 105.68,         # Take profit price
    'risk_reward': 2.14,           # Risk/reward ratio
    'rationale': {...}             # Full trade rationale
}
```

## Troubleshooting

### No Signals Generated
- Lower `min_signal_quality` to `SignalQuality.WEAK`
- Disable filters: `enable_volume_filter=False`
- Check data has sufficient history (60+ bars)
- Verify OHLCV columns exist

### Too Many Signals
- Raise `min_signal_quality` to `SignalQuality.STRONG`
- Enable filters: `enable_volume_filter=True`
- Increase `min_risk_reward_ratio`

### Position Size Too Large/Small
- Adjust `max_position_size` in RiskParameters
- Adjust `risk_per_trade` percentage
- Check stop loss distance (affects sizing)

## Examples

See `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/examples/enhanced_momentum_example.py` for 6 complete usage examples.

## Documentation

- Full docs: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/enhanced_momentum_strategy.md`
- Implementation: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/implementation_summary.md`
- Tests: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/tests/unit/python/test_enhanced_momentum.py`
