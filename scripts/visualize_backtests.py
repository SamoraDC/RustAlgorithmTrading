#!/usr/bin/env python3
"""
Create ASCII visualizations of backtest equity curves and drawdowns
"""

import json
from pathlib import Path

def create_ascii_chart(values, width=80, height=20, title=""):
    """Create ASCII chart from values"""
    if not values:
        return "No data to plot"

    min_val = min(values)
    max_val = max(values)
    value_range = max_val - min_val if max_val != min_val else 1

    # Normalize values to chart height
    normalized = [(v - min_val) / value_range * (height - 1) for v in values]

    # Create empty chart
    chart = [[' ' for _ in range(width)] for _ in range(height)]

    # Sample values to fit width
    step = max(1, len(values) // width)
    sampled_values = [normalized[i] for i in range(0, len(values), step)][:width]

    # Plot line
    for x, y in enumerate(sampled_values):
        y_pos = int(height - 1 - y)
        if 0 <= y_pos < height:
            chart[y_pos][x] = '█'

    # Add title
    result = [title]
    result.append('=' * width)

    # Add y-axis labels and chart
    for i, row in enumerate(chart):
        y_val = max_val - (i / (height - 1)) * value_range
        label = f"{y_val:>8.2f} |"
        result.append(label + ''.join(row))

    # Add x-axis
    result.append(' ' * 10 + '-' * width)
    result.append(' ' * 10 + f"Time (0 to {len(values)} bars)")

    return '\n'.join(result)

def analyze_single_backtest(file_path):
    """Analyze and visualize a single backtest"""
    with open(file_path) as f:
        data = json.load(f)

    print("\n" + "=" * 100)
    print(f"BACKTEST: {file_path.name}")
    print("=" * 100)

    # Basic info
    metrics = data.get('metrics', {})
    print(f"\nStrategy: {data.get('strategy', 'unknown')}")
    print(f"Symbols: {', '.join(data.get('symbols', []))}")
    print(f"Period: {data.get('start_date', 'N/A')} to {data.get('end_date', 'N/A')}")
    print(f"\nInitial Capital: ${data.get('initial_capital', 0):,.2f}")
    print(f"Final Value: ${data.get('final_value', 0):,.2f}")
    print(f"Total Return: {metrics.get('total_return', 0):.2%}")
    print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
    print(f"\nTotal Trades: {metrics.get('total_trades', 0)}")
    print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
    print(f"Winning Trades: {metrics.get('winning_trades', 0)}")
    print(f"Losing Trades: {metrics.get('losing_trades', 0)}")
    print(f"Average Win: {metrics.get('average_win', 0):.2%}")
    print(f"Average Loss: {metrics.get('average_loss', 0):.2%}")

    # Check for signals
    signals = data.get('signals', [])
    if signals:
        print(f"\n{'=' * 100}")
        print(f"SIGNALS ANALYSIS ({len(signals)} total)")
        print('=' * 100)

        # Count signal types
        signal_counts = {}
        for sig in signals:
            sig_type = sig.get('signal_type', 'UNKNOWN')
            signal_counts[sig_type] = signal_counts.get(sig_type, 0) + 1

        print("\nSignal Distribution:")
        for sig_type, count in sorted(signal_counts.items()):
            print(f"  {sig_type}: {count}")

        # Show first 10 signals
        print("\nFirst 10 Signals:")
        print(f"{'#':<4} {'Type':<6} {'Symbol':<8} {'Price':<10} {'Confidence':<12} {'Metadata'}")
        print('-' * 100)
        for i, sig in enumerate(signals[:10], 1):
            sig_type = sig.get('signal_type', 'N/A')
            symbol = sig.get('symbol', 'N/A')
            price = sig.get('price', 0)
            confidence = sig.get('confidence', 0)
            metadata = sig.get('metadata', {})

            # Format metadata
            if sig_type == 'EXIT':
                meta_str = f"Reason: {metadata.get('exit_reason', 'N/A')}, P&L: {metadata.get('pnl_pct', 0):.2%}"
            else:
                meta_str = f"RSI: {metadata.get('rsi', 0):.1f}, MACD_hist: {metadata.get('macd_histogram', 0):.5f}"

            print(f"{i:<4} {sig_type:<6} {symbol:<8} ${price:<9.2f} {confidence:<12.2f} {meta_str}")

        # Trade analysis - match entry/exit pairs
        print("\n" + "=" * 100)
        print("TRADE ANALYSIS (Entry/Exit Pairs)")
        print("=" * 100)

        trades = []
        open_positions = {}

        for sig in signals:
            symbol = sig.get('symbol')
            sig_type = sig.get('signal_type')

            if sig_type in ['LONG', 'SHORT']:
                # Entry signal
                open_positions[symbol] = sig
            elif sig_type == 'EXIT' and symbol in open_positions:
                # Exit signal - create trade
                entry = open_positions[symbol]
                exit_sig = sig

                trade = {
                    'symbol': symbol,
                    'entry_type': entry.get('signal_type'),
                    'entry_price': entry.get('price'),
                    'exit_price': exit_sig.get('price'),
                    'pnl_pct': exit_sig.get('metadata', {}).get('pnl_pct', 0),
                    'exit_reason': exit_sig.get('metadata', {}).get('exit_reason', 'N/A'),
                    'bars_held': exit_sig.get('metadata', {}).get('bars_held', 0),
                }
                trades.append(trade)
                del open_positions[symbol]

        if trades:
            print(f"\nCompleted Trades: {len(trades)}")
            print(f"{'#':<4} {'Symbol':<8} {'Type':<6} {'Entry':<10} {'Exit':<10} {'P&L':<10} {'Bars':<6} {'Exit Reason'}")
            print('-' * 100)

            for i, trade in enumerate(trades[:15], 1):  # Show first 15 trades
                pnl_indicator = '✓' if trade['pnl_pct'] > 0 else '✗'
                print(
                    f"{i:<4} {trade['symbol']:<8} {trade['entry_type']:<6} "
                    f"${trade['entry_price']:<9.2f} ${trade['exit_price']:<9.2f} "
                    f"{pnl_indicator} {trade['pnl_pct']:>7.2%} {trade['bars_held']:<6} "
                    f"{trade['exit_reason']}"
                )

            # Summary
            winners = [t for t in trades if t['pnl_pct'] > 0]
            losers = [t for t in trades if t['pnl_pct'] <= 0]

            print(f"\nTrade Summary:")
            print(f"  Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)")
            print(f"  Losers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)")

            if winners:
                avg_win = sum(t['pnl_pct'] for t in winners) / len(winners)
                print(f"  Average Win: {avg_win:.2%}")

            if losers:
                avg_loss = sum(t['pnl_pct'] for t in losers) / len(losers)
                print(f"  Average Loss: {avg_loss:.2%}")

def main():
    backtest_dir = Path('data/backtest_results')

    # Get most recent backtests
    backtest_files = sorted(backtest_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)

    if not backtest_files:
        print("No backtest files found!")
        return

    print("=" * 100)
    print("BACKTEST VISUALIZATION ANALYSIS")
    print("=" * 100)
    print(f"\nFound {len(backtest_files)} backtest files")
    print("\nAnalyzing most recent and notable backtests...\n")

    # Analyze specific backtests
    notable_files = [
        'strategy2_simplified.json',  # Only one with positive win rate
        'strategy3_mean_reversion.json',  # Mean reversion
        'backtest_20251029_101115.json',  # Most recent
    ]

    for filename in notable_files:
        file_path = backtest_dir / filename
        if file_path.exists():
            analyze_single_backtest(file_path)

if __name__ == '__main__':
    main()
