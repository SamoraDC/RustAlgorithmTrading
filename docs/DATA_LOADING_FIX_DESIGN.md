# Data Loading Issue - Complete Fix Design

**Status**: Design Complete - Ready for Implementation
**Date**: 2025-10-22
**Priority**: High - Blocks Backtesting

---

## Executive Summary

The backtesting system fails at line 183 of `data_handler.py` with "No data loaded" because historical data files are missing from `data/historical/` directory. While a data download script exists (`scripts/download_historical_data.py`), it's never automatically invoked, leaving the system without required data.

**Solution**: Implement automatic data availability checking and downloading as a pre-flight step in the autonomous trading system.

---

## Root Cause Analysis

### Current Flow (Broken)
```
autonomous_trading_system.sh
  └─> run_backtesting()
      └─> HistoricalDataHandler(data_dir='data/historical')
          └─> _load_data()
              └─> No files found (data/historical/ is empty)
              └─> Warning logged but continues
              └─> Line 183: No data in symbol_data dict
              └─> FAILURE: "No data loaded for {symbol}"
```

### Missing Component
```
NO DATA PRE-CHECK STEP EXISTS
  - autonomous_trading_system.sh doesn't verify data availability
  - HistoricalDataHandler creates empty directory but doesn't download
  - download_historical_data.py exists but requires manual invocation
```

---

## Architecture Design

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│           AUTONOMOUS TRADING SYSTEM                          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 0: DATA AVAILABILITY CHECK (NEW)                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │ check_and_download_data.sh                         │    │
│  │  1. Load config from .env                          │    │
│  │  2. Check data/historical/ for required symbols    │    │
│  │  3. If missing: invoke download_historical_data.py │    │
│  │  4. Validate downloaded data integrity             │    │
│  │  5. Report status                                  │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: BACKTESTING (EXISTING - ENHANCED)                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │ HistoricalDataHandler (ENHANCED)                   │    │
│  │  - Better error messages                           │    │
│  │  - Data validation before backtesting              │    │
│  │  - Clear instructions on how to fix               │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Design

### 1. Data Download Pre-Check Script

**File**: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/check_and_download_data.sh`

**Purpose**: Automated data availability verification and download orchestration

**Functions**:

```bash
check_data_exists() {
    # Input: symbols array, data_dir path
    # Output: 0 if all data exists, 1 if any missing
    # Logic:
    #   - For each symbol in symbols:
    #     - Check if {symbol}.parquet or {symbol}.csv exists in data_dir
    #     - If exists: validate file size > 0
    #   - Return 0 only if all symbols have data
}

download_missing_data() {
    # Input: symbols array, start_date, end_date
    # Output: 0 on success, 1 on failure
    # Logic:
    #   - Activate Python environment
    #   - Call download_historical_data.py with parameters:
    #     --symbols ${SYMBOLS[@]}
    #     --start ${START_DATE}
    #     --end ${END_DATE}
    #     --output-dir data/historical
    #     --timeframe 1Day
    #   - Monitor exit code
    #   - Return result
}

validate_downloaded_data() {
    # Input: symbols array, data_dir path
    # Output: 0 if valid, 1 if invalid
    # Logic:
    #   - For each symbol:
    #     - Check file exists
    #     - Check file size > 1KB (has actual data)
    #     - Quick validation: can read first row
    #   - Return overall result
}

main() {
    # Load configuration from .env
    # Check if data exists
    # If missing: download data
    # Validate downloaded data
    # Report results
}
```

**Integration Point**: Called by `autonomous_trading_system.sh` before backtesting

---

### 2. Enhanced Data Handler

**File**: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/backtesting/data_handler.py`

**Modifications**:

#### Change 1: Enhanced Directory Creation (Lines 59-64)
```python
# CURRENT:
if not self.data_dir.exists():
    logger.warning(f"Data directory does not exist: {self.data_dir}")
    self.data_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created data directory: {self.data_dir}")

# ENHANCED:
if not self.data_dir.exists():
    logger.error(f"Data directory does not exist: {self.data_dir}")
    logger.error(f"SOLUTION: Run data download script:")
    logger.error(f"  cd {Path.cwd()}")
    logger.error(f"  bash scripts/check_and_download_data.sh")
    raise FileNotFoundError(
        f"Historical data directory not found: {self.data_dir}\n"
        f"Run: bash scripts/check_and_download_data.sh to download data"
    )
```

#### Change 2: Better File Not Found Messages (Lines 121-126)
```python
# CURRENT:
else:
    logger.warning(
        f"No data file found for {symbol} "
        f"(checked: {parquet_path}, {csv_path})"
    )
    continue

# ENHANCED:
else:
    logger.error(f"No data file found for {symbol}")
    logger.error(f"  Checked: {parquet_path}")
    logger.error(f"  Checked: {csv_path}")
    logger.error(f"")
    logger.error(f"SOLUTION: Download historical data:")
    logger.error(f"  python scripts/download_historical_data.py \\")
    logger.error(f"    --symbols {symbol} \\")
    logger.error(f"    --start 2024-01-01 \\")
    logger.error(f"    --end {datetime.now().strftime('%Y-%m-%d')} \\")
    logger.error(f"    --output-dir data/historical")

    # Don't continue - this is a fatal error
    raise FileNotFoundError(
        f"Historical data file not found for {symbol}. "
        f"Run data download script first."
    )
```

#### Change 3: Post-Load Validation (After Line 171)
```python
# NEW CODE AFTER LINE 171:
def _validate_all_data_loaded(self):
    """Validate that data was successfully loaded for all symbols."""
    if not self.symbol_data:
        raise ValueError(
            "No data loaded for any symbols. Check that:\n"
            "1. Data files exist in data directory\n"
            "2. Files are not empty or corrupted\n"
            "3. Date range overlaps with available data\n"
            "Run: bash scripts/check_and_download_data.sh"
        )

    missing_symbols = set(self.symbols) - set(self.symbol_data.keys())
    if missing_symbols:
        logger.warning(
            f"Data loaded for {len(self.symbol_data)}/{len(self.symbols)} symbols. "
            f"Missing: {missing_symbols}"
        )

# CALL in __init__ after line 84:
self._load_data()
self._validate_all_data_loaded()  # NEW
```

---

### 3. Updated Autonomous Trading System

**File**: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/autonomous_trading_system.sh`

**Modifications**:

#### Change 1: New Function Before run_backtesting()
```bash
# INSERT AFTER LINE 157 (after build_rust_services function)

################################################################################
# Data Availability Check
################################################################################

check_historical_data() {
    log_info "=========================================="
    log_info "PHASE 0: DATA AVAILABILITY CHECK"
    log_info "=========================================="

    log_info "Checking for historical data..."

    # Run data check script
    if bash "$SCRIPT_DIR/check_and_download_data.sh"; then
        log_success "Historical data verified and ready"
        return 0
    else
        log_error "Historical data check failed"
        log_error "Please review the logs and ensure data is available"
        return 1
    fi
}
```

#### Change 2: Update Main Flow (Lines 669-678)
```bash
# CURRENT:
"full")
    # Run complete pipeline
    if run_backtesting && run_simulation; then
        log_success "Validation passed - proceeding to paper trading"
        run_paper_trading
    else
        log_error "Validation failed - aborting paper trading"
        exit 1
    fi
    ;;

# ENHANCED:
"full")
    # Run complete pipeline with data check
    if check_historical_data && run_backtesting && run_simulation; then
        log_success "Validation passed - proceeding to paper trading"
        run_paper_trading
    else
        log_error "Validation failed - aborting paper trading"
        exit 1
    fi
    ;;
```

#### Change 3: Update backtest-only Mode (Lines 681-683)
```bash
# CURRENT:
"backtest-only")
    run_backtesting
    ;;

# ENHANCED:
"backtest-only")
    check_historical_data && run_backtesting
    ;;
```

---

### 4. Configuration Updates

#### File: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/config/config.py`

**Add New DataConfig Class** (After line 47):

```python
class DataConfig(BaseModel):
    """Historical data configuration"""
    data_dir: str = Field(default="data/historical", description="Data directory path")
    default_symbols: list[str] = Field(
        default=["AAPL", "MSFT", "GOOGL"],
        description="Default symbols to download"
    )
    start_date: str = Field(default="2024-01-01", description="Data start date")
    end_date: str = Field(default="2025-10-21", description="Data end date")
    timeframe: str = Field(default="1Day", description="Data timeframe")
    auto_download: bool = Field(default=True, description="Auto-download missing data")
    cache_enabled: bool = Field(default=True, description="Enable data caching")
```

**Update TradingConfig Class** (Line 49-56):

```python
class TradingConfig(BaseModel):
    """Complete trading system configuration"""
    alpaca: AlpacaConfig
    data: DataConfig = Field(default_factory=DataConfig)  # NEW
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
```

**Update _load_config Method** (After line 101):

```python
data_config = DataConfig(
    data_dir=os.getenv("DATA_DIR", "data/historical"),
    default_symbols=os.getenv("DEFAULT_SYMBOLS", "AAPL,MSFT,GOOGL").split(","),
    start_date=os.getenv("DATA_START_DATE", "2024-01-01"),
    end_date=os.getenv("DATA_END_DATE", "2025-10-21"),
    timeframe=os.getenv("DATA_TIMEFRAME", "1Day"),
    auto_download=os.getenv("DATA_AUTO_DOWNLOAD", "true").lower() == "true"
)
```

#### File: `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/.env`

**Add Data Configuration** (After line 3):

```bash
# Data Configuration
DATA_DIR=data/historical
DEFAULT_SYMBOLS=AAPL,MSFT,GOOGL
DATA_START_DATE=2024-01-01
DATA_END_DATE=2025-10-21
DATA_TIMEFRAME=1Day
DATA_AUTO_DOWNLOAD=true
```

---

## Implementation Steps

### Step 1: Create Data Pre-Check Script
1. Create `scripts/check_and_download_data.sh`
2. Implement data checking logic
3. Implement download orchestration
4. Add validation functions
5. Make executable: `chmod +x scripts/check_and_download_data.sh`

### Step 2: Enhance Data Handler
1. Modify `src/backtesting/data_handler.py`
2. Update error messages (lines 59-64, 121-126)
3. Add validation method
4. Add post-load validation call

### Step 3: Update Autonomous System
1. Modify `scripts/autonomous_trading_system.sh`
2. Add `check_historical_data()` function
3. Update main flow to call data check
4. Update all modes that use backtesting

### Step 4: Update Configuration
1. Modify `config/config.py`
2. Add `DataConfig` class
3. Update `TradingConfig` to include data config
4. Update `.env` with data variables

### Step 5: Testing
1. Test with empty data directory
2. Verify auto-download works
3. Test with existing data (should skip)
4. Test error handling
5. Run full autonomous system end-to-end

---

## Testing Strategy

### Test Case 1: Empty Data Directory
```bash
# Setup
rm -rf data/historical/*

# Execute
bash scripts/autonomous_trading_system.sh --mode=backtest-only

# Expected Result
- check_and_download_data.sh detects missing data
- Automatically invokes download_historical_data.py
- Downloads AAPL, MSFT, GOOGL data
- Backtesting proceeds successfully
```

### Test Case 2: Partial Data Available
```bash
# Setup
rm -f data/historical/MSFT.parquet
rm -f data/historical/GOOGL.parquet

# Execute
bash scripts/check_and_download_data.sh

# Expected Result
- Detects MSFT and GOOGL missing
- Downloads only missing symbols
- Validates all data present
```

### Test Case 3: Data Validation Failure
```bash
# Setup
touch data/historical/AAPL.parquet  # Create empty file

# Execute
bash scripts/check_and_download_data.sh

# Expected Result
- Detects invalid AAPL data (size = 0)
- Re-downloads AAPL data
- Validates successful download
```

### Test Case 4: API Failure Handling
```bash
# Setup
export ALPACA_API_KEY="invalid_key"

# Execute
bash scripts/check_and_download_data.sh

# Expected Result
- Download fails with clear error message
- Script exits with error code 1
- Autonomous system stops before backtesting
```

### Test Case 5: Existing Valid Data
```bash
# Setup
# Data already exists from previous download

# Execute
bash scripts/check_and_download_data.sh

# Expected Result
- Quickly validates existing data
- Skips download (logs "Data already available")
- Proceeds to backtesting immediately
```

---

## File Modification Summary

| File | Action | Lines Modified | Purpose |
|------|--------|----------------|---------|
| `scripts/check_and_download_data.sh` | CREATE | N/A | Data availability check and auto-download |
| `src/backtesting/data_handler.py` | MODIFY | 59-64, 121-126, +20 | Enhanced error messages and validation |
| `scripts/autonomous_trading_system.sh` | MODIFY | +30, 669-678, 681-683 | Add data check phase |
| `config/config.py` | MODIFY | +30 | Add DataConfig class |
| `.env` | MODIFY | +6 | Add data configuration variables |

**Total Files**: 5
**New Files**: 1
**Modified Files**: 4

---

## Success Criteria

1. **Automated Data Download**: System automatically downloads missing data without manual intervention
2. **Clear Error Messages**: When data missing, user sees actionable error with exact command to run
3. **Data Validation**: System validates data integrity before proceeding to backtesting
4. **Zero Manual Steps**: Full autonomous system runs without requiring manual data setup
5. **Error Recovery**: System handles API failures gracefully with clear error messages
6. **Performance**: Data check completes in <5 seconds when data exists
7. **Idempotent**: Running multiple times doesn't re-download existing data

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | Download fails | Implement retry with exponential backoff (already in download script) |
| Invalid API credentials | Download fails | Early validation of credentials in check script |
| Disk space full | Download fails | Check available disk space before download |
| Network failure | Download fails | Clear error message with retry instructions |
| Corrupted downloads | Backtesting fails | Validate data integrity post-download |
| Date range issues | No data returned | Use default date range (last 365 days) as fallback |

---

## Dependencies

- **Python Packages**: pandas, pyarrow, alpaca-py (already in requirements.txt)
- **Environment Variables**: ALPACA_API_KEY, ALPACA_SECRET_KEY (already configured)
- **Disk Space**: ~10-50 MB per symbol per year
- **Network**: Internet connection for Alpaca API access

---

## Future Enhancements

1. **Incremental Updates**: Download only new data since last update
2. **Multiple Timeframes**: Support 1Hour, 5Min data downloads
3. **Data Quality Checks**: More comprehensive validation (gaps, outliers)
4. **Alternative Data Sources**: Support for other data providers
5. **Data Caching**: Redis/SQLite cache for faster access
6. **Parallel Downloads**: Download multiple symbols concurrently
7. **Web UI**: Dashboard showing data availability status

---

## Implementation Ready

All design specifications are complete and ready for implementation. The coder agent can now proceed with creating and modifying files according to this design document.

**Next Steps**:
1. Coder agent implements changes
2. Test each component individually
3. Integration testing
4. Documentation updates
5. Deployment

---

**Design Document Version**: 1.0
**Last Updated**: 2025-10-22
**Status**: Ready for Implementation
