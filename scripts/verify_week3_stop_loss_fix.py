#!/usr/bin/env python3
"""
WEEK 3 VERIFICATION: Analyze backtest data to confirm stop-loss bypass fix

This script analyzes existing backtest results to verify that:
1. Stop-losses exit immediately (bars_held < 10)
2. Take-profits enforce holding period (bars_held >= 10)
3. Average stop-loss improved from -5.49% to -2.0%
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import statistics


def load_backtest_results(result_file: Path) -> Dict[str, Any]:
    """Load backtest results JSON"""
    with open(result_file, 'r') as f:
        return json.load(f)


def analyze_exit_patterns(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze exit patterns to verify Week 3 fix

    Returns:
        Dict with analysis results:
        - stop_loss_stats: Stats for stop-loss exits
        - take_profit_stats: Stats for take-profit exits
        - trailing_stop_stats: Stats for trailing stop exits
        - technical_exit_stats: Stats for technical exits
    """
    trades = results.get('trades', [])

    if not trades:
        return {
            'error': 'No trades found in backtest results',
            'total_trades': 0
        }

    # Categorize exits
    stop_loss_exits = []
    take_profit_exits = []
    trailing_stop_exits = []
    technical_exits = []
    catastrophic_exits = []

    for trade in trades:
        if not isinstance(trade, dict):
            continue

        exit_reason = trade.get('exit_reason', 'unknown')
        pnl_pct = trade.get('pnl_pct', 0.0)
        bars_held = trade.get('bars_held', 0)

        trade_data = {
            'pnl_pct': pnl_pct,
            'bars_held': bars_held,
            'exit_reason': exit_reason,
            'symbol': trade.get('symbol', 'UNKNOWN'),
            'timestamp': trade.get('exit_time', 'unknown')
        }

        if exit_reason == 'stop_loss':
            stop_loss_exits.append(trade_data)
        elif exit_reason == 'take_profit':
            take_profit_exits.append(trade_data)
        elif exit_reason == 'trailing_stop_loss':
            trailing_stop_exits.append(trade_data)
        elif exit_reason == 'catastrophic_stop_loss':
            catastrophic_exits.append(trade_data)
        elif exit_reason in ['technical_reversal', 'technical']:
            technical_exits.append(trade_data)

    def calc_stats(exits: List[Dict], exit_type: str) -> Dict:
        """Calculate statistics for exit type"""
        if not exits:
            return {
                'count': 0,
                'avg_pnl': 0.0,
                'avg_bars_held': 0.0,
                'min_bars': 0,
                'max_bars': 0,
                'bypassed_holding_period': 0,
                'enforced_holding_period': 0
            }

        pnls = [e['pnl_pct'] for e in exits]
        bars = [e['bars_held'] for e in exits]

        bypassed = sum(1 for b in bars if b < 10)
        enforced = sum(1 for b in bars if b >= 10)

        return {
            'count': len(exits),
            'avg_pnl': statistics.mean(pnls) * 100,  # Convert to percentage
            'median_pnl': statistics.median(pnls) * 100,
            'min_pnl': min(pnls) * 100,
            'max_pnl': max(pnls) * 100,
            'avg_bars_held': statistics.mean(bars),
            'median_bars_held': statistics.median(bars),
            'min_bars': min(bars),
            'max_bars': max(bars),
            'bypassed_holding_period': bypassed,
            'bypassed_pct': (bypassed / len(exits)) * 100 if exits else 0,
            'enforced_holding_period': enforced,
            'enforced_pct': (enforced / len(exits)) * 100 if exits else 0,
            'examples': exits[:3]  # First 3 examples
        }

    analysis = {
        'total_trades': len(trades),
        'stop_loss': calc_stats(stop_loss_exits, 'stop_loss'),
        'take_profit': calc_stats(take_profit_exits, 'take_profit'),
        'trailing_stop': calc_stats(trailing_stop_exits, 'trailing_stop'),
        'catastrophic': calc_stats(catastrophic_exits, 'catastrophic'),
        'technical': calc_stats(technical_exits, 'technical')
    }

    return analysis


def print_verification_report(analysis: Dict[str, Any], result_file: str):
    """Print formatted verification report"""
    print("\n" + "="*80)
    print("WEEK 3 VERIFICATION REPORT: Stop-Loss Bypass Fix")
    print("="*80)
    print(f"\nBacktest File: {result_file}")
    print(f"Total Trades: {analysis.get('total_trades', 0)}")

    # CRITICAL TEST 1: Stop-Loss Exits
    print("\n" + "-"*80)
    print("1. STOP-LOSS EXITS (Should bypass holding period)")
    print("-"*80)
    sl_stats = analysis.get('stop_loss', {})
    sl_count = sl_stats.get('count', 0)

    if sl_count > 0:
        print(f"   Count: {sl_count} trades")
        print(f"   Average P&L: {sl_stats['avg_pnl']:.2f}%")
        print(f"   Median P&L: {sl_stats['median_pnl']:.2f}%")
        print(f"   Range: {sl_stats['min_pnl']:.2f}% to {sl_stats['max_pnl']:.2f}%")
        print(f"\n   Average Bars Held: {sl_stats['avg_bars_held']:.1f}")
        print(f"   Median Bars Held: {sl_stats['median_bars_held']:.0f}")
        print(f"   Range: {sl_stats['min_bars']} to {sl_stats['max_bars']} bars")
        print(f"\n   ⚡ IMMEDIATE EXITS (< 10 bars): {sl_stats['bypassed_holding_period']} "
              f"({sl_stats['bypassed_pct']:.1f}%)")
        print(f"   ⏳ DELAYED EXITS (>= 10 bars): {sl_stats['enforced_holding_period']} "
              f"({sl_stats['enforced_pct']:.1f}%)")

        # Verification
        if sl_stats['avg_pnl'] > -2.5 and sl_stats['avg_pnl'] < -1.8:
            print(f"\n   ✅ PASS: Average loss {sl_stats['avg_pnl']:.2f}% is within expected range "
                  f"(-2.5% to -1.8%)")
        else:
            print(f"\n   ⚠️ WARNING: Average loss {sl_stats['avg_pnl']:.2f}% outside expected range")

        if sl_stats['bypassed_pct'] > 50:
            print(f"   ✅ PASS: {sl_stats['bypassed_pct']:.1f}% of stop-losses bypass holding period")
        else:
            print(f"   ⚠️ WARNING: Only {sl_stats['bypassed_pct']:.1f}% bypass holding period "
                  f"(expected >50%)")
    else:
        print("   ℹ️ No stop-loss exits found in backtest")

    # CRITICAL TEST 2: Take-Profit Exits
    print("\n" + "-"*80)
    print("2. TAKE-PROFIT EXITS (Should enforce holding period)")
    print("-"*80)
    tp_stats = analysis.get('take_profit', {})
    tp_count = tp_stats.get('count', 0)

    if tp_count > 0:
        print(f"   Count: {tp_count} trades")
        print(f"   Average P&L: {tp_stats['avg_pnl']:.2f}%")
        print(f"   Median P&L: {tp_stats['median_pnl']:.2f}%")
        print(f"\n   Average Bars Held: {tp_stats['avg_bars_held']:.1f}")
        print(f"   Median Bars Held: {tp_stats['median_bars_held']:.0f}")
        print(f"   Range: {tp_stats['min_bars']} to {tp_stats['max_bars']} bars")
        print(f"\n   ⚡ IMMEDIATE EXITS (< 10 bars): {tp_stats['bypassed_holding_period']} "
              f"({tp_stats['bypassed_pct']:.1f}%)")
        print(f"   ⏳ DELAYED EXITS (>= 10 bars): {tp_stats['enforced_holding_period']} "
              f"({tp_stats['enforced_pct']:.1f}%)")

        # Verification
        if tp_stats['enforced_pct'] > 80:
            print(f"\n   ✅ PASS: {tp_stats['enforced_pct']:.1f}% of take-profits enforce "
                  f"holding period (expected >80%)")
        else:
            print(f"\n   ⚠️ WARNING: Only {tp_stats['enforced_pct']:.1f}% enforce holding period")
    else:
        print("   ℹ️ No take-profit exits found in backtest")

    # CRITICAL TEST 3: Trailing Stop Exits
    print("\n" + "-"*80)
    print("3. TRAILING STOP EXITS (Should bypass holding period)")
    print("-"*80)
    ts_stats = analysis.get('trailing_stop', {})
    ts_count = ts_stats.get('count', 0)

    if ts_count > 0:
        print(f"   Count: {ts_count} trades")
        print(f"   Average P&L: {ts_stats['avg_pnl']:.2f}%")
        print(f"   Average Bars Held: {ts_stats['avg_bars_held']:.1f}")
        print(f"\n   ⚡ IMMEDIATE EXITS (< 10 bars): {ts_stats['bypassed_holding_period']} "
              f"({ts_stats['bypassed_pct']:.1f}%)")

        if ts_stats['bypassed_pct'] > 30:
            print(f"\n   ✅ PASS: {ts_stats['bypassed_pct']:.1f}% bypass holding period")
        else:
            print(f"\n   ⚠️ INFO: {ts_stats['bypassed_pct']:.1f}% bypass holding period")
    else:
        print("   ℹ️ No trailing stop exits found in backtest")

    # Catastrophic Exits
    cat_stats = analysis.get('catastrophic', {})
    if cat_stats.get('count', 0) > 0:
        print("\n" + "-"*80)
        print("4. CATASTROPHIC EXITS (< -5%)")
        print("-"*80)
        print(f"   Count: {cat_stats['count']} trades")
        print(f"   Average P&L: {cat_stats['avg_pnl']:.2f}%")
        print(f"   Average Bars Held: {cat_stats['avg_bars_held']:.1f}")
        print(f"\n   ⚡ All catastrophic exits bypass holding period (risk management)")

    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)

    all_pass = True

    # Check 1: Stop-loss average
    if sl_count > 0:
        if -2.5 <= sl_stats['avg_pnl'] <= -1.8:
            print("✅ Stop-loss average P&L within expected range")
        else:
            print(f"⚠️ Stop-loss average P&L {sl_stats['avg_pnl']:.2f}% outside expected range")
            all_pass = False

        if sl_stats['bypassed_pct'] > 50:
            print("✅ Stop-losses bypass holding period correctly")
        else:
            print(f"⚠️ Only {sl_stats['bypassed_pct']:.1f}% of stop-losses bypass holding period")
            all_pass = False

    # Check 2: Take-profit holding
    if tp_count > 0:
        if tp_stats['enforced_pct'] > 80:
            print("✅ Take-profits enforce holding period correctly")
        else:
            print(f"⚠️ Only {tp_stats['enforced_pct']:.1f}% of take-profits enforce holding period")
            all_pass = False

    if all_pass and (sl_count > 0 or tp_count > 0):
        print("\n✅ WEEK 3 FIX VERIFIED: Asymmetric holding period logic working correctly")
    elif sl_count == 0 and tp_count == 0:
        print("\nℹ️ Insufficient data to verify (no stop-loss or take-profit exits)")
    else:
        print("\n⚠️ WEEK 3 FIX NEEDS REVIEW: Some checks failed")

    print("="*80 + "\n")


def main():
    """Main verification script"""
    # Find most recent backtest result
    results_dir = Path("data/backtest_results")

    if not results_dir.exists():
        print(f"❌ Error: Backtest results directory not found: {results_dir}")
        return 1

    # Get all JSON files
    json_files = list(results_dir.glob("*.json"))

    if not json_files:
        print(f"❌ Error: No backtest result files found in {results_dir}")
        return 1

    # Use most recent file or specific file if provided
    if len(sys.argv) > 1:
        result_file = Path(sys.argv[1])
    else:
        result_file = max(json_files, key=lambda p: p.stat().st_mtime)

    print(f"\n📊 Analyzing: {result_file.name}")

    try:
        results = load_backtest_results(result_file)
        analysis = analyze_exit_patterns(results)

        if 'error' in analysis:
            print(f"\n❌ Error: {analysis['error']}")
            return 1

        print_verification_report(analysis, result_file.name)

        return 0

    except Exception as e:
        print(f"\n❌ Error analyzing results: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
