# Momentum Strategy Improvement Tests

**Created**: 2025-10-29
**Purpose**: Comprehensive validation of strategy improvements to achieve target metrics
**Status**: 🧪 Ready for Execution

---

## 🎯 Target Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Win Rate** | 0% | >30% | ❌ Needs Improvement |
| **Total Return** | -0.96% | >0% | ❌ Needs Improvement |
| **Total Trades** | 10-20 | 30-40 | ⚠️ Below Target |
| **Max Drawdown** | 0.96% | <5% | ✅ Within Target |
| **Sharpe Ratio** | -11.38 | >0.5 | ❌ Needs Improvement |

---

## 📋 Test Suite Overview

### 1. Parameter Sensitivity Tests (`TestParameterSensitivity`)

**Purpose**: Find optimal parameter combinations for best risk-adjusted returns

#### Tests Included:

- **MACD Histogram Threshold** (`test_macd_histogram_threshold_sensitivity`)
  - Tests: `[0.0003, 0.0005, 0.001, 0.002]`
  - Expected: Higher thresholds → fewer, higher-quality signals
  - Validates: Signal quality vs quantity trade-off

- **RSI Midpoint Levels** (`test_rsi_midpoint_sensitivity`)
  - Tests: `[45, 47, 50, 52, 55]`
  - Expected: Trend-following entries at RSI crossovers
  - Validates: Entry timing optimization

- **SMA Trend Filter** (`test_sma_trend_filter_sensitivity`)
  - Tests: `[None, 20, 50, 100, 200]`
  - Expected: Longer SMAs → stronger trend confirmation
  - Validates: False breakout reduction

- **Optimal Combination** (`test_optimal_parameter_combination`)
  - Grid search over key parameters
  - Scores based on confidence × signal count - imbalance
  - Identifies best parameter set

---

### 2. Volume Confirmation Tests (`TestVolumeConfirmation`)

**Purpose**: Validate volume filter reduces false breakouts

#### Tests Included:

- **Volume Multiplier Impact** (`test_volume_multiplier_impact`)
  - Tests: `[1.0, 1.2, 1.5, 2.0]`
  - Expected: Higher multipliers → fewer signals (volume spikes only)
  - Validates: Breakout quality improvement

- **Filter Comparison** (`test_volume_filter_vs_no_filter`)
  - Compares with/without volume filter
  - Expected: 20%+ signal reduction with filter
  - Validates: False breakout elimination

**Key Insight**: Volume confirmation should reduce noise while preserving genuine breakouts.

---

### 3. Trailing Stop Loss Tests (`TestTrailingStopLoss`)

**Purpose**: Compare trailing stops vs fixed take-profit for profit maximization

#### Tests Included:

- **Trailing Percentages** (`test_trailing_stop_percentages`)
  - Tests: `[1%, 1.5%, 2%, 2.5%]`
  - Expected: Tighter trails → faster profit-taking
  - Validates: Optimal trailing distance

- **Trailing vs Fixed** (`test_trailing_vs_fixed_takeprofit`)
  - Compares strategies in trending market
  - Expected: Trailing captures more of trend
  - Validates: Profit capture efficiency

**Key Insight**: Trailing stops should extend winners while protecting profits.

---

### 4. Market Regime Tests (`TestMarketRegimes`)

**Purpose**: Ensure strategy performs across different market conditions

#### Market Scenarios:

##### A. Trending Market (Bull Run 2023-style)
- **Characteristics**: Strong uptrend with minor pullbacks
- **Expected**: 60%+ LONG signals
- **Test**: `test_trending_market_performance`

##### B. Choppy Market (2022 Volatility)
- **Characteristics**: Range-bound with high volatility
- **Expected**: Balanced LONG/SHORT, fewer signals
- **Test**: `test_choppy_market_performance`
- **Adaptations**: Wider stops, tighter targets, longer holds

##### C. Crash Scenario (2020 COVID-style)
- **Characteristics**: Sharp decline, high volume
- **Expected**: 30%+ defensive ratio (SHORT + EXIT)
- **Test**: `test_crash_scenario_protection`
- **Adaptations**: Quick exits, tight stops

**Key Insight**: Strategy should adapt to market regime or maintain performance across conditions.

---

### 5. Integration & Walk-Forward Tests (`TestIntegrationAndWalkForward`)

**Purpose**: Validate full strategy integration and out-of-sample performance

#### Tests Included:

- **Full Integration** (`test_full_backtest_integration`)
  - Full year backtest with all improvements
  - Validates: 30-60 signals, >50% avg confidence
  - Checks: Signal distribution, quality metrics

- **Walk-Forward Optimization** (`test_walk_forward_optimization`)
  - Train: First 6 months
  - Test: Last 6 months
  - Validates: Stable performance (no overfitting)
  - Checks: Confidence stability (<15% difference)

- **Out-of-Sample Validation** (`test_out_of_sample_validation`)
  - Tests on 2023 data (different pattern)
  - Validates: Strategy generalization
  - Checks: ≥15 signals on unseen data

**Key Insight**: Strategy must perform consistently across time periods.

---

### 6. Performance Metrics Tests (`TestPerformanceMetrics`)

**Purpose**: Validate achievement of target metrics

#### Tests Included:

- **Target Metrics Validation** (`test_target_metrics_validation`)
  - Documents target requirements
  - Placeholder for backtest integration

- **Minimum Holding Period** (`test_minimum_holding_period_enforcement`)
  - Validates: Positions held ≥10 bars
  - Prevents: Overtrading/churning
  - Checks: Exit metadata for `bars_held`

**Key Insight**: Enforce minimum hold to prevent commission death spiral.

---

## 🚀 Running the Tests

### Quick Run (Core Tests Only)
```bash
python tests/strategies/run_improvement_tests.py --quick
```

### Full Run (All Tests)
```bash
python tests/strategies/run_improvement_tests.py --verbose
```

### Specific Test Category
```bash
# Parameter sensitivity only
pytest tests/strategies/test_momentum_improvements.py::TestParameterSensitivity -v

# Market regimes only
pytest tests/strategies/test_momentum_improvements.py::TestMarketRegimes -v

# Integration tests only
pytest tests/strategies/test_momentum_improvements.py::TestIntegrationAndWalkForward -v
```

### Generate HTML Report
```bash
python tests/strategies/run_improvement_tests.py --html
```

---

## 📊 Expected Test Results

### Parameter Sensitivity
- **Histogram 0.001**: Best balance (30-50 signals, 60%+ confidence)
- **RSI 50**: Optimal midpoint for trend-following
- **SMA 50**: Good trend confirmation without lag

### Volume Confirmation
- **Multiplier 1.5**: Sweet spot (reduces noise, keeps genuine signals)
- **Signal Reduction**: 20-30% with volume filter

### Trailing Stops
- **1.5-2%**: Optimal trailing distance
- **Profit Extension**: 10-20% better in trends vs fixed TP

### Market Regimes
- **Trending**: 60%+ directional signals
- **Choppy**: Balanced signals, <50% of trending signal count
- **Crash**: 30%+ defensive positioning

### Integration
- **Signal Count**: 30-60 per year
- **Confidence**: 55%+ average
- **Stability**: <15% confidence difference train/test

---

## 🔧 Key Improvements to Validate

### 1. Minimum Holding Period (10 bars)
- **Problem**: Overtrading (137 trades → -10% return)
- **Solution**: Force 10-bar minimum hold
- **Test**: `test_minimum_holding_period_enforcement`
- **Expected**: <30 trades, no churning pattern

### 2. Stricter Exit Thresholds
- **Old**: RSI 60/40 (too sensitive)
- **New**: RSI 70/30 (extreme reversals only)
- **Test**: Parameter sensitivity tests
- **Expected**: Fewer false exits, longer winning trades

### 3. SMA Trend Filter
- **Addition**: 50-period SMA
- **Purpose**: Filter counter-trend signals
- **Test**: `test_sma_trend_filter_sensitivity`
- **Expected**: 15-25% signal reduction, improved quality

### 4. Volume Confirmation
- **Addition**: 1.5x average volume requirement
- **Purpose**: Confirm genuine breakouts
- **Test**: Volume confirmation tests
- **Expected**: Reduced false breakouts

---

## 📈 Success Criteria

### Tier 1 (Critical)
- ✅ Win Rate ≥ 30%
- ✅ Total Return > 0%
- ✅ Sharpe Ratio > 0.5
- ✅ Max Drawdown < 5%

### Tier 2 (Important)
- ✅ Total Trades: 30-40
- ✅ Average Confidence: >55%
- ✅ Signal Balance: 40-60% LONG ratio
- ✅ Minimum Hold: ≥10 bars

### Tier 3 (Nice to Have)
- ✅ Walk-Forward Stable: <15% metric variance
- ✅ Out-of-Sample: ≥15 signals
- ✅ Market Regime Adaptive

---

## 🧪 Test Execution Workflow

### Phase 1: Unit Tests (Individual Components)
```bash
pytest tests/strategies/test_momentum_improvements.py::TestParameterSensitivity -v
pytest tests/strategies/test_momentum_improvements.py::TestVolumeConfirmation -v
pytest tests/strategies/test_momentum_improvements.py::TestTrailingStopLoss -v
```

### Phase 2: Integration Tests
```bash
pytest tests/strategies/test_momentum_improvements.py::TestIntegrationAndWalkForward -v
```

### Phase 3: Full Validation
```bash
python tests/strategies/run_improvement_tests.py --verbose --html
```

### Phase 4: Backtest Validation
```bash
python -m src.backtesting.run_backtest \
    --strategy momentum \
    --symbols AAPL MSFT GOOGL \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --initial-capital 10000
```

---

## 📝 Test Results Documentation

After running tests, document:

1. **Parameter Optimization Results**
   - Optimal histogram threshold
   - Best RSI midpoint
   - Ideal SMA period

2. **Volume Filter Impact**
   - Signal reduction percentage
   - Quality improvement metrics

3. **Market Regime Performance**
   - Trending market results
   - Choppy market results
   - Crash scenario results

4. **Walk-Forward Validation**
   - Train vs test performance
   - Confidence stability
   - Overfitting check

5. **Final Metrics Achievement**
   - Win rate: ___%
   - Total return: ___%
   - Sharpe ratio: ___
   - Max drawdown: ___%

---

## 🔗 Related Files

- **Test Suite**: `/tests/strategies/test_momentum_improvements.py`
- **Test Runner**: `/tests/strategies/run_improvement_tests.py`
- **Strategy Implementation**: `/src/strategies/momentum.py`
- **Backtest Engine**: `/src/backtesting/backtest.py`
- **Fix Documentation**: `/docs/fixes/OVERTRADING_FIX.md`

---

## 🎓 Next Steps

1. **Run Test Suite**
   ```bash
   python tests/strategies/run_improvement_tests.py --verbose
   ```

2. **Analyze Results**
   - Identify optimal parameters
   - Document performance across regimes

3. **Integrate Findings**
   - Update strategy with optimal params
   - Implement volume/trailing stop if beneficial

4. **Full Backtest Validation**
   - Run with optimal configuration
   - Validate target metrics achieved

5. **Paper Trading**
   - Test in live market conditions
   - Confirm metrics hold in real-time

---

**Status**: ✅ **TEST SUITE COMPLETE**
**Ready For**: Execution and parameter optimization
**Expected Outcome**: Identify optimal parameters to achieve target metrics
**Document Version**: 1.0
**Last Updated**: 2025-10-29
