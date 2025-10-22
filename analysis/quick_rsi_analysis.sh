#!/bin/bash
# Quick RSI Analysis using Python with system packages

cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install --quiet pandas pyarrow numpy 2>&1 | grep -v "Requirement already"

echo "==================== RSI SIGNAL ANALYSIS ===================="
echo ""

# Run quick analysis
python3 << 'EOF'
import pandas as pd
import numpy as np
import json
from pathlib import Path

symbols = ['AAPL', 'MSFT', 'GOOGL']
results = {}

print("LOADING & ANALYZING DATA...\n")

for symbol in symbols:
    # Load parquet
    df = pd.read_parquet(f'data/historical/{symbol}.parquet')

    # Calculate RSI(14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_valid = rsi.dropna()

    # Statistics
    stats = {
        'min': float(rsi_valid.min()),
        'max': float(rsi_valid.max()),
        'mean': float(rsi_valid.mean()),
        'median': float(rsi_valid.median()),
        'std': float(rsi_valid.std()),
        'q25': float(rsi_valid.quantile(0.25)),
        'q75': float(rsi_valid.quantile(0.75)),
    }

    # Threshold analysis
    oversold_35 = (rsi_valid <= 35).sum()
    overbought_65 = (rsi_valid >= 65).sum()
    oversold_30 = (rsi_valid <= 30).sum()
    overbought_70 = (rsi_valid >= 70).sum()

    # Crossings
    cross_35_down = ((rsi_valid.shift(1) > 35) & (rsi_valid <= 35)).sum()
    cross_65_up = ((rsi_valid.shift(1) < 65) & (rsi_valid >= 65)).sum()
    cross_30_down = ((rsi_valid.shift(1) > 30) & (rsi_valid <= 30)).sum()
    cross_70_up = ((rsi_valid.shift(1) < 70) & (rsi_valid >= 70)).sum()

    results[symbol] = {
        'bars': len(rsi_valid),
        'rsi_stats': stats,
        'current_params_35_65': {
            'oversold_bars': int(oversold_35),
            'overbought_bars': int(overbought_65),
            'oversold_crossings': int(cross_35_down),
            'overbought_crossings': int(cross_65_up),
            'total_signals': int(cross_35_down + cross_65_up)
        },
        'industry_params_30_70': {
            'oversold_bars': int(oversold_30),
            'overbought_bars': int(overbought_70),
            'oversold_crossings': int(cross_30_down),
            'overbought_crossings': int(cross_70_up),
            'total_signals': int(cross_30_down + cross_70_up)
        }
    }

    print(f"{'='*60}")
    print(f"{symbol} - RSI(14) Analysis ({len(rsi_valid)} bars)")
    print(f"{'='*60}")
    print(f"\nRSI Statistics:")
    print(f"  Min:    {stats['min']:6.2f}")
    print(f"  25%:    {stats['q25']:6.2f}")
    print(f"  Mean:   {stats['mean']:6.2f}")
    print(f"  Median: {stats['median']:6.2f}")
    print(f"  75%:    {stats['q75']:6.2f}")
    print(f"  Max:    {stats['max']:6.2f}")
    print(f"  StdDev: {stats['std']:6.2f}")

    print(f"\nCurrent Parameters (35/65):")
    print(f"  Bars RSI ≤ 35:          {oversold_35:3d} ({oversold_35/len(rsi_valid)*100:5.1f}%)")
    print(f"  Bars RSI ≥ 65:          {overbought_65:3d} ({overbought_65/len(rsi_valid)*100:5.1f}%)")
    print(f"  Oversold crossings:     {cross_35_down:3d}")
    print(f"  Overbought crossings:   {cross_65_up:3d}")
    print(f"  TOTAL SIGNALS:          {cross_35_down + cross_65_up:3d}")

    print(f"\nIndustry Standard (30/70):")
    print(f"  Bars RSI ≤ 30:          {oversold_30:3d} ({oversold_30/len(rsi_valid)*100:5.1f}%)")
    print(f"  Bars RSI ≥ 70:          {overbought_70:3d} ({overbought_70/len(rsi_valid)*100:5.1f}%)")
    print(f"  Oversold crossings:     {cross_30_down:3d}")
    print(f"  Overbought crossings:   {cross_70_up:3d}")
    print(f"  TOTAL SIGNALS:          {cross_30_down + cross_70_up:3d}")
    print()

# Save results
with open('analysis/rsi_quick_analysis.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*60}")
print("DIAGNOSIS & RECOMMENDATIONS")
print(f"{'='*60}\n")

total_signals_35_65 = sum(r['current_params_35_65']['total_signals'] for r in results.values())
total_signals_30_70 = sum(r['industry_params_30_70']['total_signals'] for r in results.values())
avg_rsi = np.mean([r['rsi_stats']['mean'] for r in results.values()])

print(f"Root Cause Analysis:")
print(f"  • Total signals with current params (35/65): {total_signals_35_65}")
print(f"  • Total signals with industry params (30/70): {total_signals_30_70}")
print(f"  • Average RSI across all symbols: {avg_rsi:.2f}")
print()

if total_signals_35_65 == 0:
    print("❌ CRITICAL: Current parameters generate ZERO signals!")
    print("   RSI thresholds (35/65) are too tight for this market data.")
    print()

if avg_rsi > 55:
    print("📈 Market Condition: Bullish bias (elevated RSI)")
    print("   RSI staying above 50 indicates strong uptrend")
    print()

print("Recommendations:")
print("  1. Switch to industry standard thresholds: 30/70")
print(f"     This would generate ~{total_signals_30_70} signals across all symbols")
print()
print("  2. Consider strategy appropriateness:")
print("     RSI mean-reversion may not suit strong trending markets")
print()
print("  3. Alternative approaches:")
print("     - Use momentum-following instead of mean-reversion")
print("     - Add trend filter before RSI signals")
print("     - Consider asymmetric thresholds (e.g., 25/75)")
print()

print(f"Analysis saved to: analysis/rsi_quick_analysis.json")
print("="*60)

EOF

deactivate
