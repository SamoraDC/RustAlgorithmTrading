# Week 3 Quick Start Guide - PRIORITY 1 FIXES

**Date**: 2025-10-29
**Status**: ⚠️ CRITICAL - Must Complete Before Any Other Work
**Timeline**: Day 15 (First Day of Week 3)

---

## 🚨 STOP! Read This First

Week 2 **FAILED** all 5 success criteria:
- Win Rate: 26.7% (target: 40-50%) ❌
- Total Return: -25.7% (target: +3-5%) ❌
- Sharpe Ratio: -0.378 (target: 0.5-0.8) ❌
- Total Trades: 15 (target: 30-40) ❌
- Profit Factor: 0.424 (target: >1.5) ❌

**Mean Reversion Catastrophe**: 0% win rate, -283% return, 63 losing trades

**Decision**: ⚠️ **CONDITIONAL GO** for Week 3 with mandatory fixes

---

## ✅ Priority 1 Fixes (MUST COMPLETE - 4 hours total)

### Fix #1: Stop-Loss Bypass (2 hours) 🚨 CRITICAL

**Problem**: Minimum holding period prevents immediate stop-loss exits
**Impact**: Losses amplified 2-3x (e.g., -1.8% → -4.74%)
**Solution**: Stop-loss exits bypass minimum holding period

**File**: `/src/strategies/momentum.py` (lines 195-232)

**Changes Needed**:
```python
# In generate_signals() method, around line 420

# BEFORE: Apply minimum holding period to ALL exits
if self.bars_held < min_holding_period:
    continue  # Skip exit signal

# AFTER: Bypass holding period for stop-loss ONLY
if self.bars_held < min_holding_period:
    # Allow immediate stop-loss exits
    if exit_reason not in ['stop_loss', 'catastrophic_stop_loss']:
        continue  # Skip only take-profit/technical exits
```

**Test**:
```bash
python tests/unit/test_stop_loss_bypass.py
```

**Expected**: Stop-loss exits occur within 1 bar of trigger

---

### Fix #2: Disable Mean Reversion Strategy (30 minutes) 🚨 CRITICAL

**Problem**: 0% win rate, -283% return (ALL 63 trades lost money)
**Impact**: CATASTROPHIC losses if left enabled
**Solution**: Disable completely, schedule full redesign for Week 5

**File**: `/src/utils/market_regime.py` (line ~85)

**Changes Needed**:
```python
# In select_strategy_for_regime() function

MarketRegime.RANGING: {
    'strategy': 'hold',              # Changed from 'mean_reversion'
    'direction': 'neutral',          # Changed from 'both'
    'stop_loss': 0.03,
    'position_size': 0.0,            # Changed from 0.15
    'enabled': False                 # Changed from True
},
MarketRegime.VOLATILE_RANGING: {
    'strategy': 'hold',              # Changed from 'mean_reversion'
    'direction': 'neutral',
    'stop_loss': 0.03,
    'position_size': 0.0,
    'enabled': False
}
```

**Add Comment**:
```python
# WEEK 3 CRITICAL FIX: Mean reversion strategy disabled due to 0% win rate
# and -283% return in Week 2 backtests (63 consecutive losing trades).
# Strategy requires complete redesign. Scheduled for Week 5 after momentum
# strategy is validated and profitable. DO NOT re-enable without full audit.
```

**Test**:
```bash
# Verify no mean reversion trades in backtest
python scripts/run_backtest.py --strategy momentum --symbols AAPL MSFT
# Should show 0 mean reversion trades in ranging markets
```

---

### Fix #3: Disable SHORT Signals (1 hour) 🚨 CRITICAL

**Problem**: 72.7% loss rate (8 of 11 SHORT trades lose money)
**Impact**: Drags down overall win rate by 15-20 percentage points
**Solution**: LONG-only trading until regime detection validates shorts

**File**: `/src/strategies/momentum.py` (line ~45)

**Changes Needed**:
```python
# In MomentumStrategy class __init__ parameters

# BEFORE:
allow_short: bool = True,

# AFTER:
allow_short: bool = False,  # WEEK 3 FIX: Disabled due to 72.7% loss rate
```

**Add Logging**:
```python
# In generate_signals() method, add near line 360

if not self.get_parameter('allow_short', False):
    logger.info(
        f"⚠️  SHORT signals DISABLED (Week 3 fix). "
        f"SHORT loss rate was 72.7% in Week 2. "
        f"Will re-enable in Week 3 Day 18+ with regime detection confirmation."
    )
```

**Documentation**:
Create `/docs/fixes/SHORT_SIGNALS_DISABLED.md`:
```markdown
# SHORT Signals Disabled - Week 3 Fix

## Rationale
SHORT signals in momentum strategy showed 72.7% loss rate in Week 2 backtests.

## Root Cause
Indicator lag causes SHORT entries at END of declines, right when oversold bounces begin.

## Timeline
- **Week 3 Day 15**: Disabled (LONG-only trading)
- **Week 3 Day 18+**: Re-enable with regime detection confirmation
- **Criteria for Re-Enable**: ADX >30, RSI <35, extended oversold confirmation

## Expected Impact
- Win rate improvement: +15-20 percentage points
- Total return improvement: +10-15%
- Reduced volatility and drawdown
```

**Test**:
```bash
python scripts/run_backtest.py --strategy momentum --allow-short false
# Should show 0 SHORT signals, only LONG entries
```

---

## 📊 Week 3 Success Criteria (Go/No-Go for Week 4)

After completing Priority 1 fixes, Week 3 targets:

| Metric | Week 2 Actual | Week 3 Target | Decision |
|--------|---------------|---------------|----------|
| **Win Rate** | 26.7% | 40-50% | ✅ GO if ≥40% |
| **Sharpe Ratio** | -0.378 | 0.5-0.8 | ⚠️ Caution if 0.3-0.5 |
| **Total Return** | -25.7% | +3-5% | ❌ HALT if <+1% |
| **Total Trades** | 15 | 25-35 | ⚠️ Need more signals |
| **Profit Factor** | 0.424 | >1.2 | ✅ GO if >1.2 |

**Decision Thresholds**:
- ✅ **APPROVE Week 4** if win rate ≥40% AND Sharpe ≥0.5
- ⚠️ **CONTINUE with Caution** if win rate 30-40%
- ❌ **HALT & REDESIGN** if win rate <30%

---

## 📅 Week 3 Timeline

### Day 15 (TODAY): Priority 1 Fixes
- [ ] Stop-loss bypass implementation (2 hours)
- [ ] Disable mean reversion (30 min)
- [ ] Disable SHORT signals (1 hour)
- [ ] Test all fixes (30 min)
- [ ] Run validation backtest (30 min)

### Day 16: Signal Quality
- [ ] Volume filter reduction: 1.05x → 1.02x
- [ ] Add confidence scoring to signals
- [ ] Enhanced logging for signal validation

### Day 17: Parameter Tuning
- [ ] MACD histogram threshold optimization
- [ ] RSI zone boundary testing
- [ ] Stop-loss level validation

### Day 18-19: Regime Detection
- [ ] Enhance MarketRegimeDetector
- [ ] Add confidence scoring to regimes
- [ ] Integrate trending market filter (ADX >25)

### Day 20: Validation & Go/No-Go
- [ ] Full backtest with all Week 3 fixes
- [ ] Metrics validation against success criteria
- [ ] **DECISION**: Approve Week 4, Continue with Caution, or HALT

---

## 🚀 Quick Commands

### Run Backtest (After Fixes)
```bash
cd /mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading

# Test simplified momentum (LONG-only)
python scripts/test_strategy2_simple.py

# Full backtest
python scripts/run_backtest.py \
  --strategy momentum \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --symbols AAPL MSFT GOOGL AMZN NVDA
```

### Run Tests
```bash
# Stop-loss bypass tests
pytest tests/unit/test_stop_loss_bypass.py -v

# RSI fix tests
pytest tests/unit/test_rsi_fix_week2.py -v

# Full test suite
pytest tests/ -v
```

### Check Results
```bash
# Latest backtest results
ls -lt data/backtest_results/*.json | head -5

# View specific backtest
cat data/backtest_results/strategy2_simplified.json | jq '.metrics'
```

---

## 📞 Coordination

### Memory Keys
```
swarm/week2/completion_report → Week 2 synthesis
swarm/planner/week3_plan → Week 3 implementation plan
swarm/week3/day15_fixes → Priority 1 fix results (update after completion)
```

### Hooks
```bash
# Before starting
npx claude-flow@alpha hooks pre-task --description "Week 3 Day 15: Priority 1 Fixes"

# After each fix
npx claude-flow@alpha hooks post-edit --file "momentum.py" --memory-key "swarm/week3/fix_stop_loss"

# After completion
npx claude-flow@alpha hooks post-task --task-id "week3_day15_priority1"
```

---

## ⚠️ What NOT to Do

### ❌ DO NOT:
1. **Skip Priority 1 fixes** - These are MANDATORY
2. **Re-enable mean reversion** - 0% win rate is unacceptable
3. **Re-enable SHORT signals** - 72.7% loss rate must be fixed first
4. **Proceed without testing** - Validate each fix individually
5. **Ignore Go/No-Go criteria** - If win rate <30%, HALT immediately

### ✅ DO:
1. **Complete fixes in order** - Stop-loss first, then mean reversion, then shorts
2. **Test after each fix** - Individual validation before integration
3. **Run full backtest** - After all 3 fixes complete
4. **Document results** - Update memory keys with findings
5. **Enforce Go/No-Go** - Strict criteria enforcement at Day 20

---

## 📚 Reference Documents

1. **Week 2 Completion Report**: `/docs/WEEK2_COMPLETION_REPORT.md`
   - Full analysis of Week 2 results
   - Root cause analysis for failures
   - Lessons learned and recommendations

2. **Implementation Roadmap**: `/docs/HIVE_IMPLEMENTATION_ROADMAP.md`
   - Week 2 actual results (updated)
   - Week 3 revised targets
   - Week 4 planning (conditional)

3. **Fix Documentation**:
   - `/docs/fixes/SHORT_SIGNAL_FIX.md` - 72.7% loss rate analysis
   - `/docs/fixes/VOLUME_FILTER_FIX.md` - 1.05x reduction
   - `/docs/fixes/MEAN_REVERSION_RANGING_FIX.md` - Catastrophic failure

4. **Backtest Results**:
   - `/data/backtest_results/strategy2_simplified.json` - Oct 29 results
   - `/data/backtest_results/strategy3_mean_reversion.json` - Catastrophic failure

---

## 🎯 Success Indicators

After completing Priority 1 fixes, you should see:

✅ **Immediate Improvements**:
- Stop-loss exits occur within 1-2 bars (not 10+ bars)
- Average loss <2% (not 4%+)
- No mean reversion trades (0 ranging market trades)
- No SHORT signals (100% LONG-only)

✅ **Backtest Validation**:
- Total trades: 20-30 (more than Week 2's 15)
- Win rate: 35-45% (improvement from 26.7%)
- Sharpe ratio: 0.3-0.6 (positive, not negative)
- Total return: +1-3% (positive, not -25%)

✅ **Risk Management**:
- Max drawdown: <20%
- Profit factor: >1.0 (making money)
- Average loss capped at stop-loss level
- No catastrophic trades (-5%+ losses)

---

## 🚨 Emergency Contacts

If any fix causes build breaks or test failures:

1. **Revert changes immediately**
2. **Document the issue** in memory
3. **Notify team via hooks**
4. **Escalate if blocking** (cannot proceed)

**Escalation Path**:
- P0 (Blocker): All fixes failing → HALT Week 3
- P1 (High): One fix failing → Debug and retry
- P2 (Medium): Tests failing → Fix tests, not code
- P3 (Low): Documentation issues → Update docs

---

## ✅ Completion Checklist

Before proceeding to Day 16:

- [ ] Stop-loss bypass implemented and tested
- [ ] Mean reversion strategy disabled and verified
- [ ] SHORT signals disabled and verified
- [ ] All unit tests passing
- [ ] Validation backtest run
- [ ] Results documented in memory
- [ ] Post-task hooks executed
- [ ] Team notified of completion

**Expected Time**: 4 hours
**Actual Time**: _____ hours
**Blockers**: _____________________
**Next Steps**: Proceed to Day 16 (Signal Quality Improvements)

---

**Status**: 🔴 **READY TO START**
**Owner**: Coder + Reviewer Agents
**Coordination**: Via swarm memory and hooks
**Report Back**: Update `swarm/week3/day15_fixes` memory key with results

---

*Generated by Strategic Planner Agent - Hive Mind Week 3*
*Last Updated: 2025-10-29*
