#!/usr/bin/env python3
"""
Strategy Performance Analyzer and Router

Analyzes all available trading strategies and recommends the best one based on:
- Historical performance
- Market conditions
- Data availability
- Risk metrics
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import BacktestEngine
from backtesting.data_handler import HistoricalDataHandler
from backtesting.execution_handler import SimulatedExecutionHandler
from backtesting.portfolio_handler import PortfolioHandler

# Import all available strategies (using correct class names)
from strategies.simple_momentum import SimpleMomentumStrategy
from strategies.momentum_simplified import SimplifiedMomentumStrategy
from strategies.moving_average import MovingAverageCrossover  # Correct class name
from strategies.mean_reversion import MeanReversion  # Correct class name
from strategies.enhanced_momentum import EnhancedMomentumStrategy
from strategies.momentum import MomentumStrategy

print("=" * 80)
print("TRADING STRATEGY ANALYZER")
print("=" * 80)
print()

# Configuration
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL']
INITIAL_CAPITAL = 1000.0
DATA_DIR = Path('data/historical')

# Calculate date range
end_date = datetime.now() - timedelta(days=2)
start_date = end_date - timedelta(days=365)

print(f"Configuration:")
print(f"  Symbols: {SYMBOLS}")
print(f"  Period: {start_date.date()} to {end_date.date()}")
print(f"  Initial Capital: ${INITIAL_CAPITAL:,.2f}")
print(f"  Data Directory: {DATA_DIR}")
print()

# Define strategies to test
STRATEGIES = [
    {
        'name': 'Simple Momentum',
        'class': SimpleMomentumStrategy,
        'params': {
            'symbols': SYMBOLS,
            'rsi_period': 14,
            'rsi_oversold': 30,  # More aggressive (industry standard)
            'rsi_overbought': 70,
            'position_size': 0.10
        },
        'description': 'RSI-based momentum strategy with industry-standard thresholds (30/70)'
    },
    {
        'name': 'Simplified Momentum',
        'class': SimplifiedMomentumStrategy,
        'params': {
            'symbols': SYMBOLS,
            'rsi_period': 14,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            'position_size': 0.10
        },
        'description': 'Less aggressive momentum with relaxed RSI thresholds (35/65)'
    },
    {
        'name': 'Moving Average Crossover',
        'class': MovingAverageStrategy,
        'params': {
            'fast_period': 10,
            'slow_period': 20,
            'position_size': 0.10
        },
        'description': 'Classic moving average crossover (10/20)'
    },
    {
        'name': 'Mean Reversion',
        'class': MeanReversionStrategy,
        'params': {
            'lookback_period': 20,
            'std_threshold': 2.0,
            'position_size': 0.10
        },
        'description': 'Bollinger Bands mean reversion strategy'
    },
    {
        'name': 'Regime-Aware Momentum',
        'class': RegimeAwareMomentumStrategy,
        'params': {
            'symbols': SYMBOLS,
            'rsi_period': 14,
            'adx_threshold': 20,  # Lower threshold for more signals
            'position_size': 0.10
        },
        'description': 'Adaptive momentum that adjusts to market regime'
    }
]

def run_strategy_backtest(strategy_config: Dict[str, Any]) -> Dict[str, Any]:
    """Run backtest for a single strategy"""

    print(f"\n{'='*80}")
    print(f"Testing: {strategy_config['name']}")
    print(f"{'='*80}")
    print(f"Description: {strategy_config['description']}")
    print(f"Parameters: {strategy_config['params']}")
    print()

    try:
        # Initialize components
        data_handler = HistoricalDataHandler(
            symbols=SYMBOLS,
            data_dir=DATA_DIR,
            start_date=start_date,
            end_date=end_date
        )

        execution_handler = SimulatedExecutionHandler()

        portfolio_handler = PortfolioHandler(
            initial_capital=INITIAL_CAPITAL,
            data_handler=data_handler
        )

        # Initialize strategy with params
        strategy = strategy_config['class'](**strategy_config['params'])

        # Create backtest engine
        engine = BacktestEngine(
            data_handler=data_handler,
            execution_handler=execution_handler,
            portfolio_handler=portfolio_handler,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date
        )

        # Run backtest
        print("Running backtest...")
        results = engine.run()

        # Extract metrics
        metrics = results.get('metrics', {})

        # Calculate score (higher is better)
        sharpe = metrics.get('sharpe_ratio', 0)
        win_rate = metrics.get('win_rate', 0) / 100.0
        total_return = metrics.get('total_return', 0)
        max_dd = abs(metrics.get('max_drawdown', 0)) / 100.0

        # Composite score: sharpe * 40% + win_rate * 30% + return * 20% - drawdown * 10%
        score = (sharpe * 0.4) + (win_rate * 0.3) + (total_return * 0.2) - (max_dd * 0.1)

        result = {
            'name': strategy_config['name'],
            'description': strategy_config['description'],
            'metrics': metrics,
            'score': score,
            'signals_generated': results.get('stats', {}).get('signals_generated', 0),
            'trades_executed': results.get('stats', {}).get('fills_executed', 0),
            'success': True
        }

        # Print summary
        print(f"\n✅ Backtest Complete")
        print(f"  Signals Generated: {result['signals_generated']}")
        print(f"  Trades Executed: {result['trades_executed']}")
        print(f"  Total Return: {total_return*100:.2f}%")
        print(f"  Sharpe Ratio: {sharpe:.2f}")
        print(f"  Win Rate: {win_rate*100:.2f}%")
        print(f"  Max Drawdown: {max_dd*100:.2f}%")
        print(f"  Composite Score: {score:.4f}")

        return result

    except Exception as e:
        print(f"\n❌ Error running strategy: {e}")
        import traceback
        traceback.print_exc()

        return {
            'name': strategy_config['name'],
            'description': strategy_config['description'],
            'error': str(e),
            'score': float('-inf'),
            'success': False
        }

def main():
    """Main execution"""

    print("Starting strategy analysis...")
    print(f"Testing {len(STRATEGIES)} strategies")
    print()

    results = []

    # Test each strategy
    for strategy_config in STRATEGIES:
        result = run_strategy_backtest(strategy_config)
        results.append(result)

    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    # Print final rankings
    print("\n" + "="*80)
    print("FINAL RANKINGS")
    print("="*80)
    print()

    for i, result in enumerate(results, 1):
        if result['success']:
            print(f"{i}. {result['name']} (Score: {result['score']:.4f})")
            print(f"   {result['description']}")
            print(f"   Signals: {result['signals_generated']} | Trades: {result['trades_executed']}")

            metrics = result.get('metrics', {})
            print(f"   Return: {metrics.get('total_return', 0)*100:.2f}% | "
                  f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f} | "
                  f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
        else:
            print(f"{i}. {result['name']} (FAILED)")
            print(f"   Error: {result.get('error', 'Unknown error')}")
        print()

    # Save results
    output_file = f"data/strategy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results saved to: {output_file}")
    print()

    # Recommendation
    if results and results[0]['success']:
        best = results[0]
        print("="*80)
        print("🏆 RECOMMENDATION")
        print("="*80)
        print(f"Best Strategy: {best['name']}")
        print(f"Score: {best['score']:.4f}")
        print(f"Description: {best['description']}")
        print()
        print("This strategy should be used for live trading based on historical performance.")
        print("="*80)
    else:
        print("⚠️  WARNING: No strategy performed successfully!")
        print("Review the errors above and check data availability.")

    return 0 if results and results[0]['success'] else 1

if __name__ == "__main__":
    sys.exit(main())
