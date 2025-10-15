# Development Environment Setup

This guide walks you through setting up your development environment for the Rust Algorithm Trading System.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Rust Installation](#rust-installation)
3. [Project Setup](#project-setup)
4. [Alpaca API Configuration](#alpaca-api-configuration)
5. [Running Components](#running-components)
6. [Development Workflow](#development-workflow)
7. [Testing](#testing)
8. [Debugging](#debugging)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Operating System**: Linux, macOS, or Windows (WSL2 recommended)
- **Rust**: 1.70+ (latest stable)
- **Python**: 3.8+ (for signal-bridge component)
- **Git**: For version control
- **ZeroMQ**: System libraries (see installation below)

### Optional Tools

- **Docker**: For containerized deployment
- **VSCode**: Recommended IDE with rust-analyzer extension
- **RustRover/IntelliJ**: Alternative IDE with Rust plugin
- **tmux/screen**: For running multiple components in one terminal

## Rust Installation

### Install Rustup

Rustup is the official Rust toolchain installer:

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Windows (PowerShell)
# Download and run: https://win.rustup.rs/
```

### Verify Installation

```bash
rustc --version
# Output: rustc 1.77.0 (2024-03-21)

cargo --version
# Output: cargo 1.77.0 (2024-03-21)
```

### Install Additional Components

```bash
# Formatter
rustup component add rustfmt

# Linter
rustup component add clippy

# Source code for rust-analyzer
rustup component add rust-src
```

## Project Setup

### Clone Repository

```bash
git clone https://github.com/SamoraDC/RustAlgorithmTrading.git
cd RustAlgorithmTrading
```

### Install System Dependencies

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    pkg-config \
    libssl-dev \
    libzmq3-dev \
    python3-dev \
    python3-pip
```

#### macOS

```bash
brew install zeromq pkg-config openssl
```

#### Windows (WSL2)

```bash
# Use Ubuntu/Debian instructions above
```

### Build Project

```bash
cd rust
cargo build --release
```

This will:
1. Download and compile dependencies (~10 minutes first time)
2. Build all workspace members
3. Create binaries in `target/release/`

### Verify Build

```bash
# Check that all binaries were created
ls -lh target/release/market-data
ls -lh target/release/signal-bridge
ls -lh target/release/risk-manager
ls -lh target/release/execution-engine
```

## Alpaca API Configuration

### Create Alpaca Account

1. Visit [Alpaca Markets](https://alpaca.markets)
2. Sign up for a free paper trading account
3. Verify your email
4. Navigate to "API Keys" in dashboard

### Generate API Keys

1. Click "Generate API Key"
2. Select "Paper Trading" environment
3. Copy your API Key and Secret Key
4. **IMPORTANT**: Save your secret key securely (shown only once)

### Create Configuration File

Create `config/system.json` in project root:

```bash
mkdir -p config
cat > config/system.json << 'EOF'
{
  "market_data": {
    "alpaca_api_key": "YOUR_API_KEY_HERE",
    "alpaca_secret_key": "YOUR_SECRET_KEY_HERE",
    "alpaca_data_url": "wss://data.alpaca.markets/stream",
    "zmq_pub_address": "tcp://*:5555",
    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
    "reconnect_delay_secs": 5,
    "max_reconnect_attempts": 10
  },
  "signal_bridge": {
    "zmq_sub_address": "tcp://localhost:5555",
    "zmq_pub_address": "tcp://*:5556",
    "python_module": "strategies.ml_strategy",
    "model_path": "models/lstm_model.pt"
  },
  "risk_manager": {
    "zmq_sub_address": "tcp://localhost:5555,tcp://localhost:5556",
    "zmq_pub_address": "tcp://*:5557",
    "max_position_size": 10000.0,
    "max_order_size": 1000.0,
    "max_daily_loss": 5000.0,
    "max_open_positions": 10,
    "max_position_concentration": 0.25
  },
  "execution_engine": {
    "alpaca_api_key": "YOUR_API_KEY_HERE",
    "alpaca_secret_key": "YOUR_SECRET_KEY_HERE",
    "alpaca_api_url": "https://paper-api.alpaca.markets",
    "zmq_sub_address": "tcp://localhost:5557",
    "zmq_pub_address": "tcp://*:5558",
    "max_retries": 3,
    "max_slippage_bps": 50,
    "rate_limit_per_minute": 200,
    "timeout_secs": 30
  }
}
EOF
```

**Replace placeholders**:
- `YOUR_API_KEY_HERE` → Your Alpaca API key
- `YOUR_SECRET_KEY_HERE` → Your Alpaca secret key

### Secure API Keys

**IMPORTANT**: Never commit API keys to version control!

```bash
# Add to .gitignore (already included)
echo "config/system.json" >> .gitignore

# Set restrictive permissions
chmod 600 config/system.json
```

### Environment Variables (Alternative)

For production, use environment variables:

```bash
# Add to ~/.bashrc or ~/.zshrc
export ALPACA_API_KEY="your_api_key"
export ALPACA_SECRET_KEY="your_secret_key"

# Reload shell
source ~/.bashrc
```

Update code to read from environment:
```rust
use std::env;

let api_key = env::var("ALPACA_API_KEY")
    .expect("ALPACA_API_KEY must be set");
```

## Running Components

### Option 1: Individual Terminals

Run each component in a separate terminal:

```bash
# Terminal 1: Market Data Service
cd rust/market-data
RUST_LOG=info cargo run --release

# Terminal 2: Signal Bridge
cd rust/signal-bridge
RUST_LOG=info cargo run --release

# Terminal 3: Risk Manager
cd rust/risk-manager
RUST_LOG=info cargo run --release

# Terminal 4: Execution Engine
cd rust/execution-engine
RUST_LOG=info cargo run --release
```

### Option 2: tmux Session

Use tmux for a unified view:

```bash
# Create tmux session
tmux new-session -s trading

# Split into 4 panes
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

# Run components (execute in each pane)
# Pane 0: Market Data
cd rust/market-data && RUST_LOG=info cargo run --release

# Pane 1: Signal Bridge
cd rust/signal-bridge && RUST_LOG=info cargo run --release

# Pane 2: Risk Manager
cd rust/risk-manager && RUST_LOG=info cargo run --release

# Pane 3: Execution Engine
cd rust/execution-engine && RUST_LOG=info cargo run --release
```

Detach: `Ctrl+B` then `D`
Reattach: `tmux attach -t trading`

### Option 3: Shell Script

Create `scripts/start_system.sh`:

```bash
#!/bin/bash

RUST_LOG=info cargo run --release --bin market-data &
RUST_LOG=info cargo run --release --bin signal-bridge &
RUST_LOG=info cargo run --release --bin risk-manager &
RUST_LOG=info cargo run --release --bin execution-engine &

echo "System started. Press Ctrl+C to stop all components."
wait
```

```bash
chmod +x scripts/start_system.sh
./scripts/start_system.sh
```

### Verify System Health

Check component logs for startup messages:

```
[INFO market_data] WebSocket connected to Alpaca Markets
[INFO market_data] Subscribed to symbols: AAPL, MSFT, GOOGL
[INFO signal_bridge] Listening on tcp://localhost:5555
[INFO risk_manager] Risk checks enabled: max_position_size=10000.0
[INFO execution_engine] Alpaca API connection established
```

## Development Workflow

### Code Changes

1. **Edit Source Files**: Make changes to `.rs` files
2. **Format Code**: Run `cargo fmt` to auto-format
3. **Lint Code**: Run `cargo clippy` to check for issues
4. **Run Tests**: Run `cargo test` to verify changes
5. **Build**: Run `cargo build` to compile

### Hot Reload

Rust requires recompilation after changes. Use `cargo watch` for auto-rebuild:

```bash
# Install cargo-watch
cargo install cargo-watch

# Auto-rebuild on file changes
cargo watch -x check -x test -x run
```

### IDE Setup

#### VSCode

Install extensions:
1. **rust-analyzer**: Rust language server
2. **CodeLLDB**: Debugger support
3. **Better TOML**: Cargo.toml syntax highlighting
4. **Error Lens**: Inline error display

`.vscode/settings.json`:
```json
{
  "rust-analyzer.check.command": "clippy",
  "rust-analyzer.cargo.features": "all",
  "editor.formatOnSave": true
}
```

#### RustRover/IntelliJ

1. Install Rust plugin
2. Open project root as Cargo workspace
3. Configure run configurations for each binary

## Testing

### Run All Tests

```bash
# Run all tests in workspace
cargo test --workspace

# Run with logging output
cargo test --workspace -- --nocapture

# Run specific test
cargo test test_order_book
```

### Run Tests for Specific Component

```bash
# Market data tests
cargo test -p market-data

# With coverage (requires cargo-tarpaulin)
cargo install cargo-tarpaulin
cargo tarpaulin -p market-data --out Html
```

### Integration Tests

```bash
# Run integration tests only
cargo test --workspace --test '*'

# Run specific integration test
cargo test --test integration_test
```

### Benchmark Tests

```bash
# Requires nightly Rust
rustup install nightly

# Run benchmarks
cargo +nightly bench
```

## Debugging

### Print Debugging

Use `tracing` for structured logging:

```rust
use tracing::{info, debug, warn, error};

#[tracing::instrument]
async fn process_order(order: &Order) {
    debug!(?order, "Processing order");
    // ...
    info!(order_id = %order.order_id, "Order submitted");
}
```

Set log level:
```bash
# Info level (default)
RUST_LOG=info cargo run

# Debug level for specific module
RUST_LOG=market_data=debug cargo run

# Trace level for all modules
RUST_LOG=trace cargo run
```

### Debugger (LLDB/GDB)

#### VSCode with CodeLLDB

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "lldb",
      "request": "launch",
      "name": "Debug market-data",
      "cargo": {
        "args": ["build", "--bin=market-data"],
        "filter": {
          "name": "market-data",
          "kind": "bin"
        }
      },
      "args": [],
      "cwd": "${workspaceFolder}/rust"
    }
  ]
}
```

#### Command Line

```bash
# Build with debug symbols
cargo build

# Run with lldb
rust-lldb target/debug/market-data

# Set breakpoint
(lldb) breakpoint set --name main
(lldb) run
```

### Performance Profiling

```bash
# Install flamegraph
cargo install flamegraph

# Generate flamegraph (requires sudo on Linux)
cargo flamegraph --bin market-data

# Open flamegraph.svg in browser
```

## Troubleshooting

### Build Errors

#### ZMQ linking error

```
error: linking with `cc` failed
  = note: /usr/bin/ld: cannot find -lzmq
```

**Solution**: Install ZMQ development libraries
```bash
# Ubuntu/Debian
sudo apt install libzmq3-dev

# macOS
brew install zeromq
```

#### OpenSSL linking error

```
error: failed to run custom build command for `openssl-sys`
```

**Solution**: Install OpenSSL development libraries
```bash
# Ubuntu/Debian
sudo apt install libssl-dev

# macOS (usually pre-installed)
brew install openssl
export OPENSSL_DIR=$(brew --prefix openssl)
```

### Runtime Errors

#### Connection refused (ZMQ)

```
Error: Connection refused (os error 111)
```

**Solution**: Check that market-data is running first (it publishes on port 5555)

#### WebSocket authentication failed

```
Error: Unauthorized (401)
```

**Solution**: Verify API keys in `config/system.json`

#### Rate limit exceeded

```
Error: Too Many Requests (429)
```

**Solution**: Alpaca limits to 200 requests/minute. Add delay or use exponential backoff.

### Performance Issues

#### High CPU usage

**Cause**: Busy-waiting in async loops

**Solution**: Use `tokio::time::sleep` or `tokio::select!`

```rust
// Bad: Busy-waiting
loop {
    if let Some(msg) = try_recv() {
        process(msg);
    }
}

// Good: Async waiting
loop {
    let msg = socket.recv().await?;
    process(msg);
}
```

#### High memory usage

**Cause**: Large order book buffers or memory leaks

**Solution**: Monitor with `cargo-instruments` (macOS) or `valgrind` (Linux)

```bash
# macOS
cargo install cargo-instruments
cargo instruments -t Allocations

# Linux
valgrind --leak-check=full target/debug/market-data
```

## Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Review [ALPACA_API.md](../api/ALPACA_API.md) for API integration details
- Check [ZMQ_PROTOCOL.md](../api/ZMQ_PROTOCOL.md) for messaging protocols
- See [CONTRIBUTING.md](../../CONTRIBUTING.md) for code style guidelines

---

**Last Updated**: 2024-10-14 | **Maintainer**: Davi Castro Samora
