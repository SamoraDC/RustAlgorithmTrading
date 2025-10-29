#!/usr/bin/env python3
"""
Analyze backtest results to identify patterns and failure modes
"""

import json
from pathlib import Path
from datetime import datetime
import statistics

def analyze_backtest_file(file_path):
    """Extract key metrics from a backtest file"""
    with open(file_path) as f:
        data = json.load(f)

    metrics = data.get('metrics', {})

    return {
        'file': file_path.name,
        'timestamp': data.get('timestamp', 'unknown'),
        'symbols': data.get('symbols', []),
        'initial_capital': data.get('initial_capital', 0),
        'final_value': data.get('final_value', 0),
        'total_return': metrics.get('total_return', data.get('total_return', 0)),
        'sharpe_ratio': metrics.get('sharpe_ratio', data.get('sharpe_ratio', 0)),
        'sortino_ratio': metrics.get('sortino_ratio', 0),
        'max_drawdown': metrics.get('max_drawdown', data.get('max_drawdown', 0)),
        'win_rate': metrics.get('win_rate', data.get('win_rate', 0)),
        'profit_factor': metrics.get('profit_factor', data.get('profit_factor', 0)),
        'total_trades': metrics.get('total_trades', 0),
        'winning_trades': metrics.get('winning_trades', 0),
        'losing_trades': metrics.get('losing_trades', 0),
        'average_win': metrics.get('average_win', 0),
        'average_loss': metrics.get('average_loss', 0),
        'largest_win': metrics.get('largest_win', 0),
        'largest_loss': metrics.get('largest_loss', 0),
        'volatility': metrics.get('volatility', 0),
        'strategy': data.get('strategy', 'unknown'),
    }

def main():
    backtest_dir = Path('data/backtest_results')
    results = []

    print("=" * 80)
    print("BACKTEST FAILURE ANALYSIS")
    print("=" * 80)
    print()

    # Load all backtest results
    for file in sorted(backtest_dir.glob('*.json')):
        try:
            result = analyze_backtest_file(file)
            results.append(result)
        except Exception as e:
            print(f"Error reading {file.name}: {e}")

    if not results:
        print("No backtest results found!")
        return

    print(f"Total backtests analyzed: {len(results)}")
    print()

    # Summary statistics
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    total_returns = [r['total_return'] for r in results]
    sharpe_ratios = [r['sharpe_ratio'] for r in results if r['sharpe_ratio'] != 0]
    win_rates = [r['win_rate'] for r in results]
    total_trades = sum(r['total_trades'] for r in results)
    winning_trades = sum(r['winning_trades'] for r in results)
    losing_trades = sum(r['losing_trades'] for r in results)

    print(f"Average Total Return: {statistics.mean(total_returns):.2%}")
    print(f"Median Total Return: {statistics.median(total_returns):.2%}")
    print(f"Best Return: {max(total_returns):.2%}")
    print(f"Worst Return: {min(total_returns):.2%}")
    print()

    print(f"Average Sharpe Ratio: {statistics.mean(sharpe_ratios) if sharpe_ratios else 0:.2f}")
    print(f"Median Sharpe Ratio: {statistics.median(sharpe_ratios) if sharpe_ratios else 0:.2f}")
    print()

    print(f"Average Win Rate: {statistics.mean(win_rates):.2%}")
    print(f"Median Win Rate: {statistics.median(win_rates):.2%}")
    print(f"Backtests with 0% win rate: {sum(1 for r in win_rates if r == 0)} / {len(results)}")
    print()

    print(f"Total Trades: {total_trades}")
    print(f"Total Winning Trades: {winning_trades} ({winning_trades/total_trades*100 if total_trades > 0 else 0:.1f}%)")
    print(f"Total Losing Trades: {losing_trades} ({losing_trades/total_trades*100 if total_trades > 0 else 0:.1f}%)")
    print()

    # Critical issue analysis
    print("=" * 80)
    print("CRITICAL ISSUES IDENTIFIED")
    print("=" * 80)

    # Issue 1: All trades losing
    zero_win_rate_tests = [r for r in results if r['win_rate'] == 0]
    print(f"\n1. ZERO WIN RATE BACKTESTS: {len(zero_win_rate_tests)} / {len(results)}")
    if zero_win_rate_tests:
        print("   Files with 0% win rate:")
        for r in zero_win_rate_tests[:5]:
            print(f"   - {r['file']}: {r['total_trades']} trades, {r['total_return']:.2%} return")

    # Issue 2: Negative Sharpe ratios
    negative_sharpe = [r for r in results if r['sharpe_ratio'] < 0]
    print(f"\n2. NEGATIVE SHARPE RATIOS: {len(negative_sharpe)} / {len(results)}")
    if negative_sharpe:
        avg_sharpe = statistics.mean([r['sharpe_ratio'] for r in negative_sharpe])
        print(f"   Average negative Sharpe: {avg_sharpe:.2f}")

    # Issue 3: Large drawdowns
    large_drawdown = [r for r in results if r['max_drawdown'] > 0.2]
    print(f"\n3. LARGE DRAWDOWNS (>20%): {len(large_drawdown)} / {len(results)}")
    if large_drawdown:
        avg_dd = statistics.mean([r['max_drawdown'] for r in large_drawdown])
        max_dd = max(r['max_drawdown'] for r in large_drawdown)
        print(f"   Average drawdown: {avg_dd:.2%}")
        print(f"   Maximum drawdown: {max_dd:.2%}")

    # Issue 4: Average loss analysis
    print(f"\n4. AVERAGE LOSS ANALYSIS:")
    avg_losses = [r['average_loss'] for r in results if r['average_loss'] != 0]
    if avg_losses:
        print(f"   Average loss across all tests: {statistics.mean(avg_losses):.2%}")
        print(f"   Median loss: {statistics.median(avg_losses):.2%}")
        print(f"   Worst average loss: {min(avg_losses):.2%}")

    # Issue 5: Strategy comparison
    print(f"\n5. STRATEGY COMPARISON:")
    strategies = {}
    for r in results:
        strategy = r['strategy']
        if strategy not in strategies:
            strategies[strategy] = []
        strategies[strategy].append(r)

    for strategy, tests in strategies.items():
        if tests:
            avg_return = statistics.mean([t['total_return'] for t in tests])
            avg_win_rate = statistics.mean([t['win_rate'] for t in tests])
            print(f"   {strategy}:")
            print(f"      Tests: {len(tests)}, Avg Return: {avg_return:.2%}, Avg Win Rate: {avg_win_rate:.2%}")

    # Detailed report on worst performers
    print("\n" + "=" * 80)
    print("WORST PERFORMING BACKTESTS (Bottom 5)")
    print("=" * 80)

    sorted_results = sorted(results, key=lambda x: x['total_return'])
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"\n{i}. {r['file']}")
        print(f"   Strategy: {r['strategy']}")
        print(f"   Symbols: {', '.join(r['symbols'])}")
        print(f"   Total Return: {r['total_return']:.2%}")
        print(f"   Sharpe Ratio: {r['sharpe_ratio']:.2f}")
        print(f"   Win Rate: {r['win_rate']:.2%}")
        print(f"   Trades: {r['total_trades']} (W:{r['winning_trades']}, L:{r['losing_trades']})")
        print(f"   Avg Loss: {r['average_loss']:.2%}")
        print(f"   Max Drawdown: {r['max_drawdown']:.2%}")

    # Best performers (for comparison)
    print("\n" + "=" * 80)
    print("BEST PERFORMING BACKTESTS (Top 5)")
    print("=" * 80)

    for i, r in enumerate(reversed(sorted_results[-5:]), 1):
        print(f"\n{i}. {r['file']}")
        print(f"   Strategy: {r['strategy']}")
        print(f"   Symbols: {', '.join(r['symbols'])}")
        print(f"   Total Return: {r['total_return']:.2%}")
        print(f"   Sharpe Ratio: {r['sharpe_ratio']:.2f}")
        print(f"   Win Rate: {r['win_rate']:.2%}")
        print(f"   Trades: {r['total_trades']} (W:{r['winning_trades']}, L:{r['losing_trades']})")
        print(f"   Avg Win: {r['average_win']:.2%}, Avg Loss: {r['average_loss']:.2%}")
        print(f"   Max Drawdown: {r['max_drawdown']:.2%}")

    # Root cause analysis
    print("\n" + "=" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 80)

    print("\n🔍 Key Findings:")
    print(f"   1. Win rate crisis: {sum(1 for r in win_rates if r == 0)}/{len(results)} backtests have ZERO winning trades")
    print(f"   2. Negative Sharpe ratios: {len(negative_sharpe)}/{len(results)} tests have negative risk-adjusted returns")
    print(f"   3. Overall win rate: {winning_trades}/{total_trades} = {winning_trades/total_trades*100 if total_trades > 0 else 0:.1f}%")

    print("\n⚠️  Suspected Issues:")
    print("   A. Entry/Exit Logic: Signals may be inverted or poorly timed")
    print("   B. Stop-Loss Triggering: Stop losses may be too tight, triggering prematurely")
    print("   C. Minimum Holding Period: Early exits preventing profitable trades")
    print("   D. Data Quality: Prices/timestamps may be incorrect or misaligned")
    print("   E. Commission/Slippage: Transaction costs eating all profits")
    print("   F. Position Sizing: May be over-leveraging or under-sizing")

    print("\n📊 Recommendations:")
    print("   1. Review signal generation logic in momentum.py")
    print("   2. Check data quality and price alignment")
    print("   3. Validate stop-loss and take-profit levels")
    print("   4. Test with longer holding periods")
    print("   5. Reduce transaction frequency")
    print("   6. Compare signals vs actual price movements")

if __name__ == '__main__':
    main()
