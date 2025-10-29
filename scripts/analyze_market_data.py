#!/usr/bin/env python3
"""Analyze market data to understand why strategy fails"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    # Check if we have any cached market data
    data_dir = Path('data/market_data')

    if not data_dir.exists():
        print("No market data found. Run backtest first.")
        return

    files = list(data_dir.glob('*.csv'))
    print(f'Found {len(files)} data files\n')

    if not files:
        print("No CSV files in data/market_data/")
        return

    # Analyze first file
    df = pd.read_csv(files[0], parse_dates=['timestamp'])
    print(f'Analyzing {files[0].name}')
    print(f'Total bars: {len(df)}')
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}\n')

    # Price statistics
    print(f'Price Statistics:')
    print(f'  Range: ${df["close"].min():.2f} - ${df["close"].max():.2f}')
    print(f'  Mean: ${df["close"].mean():.2f}')
    print(f'  Std: ${df["close"].std():.2f}\n')

    # Calculate returns
    df['returns'] = df['close'].pct_change()
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1))

    print(f'Return Statistics:')
    print(f'  Mean daily return: {df["returns"].mean():.4%}')
    print(f'  Std daily return: {df["returns"].std():.4%}')
    print(f'  Annualized Sharpe: {(df["returns"].mean() / df["returns"].std()) * np.sqrt(252):.2f}')
    print(f'  Max daily gain: {df["returns"].max():.2%}')
    print(f'  Max daily loss: {df["returns"].min():.2%}\n')

    # Calculate RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Calculate MACD
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # Calculate SMA
    df['sma_50'] = df['close'].rolling(window=50).mean()

    # Analyze current strategy conditions
    print(f'Strategy Condition Analysis (last 50 bars):')
    recent = df.tail(50)

    # Count RSI crossings
    rsi_cross_up = ((recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50)).sum()
    rsi_cross_down = ((recent['rsi'] < 50) & (recent['rsi'].shift(1) >= 50)).sum()

    print(f'  RSI crosses above 50: {rsi_cross_up}')
    print(f'  RSI crosses below 50: {rsi_cross_down}')

    # Check price vs SMA
    above_sma = (recent['close'] > recent['sma_50']).sum()
    print(f'  Bars above 50 SMA: {above_sma}/{len(recent)} ({above_sma/len(recent):.1%})')

    # MACD bullish
    macd_bullish = (recent['macd'] > recent['macd_signal']).sum()
    print(f'  MACD bullish: {macd_bullish}/{len(recent)} ({macd_bullish/len(recent):.1%}')

    # Strong histogram
    strong_hist_up = (recent['macd_hist'] > 0.0005).sum()
    strong_hist_down = (recent['macd_hist'] < -0.0005).sum()
    print(f'  Strong bullish histogram (>0.0005): {strong_hist_up}')
    print(f'  Strong bearish histogram (<-0.0005): {strong_hist_down}\n')

    # Simulate current entry conditions
    long_conditions = (
        (recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50) &
        (recent['macd'] > recent['macd_signal']) &
        (recent['macd_hist'] > 0.0005) &
        (recent['close'] > recent['sma_50'])
    )

    short_conditions = (
        (recent['rsi'] < 50) & (recent['rsi'].shift(1) >= 50) &
        (recent['macd'] < recent['macd_signal']) &
        (recent['macd_hist'] < -0.0005) &
        (recent['close'] < recent['sma_50'])
    )

    print(f'Entry Signals in Last 50 Bars:')
    print(f'  Long signals: {long_conditions.sum()}')
    print(f'  Short signals: {short_conditions.sum()}')
    print(f'  Total: {long_conditions.sum() + short_conditions.sum()}\n')

    # Show why signals are rare
    print(f'Why So Few Signals?')
    rsi_cross_only = ((recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50)).sum()
    print(f'  RSI crosses 50: {rsi_cross_only}')

    with_macd = (
        (recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50) &
        (recent['macd'] > recent['macd_signal'])
    ).sum()
    print(f'  + MACD bullish: {with_macd}')

    with_hist = (
        (recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50) &
        (recent['macd'] > recent['macd_signal']) &
        (recent['macd_hist'] > 0.0005)
    ).sum()
    print(f'  + Strong histogram: {with_hist}')

    with_sma = long_conditions.sum()
    print(f'  + Above 50 SMA: {with_sma}\n')

    # Suggest better thresholds
    print(f'Suggested Improvements:')

    # Try removing SMA filter
    without_sma = (
        (recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50) &
        (recent['macd'] > recent['macd_signal']) &
        (recent['macd_hist'] > 0.0005)
    ).sum()
    print(f'  Remove SMA filter: {without_sma} signals')

    # Try weaker histogram
    weaker_hist = (
        (recent['rsi'] > 50) & (recent['rsi'].shift(1) <= 50) &
        (recent['macd'] > recent['macd_signal']) &
        (recent['macd_hist'] > 0.0001) &
        (recent['close'] > recent['sma_50'])
    ).sum()
    print(f'  Weaker histogram (0.0001): {weaker_hist} signals')

    # Try RSI 45/55 instead of 50
    rsi_wider = (
        ((recent['rsi'] > 45) & (recent['rsi'].shift(1) <= 45)) &
        (recent['macd'] > recent['macd_signal']) &
        (recent['macd_hist'] > 0.0005) &
        (recent['close'] > recent['sma_50'])
    ).sum()
    print(f'  RSI threshold 45: {rsi_wider} signals\n')

if __name__ == '__main__':
    main()
