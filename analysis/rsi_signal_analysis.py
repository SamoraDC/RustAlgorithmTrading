"""
RSI Signal Analysis for SimpleMomentumStrategy

Comprehensive analysis of why zero signals are being generated.
Analyzes RSI values, threshold crossings, and optimal parameters.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Tuple
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategies.simple_momentum import SimpleMomentumStrategy


class RSISignalAnalyzer:
    """Analyzes RSI signals and threshold crossings"""

    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = Path(data_dir)
        self.symbols = ["AAPL", "MSFT", "GOOGL"]
        self.data_cache = {}

    def load_data(self) -> Dict[str, pd.DataFrame]:
        """Load parquet files for all symbols"""
        print("\n" + "="*80)
        print("LOADING HISTORICAL DATA")
        print("="*80)

        for symbol in self.symbols:
            filepath = self.data_dir / f"{symbol}.parquet"
            if filepath.exists():
                df = pd.read_parquet(filepath)
                # Ensure datetime index
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                elif not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

                self.data_cache[symbol] = df
                print(f"\n{symbol}: Loaded {len(df)} bars")
                print(f"  Date range: {df.index[0]} to {df.index[-1]}")
                print(f"  Columns: {list(df.columns)}")
            else:
                print(f"\n❌ {symbol}: File not found at {filepath}")

        return self.data_cache

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def analyze_rsi_statistics(self) -> Dict[str, Dict]:
        """Calculate comprehensive RSI statistics for each symbol"""
        print("\n" + "="*80)
        print("RSI STATISTICAL ANALYSIS (Period=14)")
        print("="*80)

        results = {}

        for symbol, df in self.data_cache.items():
            # Calculate RSI
            rsi = self.calculate_rsi(df['close'], period=14)

            # Remove NaN values
            rsi_valid = rsi.dropna()

            stats = {
                'min': float(rsi_valid.min()),
                'max': float(rsi_valid.max()),
                'mean': float(rsi_valid.mean()),
                'median': float(rsi_valid.median()),
                'std': float(rsi_valid.std()),
                'q25': float(rsi_valid.quantile(0.25)),
                'q75': float(rsi_valid.quantile(0.75)),
                'total_bars': len(rsi_valid)
            }

            results[symbol] = stats

            print(f"\n{symbol} RSI Statistics:")
            print(f"  Min:    {stats['min']:.2f}")
            print(f"  25%:    {stats['q25']:.2f}")
            print(f"  Mean:   {stats['mean']:.2f}")
            print(f"  Median: {stats['median']:.2f}")
            print(f"  75%:    {stats['q75']:.2f}")
            print(f"  Max:    {stats['max']:.2f}")
            print(f"  Std:    {stats['std']:.2f}")
            print(f"  Bars:   {stats['total_bars']}")

        return results

    def count_threshold_crossings(
        self,
        oversold: float = 35,
        overbought: float = 65
    ) -> Dict[str, Dict]:
        """Count how many times RSI crosses thresholds"""
        print("\n" + "="*80)
        print(f"THRESHOLD CROSSING ANALYSIS (Oversold={oversold}, Overbought={overbought})")
        print("="*80)

        results = {}

        for symbol, df in self.data_cache.items():
            rsi = self.calculate_rsi(df['close'], period=14)
            rsi_valid = rsi.dropna()

            # Count occurrences below/above thresholds
            oversold_count = (rsi_valid <= oversold).sum()
            overbought_count = (rsi_valid >= overbought).sum()

            # Count actual crossings (transitions)
            oversold_crossings = ((rsi_valid.shift(1) > oversold) & (rsi_valid <= oversold)).sum()
            overbought_crossings = ((rsi_valid.shift(1) < overbought) & (rsi_valid >= overbought)).sum()

            # Percentage of time in each zone
            pct_oversold = (oversold_count / len(rsi_valid)) * 100
            pct_overbought = (overbought_count / len(rsi_valid)) * 100
            pct_neutral = ((rsi_valid > oversold) & (rsi_valid < overbought)).sum() / len(rsi_valid) * 100

            results[symbol] = {
                'oversold_bars': int(oversold_count),
                'overbought_bars': int(overbought_count),
                'oversold_crossings': int(oversold_crossings),
                'overbought_crossings': int(overbought_crossings),
                'pct_oversold': float(pct_oversold),
                'pct_overbought': float(pct_overbought),
                'pct_neutral': float(pct_neutral)
            }

            print(f"\n{symbol} Threshold Analysis:")
            print(f"  Oversold bars (RSI ≤ {oversold}):    {oversold_count:4d} ({pct_oversold:5.2f}%)")
            print(f"  Overbought bars (RSI ≥ {overbought}): {overbought_count:4d} ({pct_overbought:5.2f}%)")
            print(f"  Neutral bars:                {int(pct_neutral * len(rsi_valid) / 100):4d} ({pct_neutral:5.2f}%)")
            print(f"  Oversold crossings:          {oversold_crossings:4d}")
            print(f"  Overbought crossings:        {overbought_crossings:4d}")

        return results

    def find_optimal_thresholds(
        self,
        target_signals: int = 7,
        min_oversold: float = 20,
        max_oversold: float = 45,
        min_overbought: float = 55,
        max_overbought: float = 80
    ) -> Dict[str, Tuple[float, float]]:
        """Find optimal RSI thresholds to generate target number of signals"""
        print("\n" + "="*80)
        print(f"OPTIMAL THRESHOLD SEARCH (Target: ~{target_signals} signals per symbol)")
        print("="*80)

        results = {}

        for symbol, df in self.data_cache.items():
            rsi = self.calculate_rsi(df['close'], period=14)
            rsi_valid = rsi.dropna()

            best_oversold = 30
            best_overbought = 70
            best_diff = float('inf')

            # Grid search for optimal thresholds
            for oversold in range(int(min_oversold), int(max_oversold) + 1):
                for overbought in range(int(min_overbought), int(max_overbought) + 1):
                    # Count crossings with these thresholds
                    oversold_cross = ((rsi_valid.shift(1) > oversold) & (rsi_valid <= oversold)).sum()
                    overbought_cross = ((rsi_valid.shift(1) < overbought) & (rsi_valid >= overbought)).sum()

                    total_signals = oversold_cross + overbought_cross
                    diff = abs(total_signals - target_signals)

                    if diff < best_diff:
                        best_diff = diff
                        best_oversold = oversold
                        best_overbought = overbought

            # Calculate actual signals with best thresholds
            oversold_cross = ((rsi_valid.shift(1) > best_oversold) & (rsi_valid <= best_oversold)).sum()
            overbought_cross = ((rsi_valid.shift(1) < best_overbought) & (rsi_valid >= best_overbought)).sum()
            total_signals = oversold_cross + overbought_cross

            results[symbol] = (best_oversold, best_overbought)

            print(f"\n{symbol} Optimal Thresholds:")
            print(f"  Oversold:  {best_oversold:.0f}")
            print(f"  Overbought: {best_overbought:.0f}")
            print(f"  Total signals: {total_signals}")
            print(f"    - Buy signals (oversold crossings):  {oversold_cross}")
            print(f"    - Sell signals (overbought crossings): {overbought_cross}")

        return results

    def test_strategy_signals(
        self,
        oversold: float = 35,
        overbought: float = 65
    ) -> Dict[str, List]:
        """Test actual signal generation with SimpleMomentumStrategy"""
        print("\n" + "="*80)
        print(f"STRATEGY SIGNAL GENERATION TEST")
        print(f"Parameters: RSI(14), Oversold={oversold}, Overbought={overbought}")
        print("="*80)

        strategy = SimpleMomentumStrategy(
            symbols=self.symbols,
            rsi_period=14,
            rsi_oversold=oversold,
            rsi_overbought=overbought
        )

        results = {}

        for symbol, df in self.data_cache.items():
            # Prepare data with required columns
            data = df.copy()
            if 'volume' not in data.columns:
                data['volume'] = 0  # Add dummy volume if missing

            # Generate signals
            signals = strategy.generate_signals_for_symbol(symbol, data)

            results[symbol] = signals

            print(f"\n{symbol} Signals Generated: {len(signals)}")
            if signals:
                for i, sig in enumerate(signals[:5], 1):  # Show first 5
                    print(f"  {i}. {sig.signal_type.upper()} @ ${sig.price:.2f} on {sig.timestamp}")
                if len(signals) > 5:
                    print(f"  ... and {len(signals) - 5} more")
            else:
                print("  ❌ NO SIGNALS GENERATED")

        return results

    def diagnose_zero_signals(self) -> Dict[str, str]:
        """Diagnose why zero signals are being generated"""
        print("\n" + "="*80)
        print("ZERO SIGNAL DIAGNOSIS")
        print("="*80)

        diagnoses = {}

        for symbol, df in self.data_cache.items():
            rsi = self.calculate_rsi(df['close'], period=14)
            rsi_valid = rsi.dropna()

            reasons = []

            # Check 1: RSI never reaches thresholds
            if rsi_valid.min() > 35:
                reasons.append(f"RSI minimum ({rsi_valid.min():.2f}) never reaches oversold threshold (35)")
            if rsi_valid.max() < 65:
                reasons.append(f"RSI maximum ({rsi_valid.max():.2f}) never reaches overbought threshold (65)")

            # Check 2: Check if RSI is stuck in neutral zone
            neutral_pct = ((rsi_valid > 35) & (rsi_valid < 65)).sum() / len(rsi_valid) * 100
            if neutral_pct > 90:
                reasons.append(f"RSI in neutral zone {neutral_pct:.1f}% of the time (very low volatility)")

            # Check 3: Market trend analysis
            price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
            if price_change > 20:
                reasons.append(f"Strong uptrend ({price_change:.1f}% gain) - RSI likely elevated")
            elif price_change < -20:
                reasons.append(f"Strong downtrend ({price_change:.1f}% loss) - RSI likely depressed")

            diagnoses[symbol] = reasons

            print(f"\n{symbol} Diagnosis:")
            if reasons:
                for reason in reasons:
                    print(f"  • {reason}")
            else:
                print(f"  ✓ No obvious issues detected")

        return diagnoses

    def generate_report(self, output_file: str = "analysis/rsi_analysis_report.json"):
        """Generate comprehensive analysis report"""
        print("\n" + "="*80)
        print("GENERATING COMPREHENSIVE REPORT")
        print("="*80)

        # Run all analyses
        rsi_stats = self.analyze_rsi_statistics()
        current_crossings = self.count_threshold_crossings(oversold=35, overbought=65)
        standard_crossings = self.count_threshold_crossings(oversold=30, overbought=70)
        optimal_thresholds = self.find_optimal_thresholds(target_signals=7)
        diagnoses = self.diagnose_zero_signals()

        # Test with current and optimal parameters
        current_signals = self.test_strategy_signals(oversold=35, overbought=65)

        # Compile report
        report = {
            'analysis_date': pd.Timestamp.now().isoformat(),
            'symbols_analyzed': self.symbols,
            'total_bars_per_symbol': {s: len(self.data_cache[s]) for s in self.symbols},
            'rsi_statistics': rsi_stats,
            'current_parameters': {
                'rsi_period': 14,
                'oversold': 35,
                'overbought': 65,
                'crossings': current_crossings
            },
            'industry_standard_parameters': {
                'rsi_period': 14,
                'oversold': 30,
                'overbought': 70,
                'crossings': standard_crossings
            },
            'optimal_thresholds': {
                symbol: {'oversold': int(thresholds[0]), 'overbought': int(thresholds[1])}
                for symbol, thresholds in optimal_thresholds.items()
            },
            'signal_counts': {
                symbol: len(signals) for symbol, signals in current_signals.items()
            },
            'diagnoses': diagnoses,
            'recommendations': self._generate_recommendations(
                rsi_stats, current_crossings, optimal_thresholds
            )
        }

        # Save report
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Report saved to: {output_path}")

        return report

    def _generate_recommendations(
        self,
        rsi_stats: Dict,
        current_crossings: Dict,
        optimal_thresholds: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Check if any signals were generated with current params
        total_crossings = sum(
            c['oversold_crossings'] + c['overbought_crossings']
            for c in current_crossings.values()
        )

        if total_crossings == 0:
            recommendations.append(
                "CRITICAL: Current parameters (35/65) generate ZERO signals across all symbols"
            )
            recommendations.append(
                "Adjust RSI thresholds to capture actual market conditions"
            )

        # Analyze if market is trending
        avg_rsi = np.mean([s['mean'] for s in rsi_stats.values()])
        if avg_rsi > 60:
            recommendations.append(
                f"Market showing bullish bias (avg RSI={avg_rsi:.1f}). "
                "Consider asymmetric thresholds or trend-following approach"
            )
        elif avg_rsi < 40:
            recommendations.append(
                f"Market showing bearish bias (avg RSI={avg_rsi:.1f}). "
                "Consider defensive thresholds or wait for reversal"
            )

        # Recommend optimal thresholds
        recommendations.append(
            "Suggested optimal thresholds for 5-10 signals per symbol:"
        )
        for symbol, (oversold, overbought) in optimal_thresholds.items():
            recommendations.append(
                f"  {symbol}: Oversold={oversold:.0f}, Overbought={overbought:.0f}"
            )

        # Strategy type recommendation
        if avg_rsi > 55:
            recommendations.append(
                "Consider momentum-following strategy instead of mean-reversion "
                "given elevated RSI levels"
            )

        return recommendations


def main():
    """Main analysis execution"""
    analyzer = RSISignalAnalyzer()

    # Load data
    analyzer.load_data()

    # Generate comprehensive report
    report = analyzer.generate_report()

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80)

    for rec in report['recommendations']:
        print(f"\n• {rec}")

    print("\n" + "="*80)
    print("Analysis complete! Check analysis/rsi_analysis_report.json for full details")
    print("="*80)

    return report


if __name__ == "__main__":
    main()
