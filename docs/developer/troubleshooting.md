# Troubleshooting Guide

Common issues and solutions for the py_rt trading system.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Build Errors](#build-errors)
3. [Runtime Errors](#runtime-errors)
4. [Performance Issues](#performance-issues)
5. [Data Issues](#data-issues)
6. [API Issues](#api-issues)
7. [Debugging Tools](#debugging-tools)

## Connection Issues

### ZMQ Connection Failed

**Symptom**: Services fail to connect via ZeroMQ

```
Error: Connection refused (os error 111)
Failed to connect to tcp://localhost:5555
```

**Solutions**:

1. Check if publisher is running:
```bash
# Check if market data service is running
sudo systemctl status py_rt-market-data

# Or check process
ps aux | grep market-data
```

2. Verify port is accessible:
```bash
# Check if port is listening
netstat -tlnp | grep 5555
# or
ss -tlnp | grep 5555
```

3. Check firewall rules:
```bash
# Allow ZMQ ports
sudo ufw allow 5555/tcp
sudo ufw allow 5556/tcp
sudo ufw allow 5557/tcp
sudo ufw allow 5558/tcp
```

4. Verify bind address in config:
```json
{
  "zmq_pub_address": "tcp://*:5555",  // Bind to all interfaces
  "zmq_sub_address": "tcp://localhost:5555"  // Connect to localhost
}
```

### Alpaca WebSocket Connection Failed

**Symptom**: Market data service cannot connect to Alpaca

```
WebSocket error: tungstenite::Error(Http(Response { status: 401 }))
```

**Solutions**:

1. Verify API credentials:
```bash
# Check environment variables
echo $ALPACA_API_KEY
echo $ALPACA_SECRET_KEY

# Test credentials
curl -u $ALPACA_API_KEY:$ALPACA_SECRET_KEY \
  https://paper-api.alpaca.markets/v2/account
```

2. Check API URL:
```bash
# Paper trading (default)
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Live trading (caution!)
ALPACA_BASE_URL=https://api.alpaca.markets
```

3. Verify account status:
```bash
# Check account in Alpaca dashboard
# Ensure trading is enabled
```

## Build Errors

### Rust Compilation Errors

**Symptom**: Cargo build fails

```
error[E0599]: no method named `send` found for type `Socket`
```

**Solutions**:

1. Update dependencies:
```bash
cd rust
cargo update
cargo build --release
```

2. Clean build cache:
```bash
cargo clean
cargo build --release
```

3. Check Rust version:
```bash
rustc --version
# Should be 1.70+

# Update if needed
rustup update
```

### Missing ZMQ Library

**Symptom**: Linker error about libzmq

```
= note: /usr/bin/ld: cannot find -lzmq
```

**Solutions**:

```bash
# Ubuntu/Debian
sudo apt-get install libzmq3-dev

# RHEL/CentOS
sudo yum install zeromq-devel

# macOS
brew install zeromq

# Then rebuild
cargo clean
cargo build --release
```

### Python Package Installation Errors

**Symptom**: uv sync fails

```
error: Failed to download package
```

**Solutions**:

1. Update uv:
```bash
pip install --upgrade uv
```

2. Clear cache:
```bash
uv cache clean
uv sync --reinstall
```

3. Check Python version:
```bash
python --version
# Should be 3.11+

# Use specific version
uv python install 3.11
```

## Runtime Errors

### Panic in Rust Component

**Symptom**: Service crashes with panic

```
thread 'main' panicked at 'called `Result::unwrap()` on an `Err` value'
```

**Solutions**:

1. Enable backtrace:
```bash
RUST_BACKTRACE=1 ./market-data
# or
RUST_BACKTRACE=full ./market-data
```

2. Check logs:
```bash
# Systemd journal
sudo journalctl -u py_rt-market-data -n 100 --no-pager

# Log files
tail -f /var/log/py_rt/market-data.log
```

3. Run in debug mode:
```bash
RUST_LOG=debug cargo run --bin market-data
```

### Memory Leak

**Symptom**: Memory usage grows continuously

**Solutions**:

1. Monitor memory:
```bash
# Check current usage
ps aux | grep market-data

# Monitor over time
watch -n 5 'ps aux | grep py_rt'
```

2. Profile with valgrind:
```bash
cargo build
valgrind --leak-check=full ./target/debug/market-data
```

3. Use heaptrack:
```bash
heaptrack ./target/release/market-data
heaptrack_gui heaptrack.market-data.*.gz
```

### Deadlock

**Symptom**: Service hangs, no progress

**Solutions**:

1. Get stack trace:
```bash
# Find PID
ps aux | grep market-data

# Send SIGQUIT to print stack trace
kill -3 <PID>

# Check logs for stack trace
```

2. Use GDB:
```bash
# Attach to running process
gdb -p <PID>

# Get backtrace
(gdb) thread apply all bt
```

## Performance Issues

### High Latency

**Symptom**: Orders execute slowly (>100ms)

**Solutions**:

1. Check system load:
```bash
# CPU usage
top

# I/O wait
iostat -x 1

# Network latency
ping data.alpaca.markets
```

2. Optimize Rust build:
```toml
[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
```

3. Tune ZMQ buffers:
```rust
socket.set_sndhwm(10000)?;
socket.set_rcvhwm(10000)?;
socket.set_tcp_nodelay(true)?;
```

### Low Throughput

**Symptom**: Processing <1000 messages/second

**Solutions**:

1. Profile with perf:
```bash
# Record
sudo perf record -g ./target/release/market-data

# Analyze
sudo perf report
```

2. Use flamegraph:
```bash
cargo install flamegraph
cargo flamegraph --bin market-data
```

3. Check async runtime:
```rust
// Increase worker threads
tokio::runtime::Builder::new_multi_thread()
    .worker_threads(8)
    .enable_all()
    .build()?
```

## Data Issues

### Missing Market Data

**Symptom**: No updates received

**Solutions**:

1. Check subscription:
```rust
// Verify symbols are subscribed
let symbols = vec!["AAPL", "MSFT"];
ws_client.subscribe(&symbols).await?;
```

2. Check market hours:
```bash
# Market data only during trading hours
# NYSE: 9:30 AM - 4:00 PM ET
```

3. Verify data plan:
```bash
# Check Alpaca account
# Ensure data subscription is active
```

### Stale Data

**Symptom**: Data is delayed or old

**Solutions**:

1. Check timestamp:
```rust
let age = SystemTime::now() - bar.timestamp;
if age > Duration::from_secs(60) {
    warn!("Stale data: {:?}", age);
}
```

2. Monitor WebSocket connection:
```rust
// Add heartbeat
tokio::spawn(async move {
    let mut interval = tokio::time::interval(Duration::from_secs(30));
    loop {
        interval.tick().await;
        ws.send_heartbeat().await?;
    }
});
```

## API Issues

### Rate Limit Exceeded

**Symptom**: API requests rejected with 429

```
ApiError: Rate limit exceeded (429)
```

**Solutions**:

1. Check rate limiter:
```rust
use governor::{Quota, RateLimiter};

let limiter = RateLimiter::direct(
    Quota::per_minute(nonzero!(200u32))
);

// Before each request
limiter.until_ready().await;
```

2. Reduce request frequency:
```rust
// Batch orders
let orders = vec![order1, order2, order3];
let results = execute_batch(orders).await?;
```

### Authentication Errors

**Symptom**: 401 Unauthorized

**Solutions**:

1. Verify credentials:
```bash
# Test with curl
curl -v \
  -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
  -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" \
  https://paper-api.alpaca.markets/v2/account
```

2. Check credentials format:
```bash
# Should be alphanumeric strings
echo $ALPACA_API_KEY | wc -c
# Should be 20+ characters
```

### Order Rejection

**Symptom**: Orders rejected by broker

**Solutions**:

1. Check order parameters:
```rust
// Ensure valid order type
let order = Order {
    symbol: "AAPL".to_string(),
    side: Side::Buy,
    quantity: 100,
    order_type: OrderType::Limit,
    limit_price: Some(150.0),  // Required for Limit orders
};
```

2. Verify buying power:
```rust
let account = client.get_account().await?;
if order_value > account.buying_power {
    return Err(Error::InsufficientFunds);
}
```

3. Check position limits:
```rust
let position = positions.get(&symbol);
if position.quantity + order.quantity > max_position_size {
    return Err(Error::PositionLimit);
}
```

## Debugging Tools

### Logging

```rust
// Enable debug logging
use tracing::{debug, info, warn, error};

#[instrument(skip(data))]
async fn process_trade(trade: Trade) {
    debug!("Processing trade: {:?}", trade);
    // ...
    info!("Trade processed successfully");
}

// Run with debug logs
RUST_LOG=debug cargo run
```

### Metrics

```rust
use prometheus::{Counter, Histogram, register_counter, register_histogram};

lazy_static! {
    static ref TRADES_PROCESSED: Counter = register_counter!(
        "trades_processed_total",
        "Total number of trades processed"
    ).unwrap();

    static ref ORDER_LATENCY: Histogram = register_histogram!(
        "order_latency_seconds",
        "Order execution latency"
    ).unwrap();
}

// Use in code
TRADES_PROCESSED.inc();
let timer = ORDER_LATENCY.start_timer();
// ... execute order ...
timer.observe_duration();
```

### Distributed Tracing

```rust
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

tracing_subscriber::registry()
    .with(tracing_subscriber::fmt::layer())
    .with(tracing_subscriber::EnvFilter::from_default_env())
    .init();
```

### Health Checks

```bash
# Check service health
curl http://localhost:9090/health

# Check metrics
curl http://localhost:9090/metrics

# Check component status
systemctl status py_rt-*
```

### Testing

```bash
# Run tests with output
cargo test -- --nocapture --test-threads=1

# Run specific test
cargo test test_order_execution

# Run with logging
RUST_LOG=debug cargo test
```

## Getting Help

If you can't resolve your issue:

1. Search [GitHub Issues](https://github.com/SamoraDC/RustAlgorithmTrading/issues)
2. Check [GitHub Discussions](https://github.com/SamoraDC/RustAlgorithmTrading/discussions)
3. Create a new issue with:
   - Error message
   - Log output
   - System information
   - Steps to reproduce

## Next Steps

- [Performance Tuning](performance.md) - Optimize system
- [Monitoring Guide](../guides/monitoring.md) - Set up monitoring
- [Contributing](contributing.md) - Fix issues and contribute

---

**Last Updated**: 2025-10-14
