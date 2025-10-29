# Strategy Tests - Quick Reference

## 📁 Files Created

- **`test_momentum_improvements.py`** - Comprehensive test suite (29KB, 800+ lines)
- **`conftest.py`** - Shared fixtures and configuration
- **`run_improvement_tests.py`** - Test runner with reporting
- **`README.md`** - This file

## 🎯 Quick Start

### Run All Tests
```bash
# From project root
python tests/strategies/run_improvement_tests.py --verbose

# Or with pytest directly
pytest tests/strategies/test_momentum_improvements.py -v
```

### Run Specific Test Category
```bash
# Parameter sensitivity tests
pytest tests/strategies/test_momentum_improvements.py::TestParameterSensitivity -v

# Volume confirmation tests
pytest tests/strategies/test_momentum_improvements.py::TestVolumeConfirmation -v

# Trailing stop tests
pytest tests/strategies/test_momentum_improvements.py::TestTrailingStopLoss -v

# Market regime tests
pytest tests/strategies/test_momentum_improvements.py::TestMarketRegimes -v

# Integration tests
pytest tests/strategies/test_momentum_improvements.py::TestIntegrationAndWalkForward -v

# Performance metric validation
pytest tests/strategies/test_momentum_improvements.py::TestPerformanceMetrics -v
```

### Run Quick Tests Only (Skip Slow Parametric)
```bash
python tests/strategies/run_improvement_tests.py --quick
```

### Generate HTML Report
```bash
python tests/strategies/run_improvement_tests.py --html
# Report saved to: test_reports/momentum_improvements_YYYYMMDD_HHMMSS.html
```

## 📊 Test Categories Summary

| Category | Tests | Purpose |
|----------|-------|---------|
| **Parameter Sensitivity** | 4 | Find optimal parameters (histogram, RSI, SMA) |
| **Volume Confirmation** | 2 | Validate volume filter reduces false signals |
| **Trailing Stops** | 2 | Compare trailing vs fixed take-profit |
| **Market Regimes** | 3 | Test across trending/choppy/crash scenarios |
| **Integration** | 3 | Full backtest, walk-forward, out-of-sample |
| **Performance Metrics** | 2 | Validate target metrics achievement |

**Total**: 16+ test methods with parametric variations (60+ test runs)

## 🎯 Target Metrics Being Validated

- ✅ Win Rate: >30% (currently 0%)
- ✅ Total Return: >0% (currently -0.96%)
- ✅ Total Trades: 30-40 (currently 10-20)
- ✅ Max Drawdown: <5% (currently 0.96%)
- ✅ Sharpe Ratio: >0.5 (currently -11.38)

## 🔧 Key Parameters Being Tested

### MACD Histogram Threshold
- Values: `[0.0003, 0.0005, 0.001, 0.002]`
- Impact: Signal filtering quality

### RSI Midpoint
- Values: `[45, 47, 50, 52, 55]`
- Impact: Entry timing optimization

### SMA Period
- Values: `[None, 20, 50, 100, 200]`
- Impact: Trend confirmation

### Volume Multiplier
- Values: `[1.0, 1.2, 1.5, 2.0]`
- Impact: False breakout reduction

### Trailing Stop
- Values: `[1%, 1.5%, 2%, 2.5%]`
- Impact: Profit capture efficiency

## 📖 Example Usage

### Basic Test Run
```python
# Run from Python
import pytest

# All tests
pytest.main(['tests/strategies/test_momentum_improvements.py', '-v'])

# Specific test
pytest.main([
    'tests/strategies/test_momentum_improvements.py::TestParameterSensitivity::test_optimal_parameter_combination',
    '-v', '-s'
])
```

### Viewing Test Output
```bash
# Verbose with output
pytest tests/strategies/test_momentum_improvements.py -v -s

# Show only failures
pytest tests/strategies/test_momentum_improvements.py --tb=short

# Stop after first failure
pytest tests/strategies/test_momentum_improvements.py -x
```

## 📈 Interpreting Results

### Parameter Sensitivity
Look for:
- **Signal count**: 30-60 optimal
- **Average confidence**: >55%
- **Balance**: 40-60% LONG ratio

### Volume Filter
Look for:
- **Signal reduction**: 20-30%
- **Quality improvement**: Higher confidence on remaining signals

### Trailing Stops
Look for:
- **Profit extension**: 10-20% better in trends
- **Optimal distance**: 1.5-2%

### Market Regimes
Look for:
- **Trending**: >60% directional bias
- **Choppy**: Balanced signals, fewer total
- **Crash**: >30% defensive positioning

## 🐛 Troubleshooting

### Tests Fail with Import Errors
```bash
# Ensure you're in project root
cd /path/to/RustAlgorithmTrading

# Install dependencies
pip install -r requirements.txt
```

### Tests Timeout
```bash
# Run quick tests only
python tests/strategies/run_improvement_tests.py --quick
```

### Want More Detail
```bash
# Maximum verbosity
pytest tests/strategies/test_momentum_improvements.py -vv -s --tb=long
```

## 📚 Documentation

- **Full Test Documentation**: `/docs/testing/MOMENTUM_IMPROVEMENT_TESTS.md`
- **Strategy Implementation**: `/src/strategies/momentum.py`
- **Overtrading Fix**: `/docs/fixes/OVERTRADING_FIX.md`
- **Backtest Engine**: `/src/backtesting/backtest.py`

## 🔄 Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run Strategy Tests
  run: |
    python tests/strategies/run_improvement_tests.py --verbose
```

## 📞 Next Steps

1. **Run tests**: `python tests/strategies/run_improvement_tests.py --verbose`
2. **Analyze results**: Review parameter optimization outputs
3. **Update strategy**: Apply optimal parameters to momentum.py
4. **Backtest validation**: Run full backtest with optimal config
5. **Paper trading**: Validate in live market conditions

---

**Created**: 2025-10-29
**Version**: 1.0
**Status**: ✅ Ready for execution
