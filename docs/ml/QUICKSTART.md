# ML Trading Strategy - Quick Start Guide

Get started with ML-based trading strategies in 5 minutes!

## Installation

```bash
# Install Python dependencies
pip install -r config/ml/requirements.txt

# Or use uv (recommended)
uv pip install scikit-learn numpy pandas matplotlib pytest
```

## Quick Example

### 1. Import Libraries

```python
from src.strategies.ml import FeatureEngineer, PricePredictor, ModelValidator
import pandas as pd
```

### 2. Load Data

```python
# Load your OHLCV data
df = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)

# Or use the example with synthetic data
from src.strategies.ml.examples.ml_strategy_example import MLTradingStrategy

strategy = MLTradingStrategy('AAPL')
strategy.load_data()  # Generates synthetic data
```

### 3. Engineer Features

```python
strategy.engineer_features()
strategy.prepare_datasets()
```

### 4. Train and Validate

```python
results = strategy.train_models(validation_method='walk_forward')
```

### 5. Generate Signals and Backtest

```python
signals = strategy.generate_signals(confidence_threshold=0.6)
backtest_results = strategy.backtest(signals)
```

## Run Complete Example

```bash
python src/strategies/ml/examples/ml_strategy_example.py
```

## Expected Output

```
==============================================================
ML TRADING STRATEGY EXAMPLE
==============================================================
Loaded 1000 bars of AAPL data
Engineering features...
Created 87 features
Preparing datasets...
Dataset shape: (918, 87)

==============================================================
TRAINING MODELS
==============================================================

1. Training Price Prediction Model...
==============================================================
MODEL VALIDATION REPORT
==============================================================
Method: walk_forward
Number of folds: 5

Average Test Metrics:
  test_mse: 0.0004 (±0.0001)
  test_r2: 0.6523 (±0.1234)

2. Training Trend Classification Model...
==============================================================
Test Metrics:
  test_accuracy: 0.6234
  test_precision: 0.6123
  test_f1: 0.5987

==============================================================
BACKTESTING
==============================================================
Initial Capital: $100,000.00
Final Value:     $112,345.67
Total Return:    12.35%
Annual Return:   45.23%
Sharpe Ratio:    1.85
Max Drawdown:    -8.45%
Number of Trades: 234
Win Rate:        55.67%
```

## Next Steps

1. **Customize Features**: Edit `FeatureConfig` to add your own indicators
2. **Try Different Models**: Test `gradient_boosting`, `ridge`, `lasso`
3. **Tune Hyperparameters**: Optimize model parameters
4. **Add Risk Management**: Implement position sizing and stop losses
5. **Deploy to Production**: Integrate with your trading system

## Common Issues

### ImportError: No module named 'sklearn'

```bash
pip install scikit-learn
```

### TA-Lib installation fails

TA-Lib is optional. If you encounter issues:
```bash
# Remove ta-lib from requirements
# Or install system dependency first:
# Ubuntu: sudo apt-get install ta-lib
# Mac: brew install ta-lib
```

### Low model accuracy

- Increase training data (aim for >1000 samples)
- Add more relevant features
- Try different models
- Use walk-forward validation
- Check for data quality issues

## Resources

- [Full Documentation](ML_STRATEGY_GUIDE.md)
- [Example Code](../src/strategies/ml/examples/)
- [Unit Tests](../tests/ml/)

## Support

For issues or questions, see the main repository documentation.

---

Happy Trading! 🚀
