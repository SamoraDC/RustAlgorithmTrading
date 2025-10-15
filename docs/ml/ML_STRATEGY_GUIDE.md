# Machine Learning Trading Strategy Implementation Guide

## Overview

This guide provides comprehensive documentation for implementing machine learning-based trading strategies in the Rust Algorithm Trading System.

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture](#architecture)
3. [Feature Engineering](#feature-engineering)
4. [Model Types](#model-types)
5. [Validation Framework](#validation-framework)
6. [Implementation Examples](#implementation-examples)
7. [Best Practices](#best-practices)
8. [Model Assumptions and Limitations](#model-assumptions-and-limitations)
9. [Performance Optimization](#performance-optimization)

## Introduction

The ML trading module provides:
- **Feature Engineering Pipeline**: Transform raw OHLCV data into ML-ready features
- **Prediction Models**: Price forecasting and trend classification
- **Validation Framework**: Robust model validation and cross-validation
- **Integration**: Seamless integration with backtesting framework

### Key Features

✅ **50+ Technical Features**: SMA, EMA, RSI, MACD, Bollinger Bands
✅ **Statistical Features**: Returns, volatility, volume analysis
✅ **Temporal Features**: Cyclical time encoding
✅ **Multiple Models**: Random Forest, Gradient Boosting, Ridge, Lasso
✅ **Time-Series CV**: Proper validation without lookahead bias
✅ **Production-Ready**: Model persistence, metadata, version control

## Architecture

```
src/strategies/ml/
├── __init__.py                 # Module exports
├── features/
│   ├── feature_engineering.py  # Main feature pipeline
│   ├── technical_features.py   # Technical indicators
│   └── statistical_features.py # Statistical computations
├── models/
│   ├── base_model.py          # Abstract base class
│   ├── price_predictor.py     # Regression models
│   └── trend_classifier.py    # Classification models
├── validation/
│   ├── model_validator.py     # Validation framework
│   └── cross_validator.py     # Cross-validation
└── examples/
    └── ml_strategy_example.py # Complete workflow example
```

## Feature Engineering

### FeatureEngineer Class

The `FeatureEngineer` class transforms raw OHLCV data into ML-ready features.

```python
from src.strategies.ml.features import FeatureEngineer, FeatureConfig

# Configure feature engineering
config = FeatureConfig(
    lookback_periods=[5, 10, 20, 50],
    technical_indicators=['sma', 'ema', 'rsi', 'macd', 'bbands'],
    statistical_features=['returns', 'volatility', 'volume_ratio'],
    scaling_method='standard',
    fill_na_method='forward'
)

# Initialize feature engineer
fe = FeatureEngineer(config)

# Engineer features
features_df = fe.engineer_features(ohlcv_data)

# Prepare ML dataset
X, y = fe.prepare_ml_dataset(
    features_df,
    target_col='next_return',
    scale_features=True
)
```

### Feature Categories

#### 1. Technical Indicators

**Simple Moving Average (SMA)**
- `sma_{period}`: Moving average over period
- `close_sma_{period}_ratio`: Current price relative to SMA

**Exponential Moving Average (EMA)**
- `ema_{period}`: Exponential moving average
- `close_ema_{period}_ratio`: Price to EMA ratio

**Relative Strength Index (RSI)**
- `rsi_14`: 14-period RSI
- `rsi_28`: 28-period RSI
- Range: 0-100 (oversold < 30, overbought > 70)

**MACD (Moving Average Convergence Divergence)**
- `macd`: MACD line (12 EMA - 26 EMA)
- `macd_signal`: Signal line (9 EMA of MACD)
- `macd_histogram`: MACD - Signal

**Bollinger Bands**
- `bb_upper_{period}`: Upper band (SMA + 2σ)
- `bb_lower_{period}`: Lower band (SMA - 2σ)
- `bb_position_{period}`: Position within bands (0-1)

#### 2. Statistical Features

**Returns**
- `returns`: Simple returns (pct_change)
- `log_returns`: Logarithmic returns
- `returns_{period}d`: Multi-period returns

**Volatility**
- `volatility_{period}d`: Historical volatility (std of returns)
- `parkinson_vol_{period}d`: Parkinson volatility (uses high/low)

**Volume**
- `volume_ratio_{period}d`: Volume relative to average
- `vwap_{period}d`: Volume-weighted average price

#### 3. Temporal Features

**Time-Based**
- `hour`, `day_of_week`, `day_of_month`, `month`, `quarter`

**Cyclical Encoding** (prevents discontinuity)
- `hour_sin`, `hour_cos`: Cyclical hour encoding
- `day_sin`, `day_cos`: Cyclical day encoding

#### 4. Lag Features

**Historical Values**
- `close_lag_{n}`: Price n periods ago
- `volume_lag_{n}`: Volume n periods ago
- `returns_lag_{n}`: Returns n periods ago

### Feature Engineering Best Practices

1. **Always Use Forward Fill for NaN**: Prevents lookahead bias
2. **Scale Features**: Use StandardScaler or MinMaxScaler
3. **Cyclical Encoding**: Use sin/cos for time features
4. **Multi-Period Features**: Include multiple timeframes
5. **Domain Knowledge**: Add industry-specific features

## Model Types

### 1. Price Predictor (Regression)

Predicts future price returns using regression algorithms.

```python
from src.strategies.ml.models import PricePredictor

# Initialize model
predictor = PricePredictor(
    model_type='random_forest',
    n_estimators=100,
    max_depth=10,
    random_state=42
)

# Train model
train_metrics = predictor.train(X_train, y_train)

# Make predictions
predictions = predictor.predict(X_test)

# Predict with confidence (ensemble models)
pred, std = predictor.predict_with_confidence(X_test)

# Evaluate
test_metrics = predictor.evaluate(X_test, y_test)

# Get feature importance
importance = predictor.get_feature_importance()
```

**Supported Models**:
- `random_forest`: Random Forest Regressor
- `gradient_boosting`: Gradient Boosting Regressor
- `ridge`: Ridge Regression (L2 regularization)
- `lasso`: Lasso Regression (L1 regularization)

**Metrics**:
- MSE (Mean Squared Error)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R² Score
- MAPE (Mean Absolute Percentage Error)

### 2. Trend Classifier (Classification)

Classifies market direction into up/down/neutral trends.

```python
from src.strategies.ml.models import TrendClassifier

# Initialize model
classifier = TrendClassifier(
    model_type='random_forest',
    neutral_threshold=0.001,  # 0.1% threshold
    n_estimators=100,
    class_weight='balanced'
)

# Train model
train_metrics = classifier.train(X_train, y_train)

# Predict trend classes
trends = classifier.predict(X_test)  # 0=down, 1=neutral, 2=up

# Predict probabilities
probas = classifier.predict_proba(X_test)

# Predict with confidence filtering
trends, mask = classifier.predict_with_confidence(X_test, threshold=0.6)

# Evaluate
test_metrics = classifier.evaluate(X_test, y_test)
```

**Trend Classes**:
- `0`: Down trend (return < -threshold)
- `1`: Neutral (|return| ≤ threshold)
- `2`: Up trend (return > threshold)

**Metrics**:
- Accuracy
- Precision (weighted, per-class)
- Recall
- F1 Score
- Classification Report

## Validation Framework

### Model Validator

Implements multiple validation strategies to prevent overfitting.

```python
from src.strategies.ml.validation import ModelValidator

validator = ModelValidator()

# Method 1: Simple train/test split
results = validator.validate_model(
    model,
    X, y,
    method='train_test',
    test_size=0.2
)

# Method 2: Train/validation/test split
results = validator.validate_model(
    model,
    X, y,
    method='train_val_test',
    test_size=0.2,
    val_size=0.1
)

# Method 3: Walk-forward validation (recommended for time series)
results = validator.validate_model(
    model,
    X, y,
    method='walk_forward',
    n_splits=5,
    min_train_size=100
)

# Print validation report
print(validator.get_validation_report())
```

### Cross-Validator

Provides time-series aware cross-validation.

```python
from src.strategies.ml.validation import CrossValidator

cv = CrossValidator(n_splits=5)

# Method 1: Time series split (expanding window)
results = cv.cross_validate(
    model,
    X, y,
    method='time_series'
)

# Method 2: Rolling window
results = cv.cross_validate(
    model,
    X, y,
    method='rolling',
    window_size=500
)

# Method 3: Purged cross-validation (avoids lookahead)
results = cv.cross_validate(
    model,
    X, y,
    method='purged',
    embargo_size=10  # Embargo 10 samples after test set
)

# Print CV report
print(cv.get_cv_report())
```

### Validation Methods Comparison

| Method | Use Case | Pros | Cons |
|--------|----------|------|------|
| Train/Test Split | Quick evaluation | Fast, simple | Single validation point |
| Train/Val/Test | Hyperparameter tuning | Separate validation set | Reduces training data |
| Walk-Forward | Production simulation | Realistic, expanding window | Computationally expensive |
| Time Series CV | Robust estimation | Multiple folds, time-aware | Slower than simple split |
| Purged CV | Avoid lookahead | Eliminates data leakage | Complex implementation |

## Implementation Examples

### Example 1: Basic Price Prediction

```python
from src.strategies.ml import FeatureEngineer, PricePredictor, ModelValidator
import pandas as pd

# Load data
df = pd.read_csv('data/AAPL_1h.csv', index_col=0, parse_dates=True)

# Engineer features
fe = FeatureEngineer()
features = fe.engineer_features(df)

# Prepare dataset
X, y = fe.prepare_ml_dataset(features, target_col='next_return')

# Train and validate
model = PricePredictor(model_type='random_forest')
validator = ModelValidator()
results = validator.validate_model(model, X, y, method='walk_forward')

print(validator.get_validation_report())
```

### Example 2: Trend Classification with Confidence

```python
from src.strategies.ml import TrendClassifier

# Initialize classifier
classifier = TrendClassifier(
    model_type='gradient_boosting',
    neutral_threshold=0.002
)

# Train
classifier.train(X_train, y_train)

# Predict with confidence filtering
predictions, confidence_mask = classifier.predict_with_confidence(
    X_test,
    threshold=0.7  # Only trade when confidence > 70%
)

# Use only high-confidence predictions
high_conf_preds = predictions[confidence_mask]
```

### Example 3: Complete Strategy Workflow

See `/src/strategies/ml/examples/ml_strategy_example.py` for a complete end-to-end example including:
- Data loading
- Feature engineering
- Model training
- Validation
- Signal generation
- Backtesting

```bash
python src/strategies/ml/examples/ml_strategy_example.py
```

## Best Practices

### 1. Data Preparation

✅ **Use Time-Aware Splitting**: Never shuffle time series data
✅ **Handle Missing Values**: Forward fill to avoid lookahead bias
✅ **Scale Features**: Standardize features before training
✅ **Create Proper Labels**: Use future returns, not current
✅ **Remove Outliers**: Cap extreme values or use robust scaling

### 2. Feature Engineering

✅ **Domain Knowledge**: Use finance-relevant features
✅ **Multiple Timeframes**: Include various lookback periods
✅ **Feature Interaction**: Consider ratios and differences
✅ **Avoid Lookahead**: Only use past information
✅ **Feature Selection**: Remove highly correlated features

### 3. Model Training

✅ **Start Simple**: Begin with Ridge/Logistic, then tree-based
✅ **Prevent Overfitting**: Use regularization and pruning
✅ **Balance Classes**: Use class_weight='balanced' for classifiers
✅ **Hyperparameter Tuning**: Use validation set or CV
✅ **Monitor Metrics**: Track multiple metrics, not just accuracy

### 4. Validation

✅ **Use Walk-Forward**: Simulates production deployment
✅ **Out-of-Time Testing**: Test on recent unseen data
✅ **Purge Overlapping Samples**: Avoid data leakage
✅ **Embargo Period**: Add gap after test set
✅ **Multiple Seeds**: Test with different random seeds

### 5. Production Deployment

✅ **Save Models**: Use pickle with metadata
✅ **Version Control**: Track model versions and parameters
✅ **Monitor Drift**: Detect when model performance degrades
✅ **Retrain Regularly**: Update models with new data
✅ **A/B Testing**: Compare new models against baseline

## Model Assumptions and Limitations

### Assumptions

All ML models make the following assumptions:

1. **Stationarity**: Market patterns are stable over time
2. **IID Data**: Features are independent and identically distributed
3. **Predictability**: Historical patterns predict future behavior
4. **Feature Completeness**: All relevant information is captured
5. **No Regime Changes**: Market behavior remains consistent

### Limitations

1. **Black Swan Events**: Cannot predict unprecedented events
2. **Regime Changes**: Performance degrades during market shifts
3. **Data Requirements**: Need sufficient training data (>1000 samples)
4. **Computational Cost**: Training can be slow for large datasets
5. **Overfitting Risk**: Complex models may memorize noise
6. **Transaction Costs**: Models don't account for slippage/fees
7. **Market Impact**: Assumes orders don't move the market

### Risk Mitigation

- **Ensemble Methods**: Combine multiple models
- **Regular Retraining**: Update models monthly/quarterly
- **Confidence Thresholds**: Only trade high-confidence signals
- **Stop Losses**: Implement risk management rules
- **Position Sizing**: Use Kelly criterion or fixed fractional
- **Monitor Metrics**: Track Sharpe, drawdown, win rate

## Performance Optimization

### Training Speed

```python
# Use parallel processing
model = RandomForestRegressor(n_jobs=-1)  # Use all cores

# Reduce model complexity
model = RandomForestRegressor(
    n_estimators=50,      # Fewer trees
    max_depth=5,          # Shallower trees
    min_samples_split=10  # Larger leaf nodes
)
```

### Prediction Speed

```python
# Batch predictions
predictions = model.predict(X_batch)  # Better than loop

# Use simpler models in production
# Gradient Boosting > Random Forest > Ridge > Linear
```

### Memory Optimization

```python
# Use float32 instead of float64
X = X.astype(np.float32)

# Free memory after use
del X_train, y_train
import gc
gc.collect()
```

## Conclusion

This ML trading module provides a complete framework for developing, validating, and deploying machine learning-based trading strategies. Follow the best practices, understand the assumptions and limitations, and always validate thoroughly before production deployment.

For questions or contributions, see the main repository documentation.

---

**Last Updated**: 2024-10-14
**Version**: 0.1.0
**Author**: ML Developer Agent - Hive Mind Swarm
