# Dependency Check Script Fix

## Problem

The dependency check script (`scripts/check_dependencies.sh`) was incorrectly treating optional dependencies as required, causing the script to fail when optional tools like `jq` were not installed.

## Root Cause

The script had two issues:

1. **No distinction between required and optional dependencies** - All dependencies were treated equally, with missing optional dependencies contributing to failure conditions.

2. **Arithmetic expression issue with `set -euo pipefail`** - Using `((VAR++))` syntax caused the script to exit prematurely when the variable was 0, due to the strict error handling in bash.

## Solution Implemented

### 1. Separate Tracking for Required vs Optional Dependencies

Added counters to track:
- `REQUIRED_DEPS` / `REQUIRED_MET` - Required dependencies count
- `OPTIONAL_DEPS` / `OPTIONAL_MET` - Optional dependencies count
- `ERRORS` - Required dependency failures (causes script to fail)
- `WARNINGS` - Optional dependency warnings (does not cause failure)

### 2. New Logging Functions

Created specialized logging functions:
```bash
log_success_required()  # For required dependencies that are present
log_success_optional()  # For optional dependencies that are present
log_warning_optional()  # For optional dependencies that are missing
log_error()             # For required dependencies that are missing
```

### 3. Fixed Arithmetic Operations

Changed from:
```bash
((REQUIRED_MET++))  # Can return exit code 1 with set -euo pipefail
```

To:
```bash
REQUIRED_MET=$((REQUIRED_MET + 1))  # Always returns 0
```

### 4. Enhanced Summary Report

The summary now shows:
- **Required Dependencies**: X/Y met (fails if any missing)
- **Optional Dependencies**: X/Y met (warns if any missing, doesn't fail)
- **Overall Status**: PASS or FAIL based only on required dependencies
- **Clear messaging**: Distinguishes between errors (required) and warnings (optional)

## Example Output

### With Missing Optional Dependencies (PASSES)

```
Required Dependencies:
  ✓ All required dependencies met (14/14)

Optional Dependencies:
  ⚠ 1 optional dependencies missing (3/4 met)
  These are recommended but not required for basic operation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ DEPENDENCY CHECK PASSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Note: 1 optional dependencies missing (non-critical)
```

### With Missing Required Dependencies (FAILS)

```
Required Dependencies:
  ✗ Missing required dependencies (5/14 met)

Optional Dependencies:
  ⚠ 1 optional dependencies missing (3/4 met)
  These are recommended but not required for basic operation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ DEPENDENCY CHECK FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Errors: 10
Warnings: 2 (optional)

Please fix the errors above before starting the system.
```

## Dependencies Classification

### Required Dependencies
- **System Commands**: python3, pip3, cargo, curl
- **Python Version**: >= 3.8
- **Python Packages**: fastapi, uvicorn, websockets, pydantic, duckdb, loguru, psutil, numpy, pandas

### Optional Dependencies
- **System Commands**: node, npm, jq, uv (Python package manager)
- **Dashboard**: React dashboard and node_modules (for web UI)
- **Rust Binaries**: Pre-built binaries (will be built if missing)

## Testing

To test the script:
```bash
# Run the full dependency check
bash scripts/check_dependencies.sh

# Expected exit codes:
# - 0: All required dependencies met (optional may be missing)
# - 1: One or more required dependencies missing
```

## Impact

This fix ensures:
1. ✅ **System can start** even if optional tools (jq, node, npm) are missing
2. ✅ **Clear feedback** about what is required vs recommended
3. ✅ **No false failures** from missing optional dependencies
4. ✅ **Proper exit codes** for CI/CD integration
5. ✅ **Better UX** with color-coded output and clear messages

## Files Modified

- `/scripts/check_dependencies.sh` - Complete rewrite of dependency checking logic

## Related Issues

- Missing `jq` no longer blocks system startup
- Missing `node`/`npm` only warns (dashboard is optional)
- Missing `uv` only warns (faster package manager is optional)
