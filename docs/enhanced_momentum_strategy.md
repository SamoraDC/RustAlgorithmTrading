# Enhanced Momentum Strategy Documentation

## Overview

The Enhanced Momentum Strategy is a professional-grade quantitative trading strategy that implements multi-indicator confirmation, advanced risk management, and comprehensive signal quality assessment. This strategy is designed for serious quantitative trading with institutional-grade risk controls.

## Key Features

### 1. Multi-Indicator Confirmation
- **RSI (Relative Strength Index)**: Identifies overbought/oversold conditions
- **MACD (Moving Average Convergence Divergence)**: Confirms momentum direction
- **EMA Trend Filter**: Ensures trading with the prevailing trend
- **Volume Confirmation**: Validates signals with volume analysis
- **ATR (Average True Range)**: Volatility-based risk management

### 2. Signal Quality Classification

Signals are classified into four quality tiers:

| Quality | Description | Criteria |
|---------|-------------|----------|
| **STRONG** | All indicators aligned + volume | 100% confluence + volume surge |
| **MODERATE** | Majority indicators aligned | 2/3 indicators + optional volume |
| **WEAK** | Minimal alignment | 1/3 indicators aligned |
| **INVALID** | Contradicting signals | Primary indicators disagree |

### 3. Risk Management

#### Position Sizing
```python
Base Size = (Account Value × Risk %) / (Entry - Stop Loss)
Adjusted Size = Base Size × Signal Confidence × (1 - Portfolio Exposure)
Final Size = min(Adjusted Size, Max Position Size)
```

#### Risk Parameters
- **Max Position Size**: 15% of portfolio (configurable)
- **Risk Per Trade**: 2% of account value
- **Max Portfolio Exposure**: 60% total
- **Stop Loss**: 2.0 × ATR below entry
- **Take Profit**: 3.0 × ATR above entry
- **Minimum Risk/Reward**: 1.5:1

### 4. Professional Features
- Comprehensive logging with DEBUG and INFO levels
- Trade rationale tracking with full indicator context
- Signal quality metrics and performance tracking
- Exposure management across portfolio
- Configurable filters (volume, trend, quality)

## Usage Examples

### Basic Usage

```python
from src.strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    SignalQuality,
    RiskParameters
)

# Create strategy with default parameters
strategy = EnhancedMomentumStrategy(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    min_signal_quality=SignalQuality.MODERATE
)

# Generate signals
import pandas as pd
data = pd.read_csv('market_data.csv')
data.attrs['symbol'] = 'AAPL'
signals = strategy.generate_signals(data)

# Calculate position size
for signal in signals:
    position_size = strategy.calculate_position_size(
        signal=signal,
        account_value=100000,
        current_position=0
    )
    print(f"Signal: {signal.signal_type.value}, Size: {position_size} shares")
```

### Advanced Configuration

```python
from src.strategies.enhanced_momentum import (
    EnhancedMomentumStrategy,
    SignalQuality,
    RiskParameters,
    IndicatorThresholds
)

# Custom risk parameters (aggressive)
risk_params = RiskParameters(
    max_position_size=0.25,        # 25% max per position
    risk_per_trade=0.03,           # 3% risk per trade
    max_portfolio_exposure=0.80,   # 80% total exposure
    stop_loss_atr_multiple=1.5,    # Tighter stops
    take_profit_atr_multiple=4.0,  # Larger targets
    min_risk_reward_ratio=2.0      # Higher R:R requirement
)

# Custom indicator thresholds
indicator_config = IndicatorThresholds(
    rsi_period=21,                 # Longer RSI period
    rsi_oversold=25,               # More extreme oversold
    rsi_overbought=75,             # More extreme overbought
    macd_fast=8,
    macd_slow=21,
    macd_signal=5,
    ema_fast=10,
    ema_slow=30
)

# Create strategy
strategy = EnhancedMomentumStrategy(
    symbols=['SPY', 'QQQ'],
    risk_params=risk_params,
    indicator_thresholds=indicator_config,
    min_signal_quality=SignalQuality.STRONG,  # Only best signals
    enable_volume_filter=True,
    enable_trend_filter=True
)
```

### Conservative Configuration

```python
# Conservative risk parameters
conservative_risk = RiskParameters(
    max_position_size=0.10,        # 10% max per position
    risk_per_trade=0.01,           # 1% risk per trade
    max_portfolio_exposure=0.40,   # 40% total exposure
    stop_loss_atr_multiple=3.0,    # Wider stops
    take_profit_atr_multiple=2.0,  # Conservative targets
    min_risk_reward_ratio=1.0      # Any positive R:R
)

strategy = EnhancedMomentumStrategy(
    symbols=['VTI'],
    risk_params=conservative_risk,
    min_signal_quality=SignalQuality.STRONG,
    enable_volume_filter=True,
    enable_trend_filter=True
)
```

## Signal Metadata

Each signal includes comprehensive metadata:

```python
signal.metadata = {
    'quality': 'strong',              # Signal quality level
    'rsi': 35.2,                      # RSI value
    'macd': 0.0234,                   # MACD value
    'macd_histogram': 0.0156,         # MACD histogram
    'trend': 'bullish',               # Trend direction
    'volume_ratio': 1.8,              # Volume vs average
    'atr': 2.34,                      # Current ATR
    'stop_loss': 98.32,               # Calculated stop loss
    'take_profit': 105.68,            # Calculated take profit
    'risk_reward': 2.1,               # Risk/reward ratio
    'rationale': {...}                # Full trade rationale
}
```

## Trade Rationale

The strategy tracks detailed rationale for every signal:

```python
# Access trade history
for rationale in strategy.trade_history:
    print(rationale.to_dict())

# Example output:
{
    'timestamp': '2024-01-15T14:30:00',
    'symbol': 'AAPL',
    'signal_type': 'buy',
    'signal_quality': 'strong',
    'confidence_score': 0.8542,
    'indicators': {
        'rsi': 32.45,
        'rsi_trend': 'rising_from_oversold',
        'macd': 0.0234,
        'macd_histogram': 0.0156,
        'ema_fast': 182.45,
        'ema_slow': 180.12,
        'trend_direction': 'bullish',
        'volume_ratio': 1.85
    },
    'risk_management': {
        'atr': 2.34,
        'stop_loss': 178.32,
        'take_profit': 186.68,
        'risk_reward': 2.14,
        'position_size': 42.5
    }
}
```

## Performance Metrics

```python
# Get strategy performance summary
summary = strategy.get_performance_summary()

print(summary)
# Output:
{
    'total_signals': 156,
    'signals_by_quality': {
        'strong': 42,
        'moderate': 89,
        'weak': 25,
        'invalid': 0
    },
    'current_positions': 3,
    'total_trades': 156,
    'risk_parameters': {
        'max_position_size': 0.15,
        'risk_per_trade': 0.02,
        'max_portfolio_exposure': 0.60
    }
}
```

## Mathematical Formulas

### RSI (Relative Strength Index)
```
RSI = 100 - [100 / (1 + RS)]
where RS = Average Gain(n) / Average Loss(n)

Gain = max(0, Price(t) - Price(t-1))
Loss = max(0, Price(t-1) - Price(t))
```

### MACD (Moving Average Convergence Divergence)
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line

EMA(t) = α × Price(t) + (1-α) × EMA(t-1)
where α = 2 / (period + 1)
```

### ATR-Based Risk Management
```
Stop Loss = Entry Price ± (ATR × stop_loss_multiple)
Take Profit = Entry Price ± (ATR × take_profit_multiple)

For BUY signals:
  Stop Loss = Entry - (ATR × 2.0)
  Take Profit = Entry + (ATR × 3.0)

For SELL signals:
  Stop Loss = Entry + (ATR × 2.0)
  Take Profit = Entry - (ATR × 3.0)
```

### Position Sizing Formula
```
1. Calculate risk per share:
   Risk = |Entry Price - Stop Loss|

2. Calculate base position:
   Max Risk Amount = Account Value × risk_per_trade
   Base Shares = Max Risk Amount / Risk per Share

3. Adjust for confidence:
   Adjusted Shares = Base Shares × Signal Confidence

4. Adjust for exposure:
   Exposure Ratio = Total Positions / Account Value
   Exposure Factor = max(0, 1 - (Exposure Ratio / max_exposure))
   Final Shares = Adjusted Shares × Exposure Factor

5. Apply maximum limit:
   Max Shares = (Account Value × max_position_size) / Entry Price
   Position Size = min(Final Shares, Max Shares)
```

## Signal Generation Flow

```
1. Data Validation
   ├─ Check OHLCV columns
   └─ Verify minimum data length

2. Indicator Calculation
   ├─ RSI (14-period)
   ├─ MACD (12, 26, 9)
   ├─ EMA (20, 50)
   ├─ ATR (14-period)
   └─ Volume SMA (20-period)

3. Individual Indicator Evaluation
   ├─ RSI Signal + Strength
   ├─ MACD Signal + Strength
   ├─ Trend Direction + Strength
   └─ Volume Confirmation

4. Filter Application
   ├─ Trend Filter (optional)
   ├─ Volume Filter (optional)
   └─ Signal Quality Filter

5. Signal Quality Determination
   ├─ Count indicator confluence
   ├─ Check for contradictions
   └─ Calculate confidence score

6. Risk Metric Calculation
   ├─ ATR-based stop loss
   ├─ ATR-based take profit
   └─ Risk/reward ratio

7. Final Filtering
   ├─ Minimum R:R requirement
   ├─ Signal quality threshold
   └─ Exposure limits

8. Signal Creation
   ├─ Generate Signal object
   ├─ Create TradeRationale
   ├─ Update statistics
   └─ Log comprehensive details
```

## Best Practices

### 1. Parameter Optimization
- Backtest thoroughly before live trading
- Adjust thresholds based on market regime
- Consider asset volatility when setting ATR multiples
- Review signal quality distribution regularly

### 2. Risk Management
- Never exceed 2% risk per trade for conservative approach
- Keep total portfolio exposure under 60%
- Use wider stops (3×ATR) in volatile markets
- Adjust position sizes based on account growth

### 3. Signal Quality
- Prefer STRONG signals for primary strategies
- Use MODERATE signals with additional filters
- Avoid WEAK signals unless testing
- Review INVALID signals to understand contradictions

### 4. Monitoring
- Track signal quality distribution
- Monitor win rate by quality tier
- Analyze stopped-out trades
- Review average R:R of winning trades

### 5. Adaptation
- Increase RSI thresholds in trending markets
- Tighten thresholds in ranging markets
- Enable trend filter in strong trends
- Disable volume filter for low-volume assets

## Performance Considerations

### Computational Efficiency
- Uses vectorized NumPy operations
- Efficient indicator calculations via TechnicalIndicators class
- Minimal memory allocation in signal generation loop
- Single-pass data processing

### Trade-offs
- More filters = fewer signals but higher quality
- Tighter stops = higher win rate but lower R:R
- Larger positions = higher returns but higher risk
- Strict quality requirements = fewer opportunities

## Integration Examples

### Backtesting Integration

```python
from src.backtesting.engine import BacktestEngine
from src.strategies.enhanced_momentum import EnhancedMomentumStrategy

# Create strategy
strategy = EnhancedMomentumStrategy(
    symbols=['AAPL'],
    min_signal_quality=SignalQuality.MODERATE
)

# Run backtest
engine = BacktestEngine(
    strategy=strategy,
    initial_capital=100000,
    commission=0.001
)

results = engine.run(start_date='2023-01-01', end_date='2024-01-01')
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown:.2%}")
```

### Live Trading Integration

```python
from src.api.alpaca_client import AlpacaClient
from src.strategies.enhanced_momentum import EnhancedMomentumStrategy

# Create clients and strategy
client = AlpacaClient()
strategy = EnhancedMomentumStrategy(
    symbols=['SPY', 'QQQ'],
    min_signal_quality=SignalQuality.STRONG
)

# Trading loop
for symbol in strategy.symbols:
    # Fetch latest data
    data = client.get_bars(symbol, timeframe='1Day', limit=100)
    data.attrs['symbol'] = symbol

    # Generate signals
    signals = strategy.generate_signals(data)

    # Execute trades
    for signal in signals:
        if signal.signal_type != SignalType.HOLD:
            position_size = strategy.calculate_position_size(
                signal,
                account_value=client.get_account_value()
            )

            # Place order with risk management
            client.place_order(
                symbol=symbol,
                qty=position_size,
                side='buy' if signal.signal_type == SignalType.BUY else 'sell',
                type='limit',
                limit_price=signal.price,
                stop_loss=signal.metadata['stop_loss'],
                take_profit=signal.metadata['take_profit']
            )
```

## Troubleshooting

### No Signals Generated
- Check if data has sufficient history (>60 bars recommended)
- Verify signal quality threshold isn't too strict
- Review filter settings (trend, volume)
- Check if indicators are calculating (no NaN values)

### Too Many Signals
- Increase minimum signal quality requirement
- Enable trend and volume filters
- Increase risk/reward minimum threshold
- Tighten indicator thresholds

### Poor Performance
- Review signal quality distribution
- Analyze stopped-out trades
- Check if market regime matches parameters
- Consider wider stops in volatile periods
- Verify position sizing isn't too aggressive

## Version History

- **v1.0.0** (2024-01-15): Initial professional release
  - Multi-indicator confirmation system
  - Advanced risk management
  - Signal quality classification
  - Comprehensive logging and rationale tracking

## License

Copyright (c) 2024 Quantitative Research Team
