#!/usr/bin/env python3
"""
Signal Analysis Diagnostic Tool

Parses backtest logs and generates comprehensive signal quality reports.
Identifies signal execution failures, counts signals by type, and provides
actionable insights for debugging trading strategies.

Usage:
    python scripts/analyze_signals.py [log_file]
    python scripts/analyze_signals.py --recent  # Analyze most recent log
    python scripts/analyze_signals.py --help
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json


@dataclass
class SignalStats:
    """Signal statistics container"""
    total: int = 0
    long: int = 0
    short: int = 0
    exit: int = 0
    hold: int = 0
    executed: int = 0
    blocked: int = 0
    failed: int = 0
    avg_confidence: float = 0.0
    confidence_sum: float = 0.0

    symbols: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    exit_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    block_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    failures: List[str] = field(default_factory=list)


@dataclass
class OrderStats:
    """Order statistics container"""
    total: int = 0
    buy: int = 0
    sell: int = 0
    filled: int = 0
    rejected: int = 0
    total_value: float = 0.0

    by_symbol: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class PerformanceStats:
    """Performance statistics container"""
    entries: int = 0
    exits: int = 0
    total_pnl: float = 0.0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_pnl_pct: float = 0.0
    max_win_pct: float = 0.0
    max_loss_pct: float = 0.0

    pnl_by_symbol: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    trades_by_reason: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class SignalAnalyzer:
    """Analyzes trading signals from log files"""

    # Regular expressions for parsing log entries
    SIGNAL_PATTERNS = {
        'signal_received': r'📥 Signal received: (\w+) for (\w+) @ \$([0-9.]+), confidence=([0-9.]+)',
        'long_signal': r'🟢 LONG SIGNAL: (\w+) @ \$([0-9.]+)',
        'short_signal': r'🔴 SHORT SIGNAL: (\w+) @ \$([0-9.]+)',
        'signal_blocked': r'🟡 (\w+) signal blocked by conditions:(.+)',
        'order_generated': r'✅ ORDER GENERATED: (\w+) (\d+) (\w+) @ \$([0-9.]+).*Signal: (\w+), Confidence: ([0-9.]+)',
        'entry_fill': r'💰 ENTRY: (\w+) \| (\d+) shares @ \$([0-9.]+) \| Cost: \$([0-9,]+\.[0-9]+)',
        'exit_fill': r'💵 EXIT: (\w+) \| (\d+) shares @ \$([0-9.]+) \| Entry: \$([0-9.]+) \| P&L: \$([0-9,.-]+) \(([+-][0-9.]+%)\)',
        'cash_negative': r'❌ Available cash is negative',
        'insufficient_cash': r'Insufficient.*cash',
    }

    def __init__(self, log_file: Path):
        """Initialize analyzer with log file"""
        self.log_file = log_file
        self.signals = SignalStats()
        self.orders = OrderStats()
        self.performance = PerformanceStats()
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse_log(self) -> None:
        """Parse log file and extract statistics"""
        if not self.log_file.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file}")

        print(f"📊 Analyzing log file: {self.log_file}")
        print(f"   Size: {self.log_file.stat().st_size / 1024:.1f} KB")
        print()

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    self._parse_line(line, line_num)
                except Exception as e:
                    self.errors.append(f"Line {line_num}: {str(e)}")

        # Calculate averages
        if self.signals.total > 0:
            self.signals.avg_confidence = self.signals.confidence_sum / self.signals.total

        if self.performance.exits > 0:
            self.performance.avg_pnl_pct = self.performance.total_pnl / self.performance.exits

    def _parse_line(self, line: str, line_num: int) -> None:
        """Parse a single log line"""
        # Signal received
        match = re.search(self.SIGNAL_PATTERNS['signal_received'], line)
        if match:
            signal_type, symbol, price, confidence = match.groups()
            self.signals.total += 1
            self.signals.symbols[symbol] += 1
            self.signals.confidence_sum += float(confidence)

            if signal_type == 'LONG':
                self.signals.long += 1
            elif signal_type == 'SHORT':
                self.signals.short += 1
            elif signal_type == 'EXIT':
                self.signals.exit += 1
            else:
                self.signals.hold += 1
            return

        # Long signal
        match = re.search(self.SIGNAL_PATTERNS['long_signal'], line)
        if match:
            symbol, price = match.groups()
            self.signals.long += 1
            self.signals.symbols[symbol] += 1
            return

        # Short signal
        match = re.search(self.SIGNAL_PATTERNS['short_signal'], line)
        if match:
            symbol, price = match.groups()
            self.signals.short += 1
            self.signals.symbols[symbol] += 1
            return

        # Signal blocked
        match = re.search(self.SIGNAL_PATTERNS['signal_blocked'], line)
        if match:
            signal_type, reason = match.groups()
            self.signals.blocked += 1
            self.signals.block_reasons[reason.strip()] += 1
            return

        # Order generated
        match = re.search(self.SIGNAL_PATTERNS['order_generated'], line)
        if match:
            direction, quantity, symbol, price, signal_type, confidence = match.groups()
            self.orders.total += 1
            self.signals.executed += 1

            if direction == 'BUY':
                self.orders.buy += 1
            else:
                self.orders.sell += 1

            self.orders.by_symbol[symbol] += 1
            self.orders.total_value += float(quantity) * float(price)
            return

        # Entry fill
        match = re.search(self.SIGNAL_PATTERNS['entry_fill'], line)
        if match:
            symbol, shares, price, cost = match.groups()
            self.orders.filled += 1
            self.performance.entries += 1
            return

        # Exit fill with P&L
        match = re.search(self.SIGNAL_PATTERNS['exit_fill'], line)
        if match:
            symbol, shares, exit_price, entry_price, pnl, pnl_pct = match.groups()
            self.orders.filled += 1
            self.performance.exits += 1

            pnl_value = float(pnl.replace(',', ''))
            pnl_pct_value = float(pnl_pct.rstrip('%'))

            self.performance.total_pnl += pnl_pct_value
            self.performance.pnl_by_symbol[symbol] += pnl_pct_value

            if pnl_value > 0:
                self.performance.winning_trades += 1
                self.performance.max_win_pct = max(self.performance.max_win_pct, pnl_pct_value)
            else:
                self.performance.losing_trades += 1
                self.performance.max_loss_pct = min(self.performance.max_loss_pct, pnl_pct_value)

            # Extract exit reason if present
            if 'reason=' in line:
                reason_match = re.search(r'reason=(\w+)', line)
                if reason_match:
                    self.performance.trades_by_reason[reason_match.group(1)] += 1

            return

        # Errors and warnings
        if 'ERROR' in line or '❌' in line:
            self.errors.append(line.strip())
        elif 'WARNING' in line or '⚠️' in line:
            self.warnings.append(line.strip())

    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        report = []
        report.append("=" * 80)
        report.append("SIGNAL ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Log File: {self.log_file}")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Signal Statistics
        report.append("📊 SIGNAL STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Signals:        {self.signals.total:>10}")
        report.append(f"  ├─ LONG signals:    {self.signals.long:>10}")
        report.append(f"  ├─ SHORT signals:   {self.signals.short:>10}")
        report.append(f"  ├─ EXIT signals:    {self.signals.exit:>10}")
        report.append(f"  └─ HOLD signals:    {self.signals.hold:>10}")
        report.append("")
        report.append(f"Executed Signals:     {self.signals.executed:>10} ({self._pct(self.signals.executed, self.signals.total)})")
        report.append(f"Blocked Signals:      {self.signals.blocked:>10} ({self._pct(self.signals.blocked, self.signals.total)})")
        report.append(f"Average Confidence:   {self.signals.avg_confidence:>10.2f}")
        report.append("")

        # Signals by symbol
        if self.signals.symbols:
            report.append("Signals by Symbol:")
            for symbol, count in sorted(self.signals.symbols.items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  {symbol:>10}: {count:>5} ({self._pct(count, self.signals.total)})")
        report.append("")

        # Block reasons
        if self.signals.block_reasons:
            report.append("🚫 SIGNAL BLOCK REASONS")
            report.append("-" * 80)
            for reason, count in sorted(self.signals.block_reasons.items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {count:>5}x: {reason}")
            report.append("")

        # Order Statistics
        report.append("📝 ORDER STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Orders:         {self.orders.total:>10}")
        report.append(f"  ├─ BUY orders:      {self.orders.buy:>10}")
        report.append(f"  └─ SELL orders:     {self.orders.sell:>10}")
        report.append("")
        report.append(f"Orders Filled:        {self.orders.filled:>10} ({self._pct(self.orders.filled, self.orders.total)})")
        report.append(f"Orders Rejected:      {self.orders.rejected:>10}")
        report.append(f"Total Order Value:    ${self.orders.total_value:>10,.2f}")
        report.append("")

        # Performance Statistics
        report.append("💰 PERFORMANCE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Entries:        {self.performance.entries:>10}")
        report.append(f"Total Exits:          {self.performance.exits:>10}")
        report.append("")

        if self.performance.exits > 0:
            total_trades = self.performance.winning_trades + self.performance.losing_trades
            win_rate = (self.performance.winning_trades / total_trades * 100) if total_trades > 0 else 0

            report.append(f"Winning Trades:       {self.performance.winning_trades:>10} ({win_rate:.1f}%)")
            report.append(f"Losing Trades:        {self.performance.losing_trades:>10} ({100-win_rate:.1f}%)")
            report.append("")
            report.append(f"Total P&L:            {self.performance.total_pnl:>10.2f}%")
            report.append(f"Average P&L:          {self.performance.avg_pnl_pct:>10.2f}%")
            report.append(f"Max Win:              {self.performance.max_win_pct:>10.2f}%")
            report.append(f"Max Loss:             {self.performance.max_loss_pct:>10.2f}%")
            report.append("")

            # Exit reasons
            if self.performance.trades_by_reason:
                report.append("Exit Reasons:")
                for reason, count in sorted(self.performance.trades_by_reason.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {reason:>20}: {count:>5} ({self._pct(count, self.performance.exits)})")
                report.append("")

        # Errors and Warnings
        if self.errors:
            report.append("❌ ERRORS")
            report.append("-" * 80)
            for error in self.errors[:20]:  # Show first 20 errors
                report.append(f"  {error[:100]}")
            if len(self.errors) > 20:
                report.append(f"  ... and {len(self.errors) - 20} more errors")
            report.append("")

        if self.warnings:
            report.append("⚠️  WARNINGS")
            report.append("-" * 80)
            for warning in self.warnings[:20]:  # Show first 20 warnings
                report.append(f"  {warning[:100]}")
            if len(self.warnings) > 20:
                report.append(f"  ... and {len(self.warnings) - 20} more warnings")
            report.append("")

        # Signal Quality Assessment
        report.append("🎯 SIGNAL QUALITY ASSESSMENT")
        report.append("-" * 80)

        # Calculate signal execution rate
        execution_rate = (self.signals.executed / self.signals.total * 100) if self.signals.total > 0 else 0

        if execution_rate < 10:
            report.append("⛔ CRITICAL: Less than 10% of signals are being executed!")
            report.append("   Action: Review signal generation logic and check for overly restrictive filters")
        elif execution_rate < 30:
            report.append("⚠️  WARNING: Low signal execution rate (<30%)")
            report.append("   Action: Consider relaxing entry conditions or reviewing block reasons")
        elif execution_rate > 80:
            report.append("✅ GOOD: High signal execution rate (>80%)")
        else:
            report.append("✅ OK: Moderate signal execution rate (30-80%)")

        report.append("")

        # Check for zero signals
        if self.signals.total == 0:
            report.append("❌ CRITICAL: NO SIGNALS GENERATED!")
            report.append("   Action: Check strategy logic, data availability, and indicator calculations")
        elif self.signals.long == 0 and self.signals.short == 0:
            report.append("❌ CRITICAL: No entry signals (LONG/SHORT) generated!")
            report.append("   Action: Review entry conditions and thresholds")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    @staticmethod
    def _pct(value: int, total: int) -> str:
        """Calculate percentage string"""
        if total == 0:
            return "0.0%"
        return f"{value / total * 100:.1f}%"

    def export_json(self, output_file: Path) -> None:
        """Export statistics as JSON"""
        data = {
            'log_file': str(self.log_file),
            'generated_at': datetime.now().isoformat(),
            'signals': {
                'total': self.signals.total,
                'long': self.signals.long,
                'short': self.signals.short,
                'exit': self.signals.exit,
                'hold': self.signals.hold,
                'executed': self.signals.executed,
                'blocked': self.signals.blocked,
                'avg_confidence': round(self.signals.avg_confidence, 3),
                'by_symbol': dict(self.signals.symbols),
                'block_reasons': dict(self.signals.block_reasons),
            },
            'orders': {
                'total': self.orders.total,
                'buy': self.orders.buy,
                'sell': self.orders.sell,
                'filled': self.orders.filled,
                'rejected': self.orders.rejected,
                'total_value': round(self.orders.total_value, 2),
                'by_symbol': dict(self.orders.by_symbol),
            },
            'performance': {
                'entries': self.performance.entries,
                'exits': self.performance.exits,
                'winning_trades': self.performance.winning_trades,
                'losing_trades': self.performance.losing_trades,
                'total_pnl_pct': round(self.performance.total_pnl, 2),
                'avg_pnl_pct': round(self.performance.avg_pnl_pct, 2),
                'max_win_pct': round(self.performance.max_win_pct, 2),
                'max_loss_pct': round(self.performance.max_loss_pct, 2),
                'trades_by_reason': dict(self.performance.trades_by_reason),
                'pnl_by_symbol': {k: round(v, 2) for k, v in self.performance.pnl_by_symbol.items()},
            },
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings),
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"📄 JSON export saved to: {output_file}")


def find_recent_log() -> Optional[Path]:
    """Find the most recent log file"""
    log_dirs = [
        Path('logs'),
        Path('tests/logs'),
        Path('.'),
    ]

    for log_dir in log_dirs:
        if not log_dir.exists():
            continue

        log_files = list(log_dir.glob('*.log'))
        if log_files:
            # Return most recently modified
            return max(log_files, key=lambda p: p.stat().st_mtime)

    return None


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze trading signals from backtest logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/analyze_signals.py logs/backtest.log
  python scripts/analyze_signals.py --recent
  python scripts/analyze_signals.py tests/logs/pytest.log --json stats.json
        """
    )
    parser.add_argument('log_file', nargs='?', help='Path to log file')
    parser.add_argument('--recent', action='store_true', help='Analyze most recent log file')
    parser.add_argument('--json', metavar='FILE', help='Export statistics to JSON file')

    args = parser.parse_args()

    # Determine log file
    log_file = None
    if args.recent:
        log_file = find_recent_log()
        if not log_file:
            print("❌ Error: No log files found in common directories")
            sys.exit(1)
    elif args.log_file:
        log_file = Path(args.log_file)
    else:
        parser.print_help()
        sys.exit(1)

    # Analyze log
    try:
        analyzer = SignalAnalyzer(log_file)
        analyzer.parse_log()

        # Generate and print report
        report = analyzer.generate_report()
        print(report)

        # Export JSON if requested
        if args.json:
            analyzer.export_json(Path(args.json))

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
