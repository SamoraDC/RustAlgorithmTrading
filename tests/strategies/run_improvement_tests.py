#!/usr/bin/env python3
"""
Test Runner for Momentum Strategy Improvements

Runs comprehensive test suite and generates detailed reports.

Usage:
    python tests/strategies/run_improvement_tests.py [options]

Options:
    --verbose, -v       Verbose output
    --quick             Run quick tests only (skip slow parametric tests)
    --html              Generate HTML report
    --markers MARKERS   Run specific test markers (e.g., parametric, integration)
"""

import sys
import argparse
from pathlib import Path
import pytest
import json
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(
        description='Run momentum strategy improvement tests'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick tests only'
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML report'
    )
    parser.add_argument(
        '--markers', '-m',
        type=str,
        help='Run specific test markers'
    )

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = [
        'tests/strategies/test_momentum_improvements.py',
        '--tb=short',
        '--color=yes',
    ]

    if args.verbose:
        pytest_args.append('-v')
    else:
        pytest_args.append('-q')

    if args.quick:
        pytest_args.extend(['-m', 'not slow'])

    if args.markers:
        pytest_args.extend(['-m', args.markers])

    if args.html:
        report_path = f'test_reports/momentum_improvements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        pytest_args.extend(['--html', report_path, '--self-contained-html'])
        print(f"HTML report will be generated at: {report_path}")

    # Print test info
    print("="*80)
    print("MOMENTUM STRATEGY IMPROVEMENTS - TEST SUITE")
    print("="*80)
    print("\nTarget Metrics:")
    print("  • Win Rate: >30% (currently 0%)")
    print("  • Total Return: >0% (currently -0.96%)")
    print("  • Total Trades: 30-40 (currently 10-20)")
    print("  • Max Drawdown: <5% (currently 0.96%)")
    print("  • Sharpe Ratio: >0.5 (currently -11.38)")
    print("="*80)
    print("\nTest Categories:")
    print("  1. Parameter Sensitivity (histogram, RSI, SMA)")
    print("  2. Volume Confirmation")
    print("  3. Trailing Stop Loss")
    print("  4. Market Regimes (trending, choppy, crash)")
    print("  5. Integration & Walk-Forward")
    print("  6. Performance Metrics Validation")
    print("="*80)
    print()

    # Run tests
    exit_code = pytest.main(pytest_args)

    # Print summary
    print("\n" + "="*80)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ TESTS FAILED (exit code: {exit_code})")
    print("="*80)

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
