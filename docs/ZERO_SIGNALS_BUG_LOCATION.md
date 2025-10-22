# Zero Signals Bug - Exact Location

## File: `/src/strategies/momentum.py`

### Lines 94-106: The Problematic Logic

```python
# Line 94-99: BUY SIGNAL (TOO STRICT)
if (current['rsi'] > rsi_oversold and                    # RSI crossing up from oversold
    previous['rsi'] <= rsi_oversold and                  # Previous bar was oversold
    current['macd'] > current['macd_signal'] and         # ❌ MACD must be above signal
    previous['macd'] <= previous['macd_signal']):        # ❌ AND must cross THIS bar
    signal_type = SignalType.BUY

# Line 102-106: SELL SIGNAL (TOO STRICT)  
elif (current['rsi'] < rsi_overbought and                # RSI crossing down from overbought
      previous['rsi'] >= rsi_overbought and              # Previous bar was overbought
      current['macd'] < current['macd_signal'] and       # ❌ MACD must be below signal
      previous['macd'] >= previous['macd_signal']):      # ❌ AND must cross THIS bar
    signal_type = SignalType.SELL
```

## The Problem

Lines 97-98 (buy) and 104-105 (sell) require **exact same-bar crossover** of MACD. This is extremely rare because:

1. RSI (14-period momentum) and MACD (12/26/9 trend) respond to different market dynamics
2. Probability of both crossing on same bar is very low
3. Result: **100% signal rejection** (54 RSI signals → 0 final signals)

## The Fix (Choose One)

### Option 1: Use MACD Direction (RECOMMENDED)

```python
# Buy: RSI oversold + MACD bullish
if (current['rsi'] > rsi_oversold and
    previous['rsi'] <= rsi_oversold and
    current['macd'] > 0):  # ✓ Just check if MACD is positive
    signal_type = SignalType.BUY

# Sell: RSI overbought + MACD bearish
elif (current['rsi'] < rsi_overbought and
      previous['rsi'] >= rsi_overbought and
      current['macd'] < 0):  # ✓ Just check if MACD is negative
    signal_type = SignalType.SELL
```

**Expected Signals:** ~15-20 across all symbols

### Option 2: Remove MACD Requirement

```python
# Buy: RSI oversold only
if (current['rsi'] > rsi_oversold and
    previous['rsi'] <= rsi_oversold):
    signal_type = SignalType.BUY

# Sell: RSI overbought only
elif (current['rsi'] < rsi_overbought and
      previous['rsi'] >= rsi_overbought):
    signal_type = SignalType.SELL
```

**Expected Signals:** ~54 with current params (35/65), ~56 with industry standard (30/70)

## Verification

To verify the fix works, run the backtest after applying changes:

```bash
python3 scripts/run_backtest.py --symbols AAPL MSFT GOOGL --start-date 2024-01-01
```

Expected output after fix:
- **Before:** "Generated 0 signals"
- **After (Option 1):** "Generated 15-20 signals"  
- **After (Option 2):** "Generated 50-56 signals"

## Additional Recommendation

Add logging in `momentum.py` after line 129:

```python
if len(signals) == 0:
    logger.warning(
        f"⚠️  Zero signals generated for {data.attrs.get('symbol', 'UNKNOWN')}. "
        f"RSI range: {data['rsi'].min():.2f}-{data['rsi'].max():.2f}, "
        f"Oversold threshold: {rsi_oversold}, Overbought threshold: {rsi_overbought}"
    )
```

This will alert users when signal generation fails.
