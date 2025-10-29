# Week 3 Priority 2: RSI Zone Tightening to Reduce Overtrading

## Problem Identification (Week 2 Results)

**Overtrading Symptoms:**
- Total trades: **69** (73% above target of 40)
- Win rate: **13.04%** (impacted by marginal signals)
- Sharpe ratio: **-0.54** (negative due to overtrading)
- Issue: RSI zones 55-85 (LONG) and 15-45 (SHORT) too wide

**Root Cause:**
The 30-point RSI zones (55-85 and 15-45) allowed entries during weak momentum periods:
- RSI 55-60: Weak bullish signals (just above neutral)
- RSI 80-85: Overextended signals (high reversal risk)
- RSI 15-20: Oversold bounce risk (weak bearish conviction)
- RSI 40-45: Weak bearish signals (just below neutral)

## Solution: Tightened RSI Zones (Week 3)

### New RSI Thresholds

**LONG Entry Zone:**
```python
# Week 2: RSI 55-85 (30-point range)
# Week 3: RSI 60-80 (20-point range) - 33% reduction
rsi_long_cond = current['rsi'] > 60 and current['rsi'] < 80
```

**SHORT Entry Zone:**
```python
# Week 2: RSI 15-45 (30-point range)
# Week 3: RSI 20-40 (20-point range) - 33% reduction
rsi_short_cond = current['rsi'] < 40 and current['rsi'] > 20
```

### Rationale for Zone Selection

**LONG Zone (60-80):**
- **Lower bound 60**: Filters weak bullish signals below 60 (marginal momentum)
- **Upper bound 80**: Prevents overextended entries near overbought (85+)
- **Sweet spot**: Captures strong sustained uptrends without extremes

**SHORT Zone (20-40):**
- **Lower bound 20**: Prevents oversold bounce risk below 20
- **Upper bound 40**: Filters weak bearish signals above 40 (marginal momentum)
- **Sweet spot**: Captures strong sustained downtrends without extremes

## Expected Impact

### Trade Count Reduction
- **Week 2**: 69 trades (30-point zones)
- **Week 3 Target**: 35-45 trades (20-point zones)
- **Reduction**: ~35% fewer trades (-24 trades)

### Quality Metrics Improvement

**Win Rate:**
- Week 2: 13.04% (9 wins / 69 trades)
- Week 3 Target: 20-25% (filtering marginal signals)
- Improvement: +7-12 percentage points

**Sharpe Ratio:**
- Week 2: -0.54 (negative due to overtrading)
- Week 3 Target: 0.0 to 0.5 (reduced overtrading penalty)
- Improvement: +0.5 to 1.0 points

**Average Trade Quality:**
- Fewer marginal signals (RSI 55-60, 40-45)
- Stronger momentum confirmation
- Better risk/reward on remaining trades

## Implementation Details

### File Modified
- `/src/strategies/momentum.py`
- Lines 361-365 (LONG zone)
- Lines 406-406 (SHORT zone)

### Code Changes

**LONG Entry Condition:**
```python
# WEEK 3 FIX: Tightened RSI zones to reduce overtrading
# Week 2: 55-85 LONG zone → 69 trades (too many, 73% above target)
# Week 3: 60-80 LONG zone → Target 35-45 trades (tighter thresholds)
# Rationale: Narrower zone captures stronger momentum, filters marginal signals
rsi_long_cond = current['rsi'] > 60 and current['rsi'] < 80  # Tightened bullish zone
```

**SHORT Entry Condition:**
```python
# WEEK 3 FIX: Tightened RSI zones to reduce overtrading
# Week 2: 15-45 SHORT zone → 69 trades (too many, 73% above target)
# Week 3: 20-40 SHORT zone → Target 35-45 trades (tighter thresholds)
# Rationale: Narrower zone captures stronger momentum, filters marginal signals
rsi_short_cond = current['rsi'] < 40 and current['rsi'] > 20  # Tightened bearish zone
```

### Documentation Updates
- Updated class docstring with Week 3 RSI zones
- Added RSI entry zones section to parameter documentation
- Noted expected trade count and quality improvements

## Testing Plan

### Validation Steps

1. **Backtest with New Zones:**
   ```bash
   python scripts/run_backtest.py --strategy momentum --start 2024-01-01 --end 2024-12-31
   ```

2. **Compare Trade Counts:**
   - Week 2 baseline: 69 trades
   - Week 3 target: 35-45 trades
   - Verify ~35% reduction

3. **Analyze Signal Quality:**
   - Check RSI distribution at entry points
   - Confirm entries clustered in 60-80 (LONG) and 20-40 (SHORT)
   - Verify no entries outside new zones

4. **Performance Metrics:**
   - Win rate: Should increase from 13.04% to 20-25%
   - Sharpe ratio: Should improve from -0.54 to positive territory
   - Average P&L per trade: Should improve

### Success Criteria

✅ **Trade Count**: 35-45 trades (vs 69 in Week 2)
✅ **Win Rate**: >20% (vs 13.04% in Week 2)
✅ **Sharpe Ratio**: >0.0 (vs -0.54 in Week 2)
✅ **Signal Quality**: Entries concentrated in tightened zones
✅ **Overtrading**: Eliminated (trade count within target range)

## Alternative Approaches Considered

### Option 1: Configurable RSI Zones (Future Enhancement)
```python
def __init__(
    self,
    rsi_long_min: float = 60,   # Configurable lower LONG bound
    rsi_long_max: float = 80,   # Configurable upper LONG bound
    rsi_short_min: float = 20,  # Configurable lower SHORT bound
    rsi_short_max: float = 40,  # Configurable upper SHORT bound
    ...
):
```

**Pros:**
- Allows optimization via parameter sweeps
- Adapts to different market conditions
- Enables A/B testing of zone widths

**Cons:**
- Adds complexity
- Requires additional testing
- May lead to overfitting

**Decision**: Implement in Phase 2 after validating fixed zones

### Option 2: Dynamic RSI Zones (Advanced)
- Adjust zones based on market volatility (VIX)
- Tighten zones in low volatility (reduce noise)
- Widen zones in high volatility (capture swings)

**Decision**: Consider for Phase 3 after static zones proven

## Coordination & Memory

**Hooks Executed:**
- Pre-task: `npx claude-flow@alpha hooks pre-task --description "Tighten RSI zones"`
- Post-edit: `npx claude-flow@alpha hooks post-edit --file "momentum.py" --memory-key "swarm/week3/rsi_tighten"`
- Post-task: `npx claude-flow@alpha hooks post-task --task-id "rsi_tighten_week3"`

**Memory Key**: `swarm/week3/rsi_tighten`

**Coordination Status**:
- Task: RSI zone tightening
- Status: Complete
- Files modified: `src/strategies/momentum.py`
- Documentation: `docs/fixes/WEEK3_RSI_TIGHTENING.md`

## Next Steps

1. **Immediate**: Run backtest to validate trade count reduction
2. **Week 3 Priority 3**: Adjust take-profit from 3% to 2.5% (if needed)
3. **Week 4**: Consider making RSI zones configurable parameters
4. **Week 5**: Explore dynamic zone adjustment based on volatility

## References

- Week 2 Results: 69 trades, 13.04% win rate, -0.54 Sharpe ratio
- Target Metrics: 35-45 trades, >20% win rate, >0.0 Sharpe ratio
- RSI Theory: Strong trends occur in 60-80 (bull) and 20-40 (bear) zones
- Overtrading Impact: Excess trades dilute win rate and increase transaction costs
