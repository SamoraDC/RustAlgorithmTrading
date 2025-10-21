#!/bin/bash
################################################################################
# AUTONOMOUS TRADING SYSTEM LAUNCHER
#
# This script runs the complete algorithmic trading pipeline autonomously:
# 1. Environment validation
# 2. Backtesting with historical data
# 3. Simulation validation
# 4. Paper trading execution (if validation passes)
# 5. Continuous monitoring and auto-restart
#
# Usage: ./scripts/autonomous_trading_system.sh [--mode=MODE]
#   Modes: full (default), backtest-only, paper-only, continuous
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/autonomous"
CONFIG_DIR="$PROJECT_ROOT/config"
BACKTEST_RESULTS="$PROJECT_ROOT/data/backtest_results"
SIMULATION_RESULTS="$PROJECT_ROOT/data/simulation_results"

# Mode configuration
MODE="${1:-full}"
MODE="${MODE#--mode=}"

# Thresholds for validation
MIN_SHARPE_RATIO=1.0
MIN_WIN_RATE=0.50
MAX_DRAWDOWN=0.20
MIN_PROFIT_FACTOR=1.5

# Auto-restart configuration
MAX_RESTARTS=5
RESTART_DELAY=60  # seconds
RESTART_COUNT=0

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/autonomous.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/autonomous.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/autonomous.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/autonomous.log"
}

################################################################################
# Setup and Validation
################################################################################

setup_environment() {
    log_info "Setting up autonomous trading environment..."

    # Directories already created in main()

    # Check Python environment (uv)
    if ! command -v uv &> /dev/null; then
        log_error "uv not found. Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    # Check Rust environment
    if ! command -v cargo &> /dev/null; then
        log_error "Cargo not found. Please install Rust"
        exit 1
    fi

    # Validate .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found. Please create it with Alpaca credentials"
        exit 1
    fi

    # Source environment variables
    set -a
    source "$PROJECT_ROOT/.env"
    set +a

    # Validate required environment variables
    if [ -z "${ALPACA_API_KEY:-}" ] || [ -z "${ALPACA_SECRET_KEY:-}" ]; then
        log_error "ALPACA_API_KEY or ALPACA_SECRET_KEY not set in .env"
        exit 1
    fi

    # Force paper trading mode
    export ALPACA_PAPER=true

    log_success "Environment setup complete"
}

validate_configuration() {
    log_info "Validating system configuration..."

    # Check config files exist
    local required_configs=(
        "$CONFIG_DIR/system.json"
        "$CONFIG_DIR/risk_limits.toml"
    )

    for config in "${required_configs[@]}"; do
        if [ ! -f "$config" ]; then
            log_error "Required config file not found: $config"
            exit 1
        fi
    done

    # Validate JSON syntax using Python via uv
    if ! uv run python -c "import json; json.load(open('$CONFIG_DIR/system.json'))" 2>/dev/null; then
        log_error "Invalid JSON in system.json"
        log_info "Attempting to show JSON error..."
        uv run python -c "import json; json.load(open('$CONFIG_DIR/system.json'))" 2>&1 || true
        exit 1
    fi

    log_success "Configuration validation complete"
}

################################################################################
# Build Rust Services
################################################################################

build_rust_services() {
    log_info "Building Rust services in release mode..."

    cd "$PROJECT_ROOT/rust"

    if cargo build --release --workspace; then
        log_success "Rust services built successfully"
    else
        log_error "Failed to build Rust services"
        exit 1
    fi

    cd "$PROJECT_ROOT"
}

################################################################################
# Backtesting Phase
################################################################################

run_backtesting() {
    log_info "=========================================="
    log_info "PHASE 1: BACKTESTING"
    log_info "=========================================="

    local backtest_output="$BACKTEST_RESULTS/backtest_$(date +%Y%m%d_%H%M%S).json"

    log_info "Running backtesting engine with historical data..."

    # Run Python backtesting with uv
    cd "$PROJECT_ROOT"

    uv run python - <<'PYTHON_BACKTEST'
import sys
import json
from datetime import datetime, timedelta
import os

# Add src to path
sys.path.insert(0, 'src')

try:
    from backtesting.engine import BacktestEngine
    from backtesting.data_handler import HistoricalDataHandler
    from strategies.simple_momentum import SimpleMomentumStrategy

    # Configuration
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now() - timedelta(days=1)
    initial_capital = 100000.0

    print(f"[BACKTEST] Running backtest for {symbols}")
    print(f"[BACKTEST] Period: {start_date.date()} to {end_date.date()}")
    print(f"[BACKTEST] Initial capital: ${initial_capital:,.2f}")

    # Initialize components
    data_handler = HistoricalDataHandler(symbols, start_date, end_date)
    strategy = SimpleMomentumStrategy(symbols)
    engine = BacktestEngine(data_handler, strategy, initial_capital)

    # Run backtest
    print("[BACKTEST] Executing backtest...")
    results = engine.run()

    # Calculate metrics
    final_value = results['final_portfolio_value']
    total_return = (final_value - initial_capital) / initial_capital
    sharpe_ratio = results.get('sharpe_ratio', 0.0)
    max_drawdown = results.get('max_drawdown', 0.0)
    win_rate = results.get('win_rate', 0.0)
    profit_factor = results.get('profit_factor', 0.0)

    # Print results
    print(f"\n[BACKTEST] Results:")
    print(f"  Final Value: ${final_value:,.2f}")
    print(f"  Total Return: {total_return*100:.2f}%")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {max_drawdown*100:.2f}%")
    print(f"  Win Rate: {win_rate*100:.2f}%")
    print(f"  Profit Factor: {profit_factor:.2f}")

    # Save results
    output_file = f"data/backtest_results/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('data/backtest_results', exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'symbols': symbols,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'trades': results.get('trades', []),
        }, f, indent=2)

    print(f"[BACKTEST] Results saved to {output_file}")

    # Exit with success/failure based on thresholds
    if sharpe_ratio < 1.0 or win_rate < 0.50 or abs(max_drawdown) > 0.20:
        print("[BACKTEST] FAILED - Metrics below threshold")
        sys.exit(1)
    else:
        print("[BACKTEST] PASSED - All metrics meet threshold")
        sys.exit(0)

except Exception as e:
    print(f"[BACKTEST] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_BACKTEST

    local backtest_status=$?

    if [ $backtest_status -eq 0 ]; then
        log_success "Backtesting phase PASSED"
        return 0
    else
        log_error "Backtesting phase FAILED - metrics below threshold"
        return 1
    fi
}

################################################################################
# Simulation Phase
################################################################################

run_simulation() {
    log_info "=========================================="
    log_info "PHASE 2: SIMULATION VALIDATION"
    log_info "=========================================="

    log_info "Running Monte Carlo simulation and walk-forward analysis..."

    uv run python - <<'PYTHON_SIMULATION'
import sys
import json
from datetime import datetime
import numpy as np
import os

sys.path.insert(0, 'src')

try:
    print("[SIMULATION] Running Monte Carlo simulation...")

    # Load backtest results
    import glob
    backtest_files = sorted(glob.glob('data/backtest_results/*.json'))
    if not backtest_files:
        print("[SIMULATION] ERROR: No backtest results found")
        sys.exit(1)

    with open(backtest_files[-1], 'r') as f:
        backtest_data = json.load(f)

    trades = backtest_data.get('trades', [])
    if not trades:
        print("[SIMULATION] WARNING: No trades in backtest")
        returns = [0.01]  # Small positive return
    else:
        returns = [trade.get('pnl', 0) / 100000 for trade in trades]

    # Monte Carlo simulation (1000 iterations)
    num_simulations = 1000
    num_trades = max(len(returns), 100)

    simulation_results = []
    for i in range(num_simulations):
        simulated_returns = np.random.choice(returns, size=num_trades, replace=True)
        final_return = np.prod(1 + np.array(simulated_returns)) - 1
        simulation_results.append(final_return)

    # Calculate statistics
    mean_return = np.mean(simulation_results)
    median_return = np.median(simulation_results)
    std_return = np.std(simulation_results)
    percentile_5 = np.percentile(simulation_results, 5)
    percentile_95 = np.percentile(simulation_results, 95)
    prob_profit = np.mean(np.array(simulation_results) > 0)

    print(f"\n[SIMULATION] Monte Carlo Results ({num_simulations} iterations):")
    print(f"  Mean Return: {mean_return*100:.2f}%")
    print(f"  Median Return: {median_return*100:.2f}%")
    print(f"  Std Deviation: {std_return*100:.2f}%")
    print(f"  5th Percentile: {percentile_5*100:.2f}%")
    print(f"  95th Percentile: {percentile_95*100:.2f}%")
    print(f"  Probability of Profit: {prob_profit*100:.2f}%")

    # Save results
    output_file = f"data/simulation_results/simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs('data/simulation_results', exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'num_simulations': num_simulations,
            'mean_return': float(mean_return),
            'median_return': float(median_return),
            'std_return': float(std_return),
            'percentile_5': float(percentile_5),
            'percentile_95': float(percentile_95),
            'prob_profit': float(prob_profit),
        }, f, indent=2)

    print(f"[SIMULATION] Results saved to {output_file}")

    # Validation: 5th percentile should be > -10%, prob_profit > 60%
    if percentile_5 < -0.10 or prob_profit < 0.60:
        print("[SIMULATION] FAILED - High risk of loss")
        sys.exit(1)
    else:
        print("[SIMULATION] PASSED - Risk acceptable")
        sys.exit(0)

except Exception as e:
    print(f"[SIMULATION] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SIMULATION

    local simulation_status=$?

    if [ $simulation_status -eq 0 ]; then
        log_success "Simulation phase PASSED"
        return 0
    else
        log_error "Simulation phase FAILED - risk too high"
        return 1
    fi
}

################################################################################
# Paper Trading Phase
################################################################################

start_rust_services() {
    log_info "Starting Rust microservices..."

    local services=(
        "market-data:5001"
        "risk-manager:5002"
        "execution-engine:5003"
    )

    cd "$PROJECT_ROOT/rust/target/release"

    for service_info in "${services[@]}"; do
        IFS=':' read -r service port <<< "$service_info"

        log_info "Starting $service on port $port..."

        # Start service in background
        "./$service" > "$LOG_DIR/$service.log" 2>&1 &
        local pid=$!
        echo $pid > "$LOG_DIR/$service.pid"

        # Wait for service to be ready
        sleep 2

        if kill -0 $pid 2>/dev/null; then
            log_success "$service started (PID: $pid)"
        else
            log_error "$service failed to start"
            return 1
        fi
    done

    cd "$PROJECT_ROOT"
    return 0
}

run_paper_trading() {
    log_info "=========================================="
    log_info "PHASE 3: PAPER TRADING"
    log_info "=========================================="

    # Start Rust services
    if ! start_rust_services; then
        log_error "Failed to start Rust services"
        return 1
    fi

    log_info "Starting Python paper trading client..."

    # Run paper trading with uv
    uv run python - <<'PYTHON_TRADING' &
import sys
import time
from datetime import datetime
import signal

sys.path.insert(0, 'src')

# Graceful shutdown handler
shutdown = False
def signal_handler(sig, frame):
    global shutdown
    print("\n[TRADING] Shutdown signal received, closing positions...")
    shutdown = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    from api.alpaca_paper_trading import AlpacaPaperTradingClient
    from bridge.zmq_bridge import ZMQBridge

    print("[TRADING] Initializing paper trading client...")

    # Initialize components
    alpaca_client = AlpacaPaperTradingClient()
    zmq_bridge = ZMQBridge()

    # Subscribe to market data
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    print(f"[TRADING] Subscribing to market data for {symbols}")

    # Get initial account info
    account = alpaca_client.get_account()
    print(f"\n[TRADING] Account Status:")
    print(f"  Cash: ${float(account.cash):,.2f}")
    print(f"  Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"  Buying Power: ${float(account.buying_power):,.2f}")

    print("\n[TRADING] Starting autonomous trading loop...")
    print("[TRADING] Press Ctrl+C to stop gracefully\n")

    iteration = 0
    while not shutdown:
        iteration += 1
        current_time = datetime.now()

        # Check if market is open
        clock = alpaca_client.get_clock()
        if not clock.is_open:
            print(f"[TRADING] Market is closed. Next open: {clock.next_open}")
            time.sleep(60)
            continue

        print(f"\n[TRADING] Iteration {iteration} - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Get current positions
        positions = alpaca_client.get_positions()
        print(f"[TRADING] Current positions: {len(positions)}")

        for position in positions:
            pnl = float(position.unrealized_pl)
            pnl_pct = float(position.unrealized_plpc) * 100
            print(f"  {position.symbol}: {position.qty} shares, P&L: ${pnl:,.2f} ({pnl_pct:.2f}%)")

        # TODO: Get signals from ML model / strategy
        # For now, just monitor positions

        # Sleep for 30 seconds before next iteration
        time.sleep(30)

    # Graceful shutdown
    print("\n[TRADING] Shutting down gracefully...")

    # Close all positions
    positions = alpaca_client.get_positions()
    if positions:
        print("[TRADING] Closing all open positions...")
        for position in positions:
            try:
                alpaca_client.close_position(position.symbol)
                print(f"  Closed {position.symbol}")
            except Exception as e:
                print(f"  Failed to close {position.symbol}: {e}")

    print("[TRADING] Shutdown complete")
    sys.exit(0)

except KeyboardInterrupt:
    print("\n[TRADING] Interrupted by user")
    sys.exit(0)
except Exception as e:
    print(f"[TRADING] ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_TRADING

    local trading_pid=$!
    echo $trading_pid > "$LOG_DIR/paper_trading.pid"

    log_success "Paper trading started (PID: $trading_pid)"
    log_info "Monitor logs at: $LOG_DIR/"

    # Wait for trading process
    wait $trading_pid
    local trading_status=$?

    # Cleanup
    stop_all_services

    return $trading_status
}

################################################################################
# Service Management
################################################################################

stop_all_services() {
    log_info "Stopping all services..."

    # Stop Python trading
    if [ -f "$LOG_DIR/paper_trading.pid" ]; then
        local pid=$(cat "$LOG_DIR/paper_trading.pid")
        if kill -0 $pid 2>/dev/null; then
            kill -TERM $pid
            wait $pid 2>/dev/null || true
        fi
        rm -f "$LOG_DIR/paper_trading.pid"
    fi

    # Stop Rust services
    local services=("market-data" "risk-manager" "execution-engine")
    for service in "${services[@]}"; do
        if [ -f "$LOG_DIR/$service.pid" ]; then
            local pid=$(cat "$LOG_DIR/$service.pid")
            if kill -0 $pid 2>/dev/null; then
                kill -TERM $pid
                wait $pid 2>/dev/null || true
            fi
            rm -f "$LOG_DIR/$service.pid"
        fi
    done

    log_success "All services stopped"
}

################################################################################
# Monitoring and Auto-Restart
################################################################################

monitor_and_restart() {
    log_info "Starting continuous monitoring mode..."

    while true; do
        log_info "Starting trading cycle..."

        if run_paper_trading; then
            log_success "Trading cycle completed successfully"
            RESTART_COUNT=0
        else
            log_error "Trading cycle failed"
            RESTART_COUNT=$((RESTART_COUNT + 1))

            if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
                log_error "Maximum restart attempts ($MAX_RESTARTS) reached. Stopping."
                exit 1
            fi

            log_warning "Restarting in $RESTART_DELAY seconds (attempt $RESTART_COUNT/$MAX_RESTARTS)..."
            sleep $RESTART_DELAY
        fi
    done
}

################################################################################
# Main Execution Flow
################################################################################

main() {
    # Create log directory FIRST before any logging
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKTEST_RESULTS"
    mkdir -p "$SIMULATION_RESULTS"
    mkdir -p "$PROJECT_ROOT/data/live_trading"

    log_info "=========================================="
    log_info "AUTONOMOUS TRADING SYSTEM"
    log_info "Mode: $MODE"
    log_info "=========================================="

    # Setup
    setup_environment
    validate_configuration
    build_rust_services

    case "$MODE" in
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

        "backtest-only")
            run_backtesting
            ;;

        "paper-only")
            log_warning "Skipping validation - starting paper trading directly"
            run_paper_trading
            ;;

        "continuous")
            # Run validation once, then continuous trading
            if run_backtesting && run_simulation; then
                log_success "Initial validation passed"
                monitor_and_restart
            else
                log_error "Initial validation failed"
                exit 1
            fi
            ;;

        *)
            log_error "Unknown mode: $MODE"
            echo "Usage: $0 [--mode=full|backtest-only|paper-only|continuous]"
            exit 1
            ;;
    esac

    log_success "=========================================="
    log_success "AUTONOMOUS TRADING SYSTEM COMPLETE"
    log_success "=========================================="
}

# Cleanup handler
cleanup() {
    log_info "Cleanup triggered..."
    stop_all_services
    exit 0
}

trap cleanup EXIT INT TERM

# Run main
main "$@"
