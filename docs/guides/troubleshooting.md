# Troubleshooting Guide

Common issues, error scenarios, and solutions for the py_rt algorithmic trading system.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Service-Specific Issues](#service-specific-issues)
- [Network and Connectivity](#network-and-connectivity)
- [API and Authentication](#api-and-authentication)
- [Performance Issues](#performance-issues)
- [Data and Configuration](#data-and-configuration)
- [Emergency Scenarios](#emergency-scenarios)

## Quick Diagnostics

### First Steps for Any Issue

```bash
# 1. Check all service status
./scripts/health_check.sh

# 2. View recent logs for errors
sudo journalctl -u trading-* --priority=err --since "10 minutes ago"

# 3. Check system resources
top -b -n 1 | head -20
df -h

# 4. Verify ZeroMQ connections
netstat -an | grep -E '(5555|5556|5557|5558)'

# 5. Check Prometheus metrics
curl -s http://localhost:9090/metrics | grep -E "(error|failed|disconnect)"
```

### Common Error Patterns

| Error Pattern | Location | Common Cause |
|--------------|----------|--------------|
| `Connection refused` | Any service | Service not running or wrong port |
| `WebSocket error` | Market Data | API key issue or network problem |
| `Risk check failed` | Risk Manager | Position limit exceeded |
| `Order rejected` | Execution Engine | Insufficient buying power or invalid order |
| `Timeout` | Any service | Network latency or overloaded service |
| `Parse error` | Any service | Configuration file syntax error |

## Service-Specific Issues

### Market Data Service

#### Issue: WebSocket Connection Fails

**Symptoms**:
```
ERROR market_data: WebSocket connection failed: Connection refused
ERROR market_data: Failed to authenticate with Alpaca
```

**Diagnosis**:
```bash
# Check service status
sudo systemctl status trading-market-data

# Check API credentials
grep APCA_API_KEY .env

# Test WebSocket connection manually
wscat -c wss://stream.data.alpaca.markets/v2/iex
```

**Solutions**:

1. **Invalid API credentials**:
```bash
# Verify credentials with Alpaca API
curl -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" \
     https://paper-api.alpaca.markets/v2/account

# If 401 Unauthorized, regenerate keys at alpaca.markets
```

2. **Network connectivity**:
```bash
# Test DNS resolution
nslookup stream.data.alpaca.markets

# Test connectivity
telnet stream.data.alpaca.markets 443

# Check firewall
sudo ufw status
```

3. **Service binding issue**:
```bash
# Check if port is already in use
sudo lsof -i :5555

# Kill conflicting process
sudo kill -9 <PID>

# Restart service
sudo systemctl restart trading-market-data
```

#### Issue: High Message Latency

**Symptoms**:
```
WARN market_data: Message processing latency high: 250ms
```

**Diagnosis**:
```bash
# Check current latency
curl -s http://localhost:9090/metrics | grep market_data_latency_seconds

# Check message queue depth
curl -s http://localhost:9090/metrics | grep market_data_queue_depth
```

**Solutions**:

1. **CPU bottleneck**:
```bash
# Check CPU usage
top -b -n 1 | grep market-data

# Increase process priority
sudo renice -n -5 -p $(pgrep market-data)
```

2. **Message queue backup**:
```bash
# Restart service to clear queue
sudo systemctl restart trading-market-data

# Reduce subscribed symbols if too many
nano config/system.json
# Reduce symbols list to 5-10 most active
```

3. **Network issues**:
```bash
# Check network latency to Alpaca
ping stream.data.alpaca.markets

# Check packet loss
mtr -c 100 stream.data.alpaca.markets
```

#### Issue: Missing Market Data

**Symptoms**:
- No quotes received for specific symbols
- Gaps in price data

**Diagnosis**:
```bash
# Check subscription status
sudo journalctl -u trading-market-data -n 100 | grep -i subscribe

# Check message counts per symbol
curl -s http://localhost:9090/metrics | grep market_data_messages_by_symbol
```

**Solutions**:

1. **Symbol not subscribed**:
```bash
# Add symbol to config
nano config/system.json
# Add to "symbols": ["AAPL", "MSFT", "NEW_SYMBOL"]

# Restart market data service
sudo systemctl restart trading-market-data
```

2. **Symbol suspended or halted**:
```bash
# Check symbol status via Alpaca API
curl -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" \
     https://paper-api.alpaca.markets/v2/assets/AAPL
```

### Risk Manager

#### Issue: All Orders Being Rejected

**Symptoms**:
```
ERROR risk_manager: Risk check failed: Position limit exceeded
ERROR risk_manager: Risk check failed: Max daily loss reached
```

**Diagnosis**:
```bash
# Check current risk metrics
curl -s http://localhost:9090/metrics | grep -E "(risk_|position_)"

# Check circuit breaker status
curl -s http://localhost:9090/metrics | grep circuit_breaker_active

# View risk violations
sudo journalctl -u trading-risk-manager -n 100 | grep "Risk check failed"
```

**Solutions**:

1. **Position limit exceeded**:
```bash
# Check current positions
python scripts/check_positions.py

# Close positions if needed
python scripts/close_position.py --symbol AAPL

# Or adjust limits
nano config/risk_limits.toml
# Increase max_shares or max_notional_per_position
sudo systemctl restart trading-risk-manager
```

2. **Daily loss limit reached**:
```bash
# Check current P&L
python scripts/check_pnl.py

# If circuit breaker activated incorrectly, deactivate
curl -X POST http://localhost:8080/api/v1/circuit-breaker/deactivate

# Adjust threshold if too conservative
nano config/risk_limits.toml
# Increase max_daily_loss
sudo systemctl restart trading-risk-manager
```

3. **Concentration limit**:
```bash
# Check position concentration
python scripts/check_concentration.py

# Diversify positions or adjust limits
nano config/risk_limits.toml
# Increase max_concentration_percent
```

#### Issue: Risk Manager Not Receiving Market Data

**Symptoms**:
```
WARN risk_manager: No market data received for 30 seconds
ERROR risk_manager: Cannot calculate position value without market data
```

**Diagnosis**:
```bash
# Check ZeroMQ subscription
netstat -an | grep 5555

# Verify market data service is publishing
python scripts/monitor_zmq.py --port 5555

# Check risk manager logs
sudo journalctl -u trading-risk-manager -f
```

**Solutions**:

1. **ZeroMQ connection issue**:
```bash
# Verify ZeroMQ configuration
grep zmq_subscribe_address config/system.json

# Should be: "tcp://127.0.0.1:5555"

# Restart risk manager
sudo systemctl restart trading-risk-manager
```

2. **Market data service not running**:
```bash
# Start market data service first
sudo systemctl start trading-market-data
sleep 5

# Then start risk manager
sudo systemctl start trading-risk-manager
```

### Execution Engine

#### Issue: Orders Not Being Submitted

**Symptoms**:
```
ERROR execution_engine: Failed to submit order: API rate limit exceeded
ERROR execution_engine: Order submission timeout
```

**Diagnosis**:
```bash
# Check order submission rate
curl -s http://localhost:9090/metrics | grep execution_orders_submitted_total

# Check API rate limiting
curl -s http://localhost:9090/metrics | grep execution_rate_limit_errors

# View recent order failures
sudo journalctl -u trading-execution-engine -n 50 | grep -i "failed\|error"
```

**Solutions**:

1. **API rate limit exceeded**:
```bash
# Reduce order submission rate
nano config/system.json
# Adjust: "rate_limit_per_second": 100  (from 200)

# Enable order batching
nano rust/execution-engine/src/main.rs
# Implement order batching logic

# Restart execution engine
sudo systemctl restart trading-execution-engine
```

2. **Network timeout**:
```bash
# Increase timeout values
nano config/system.json
# Increase: "retry_delay_ms": 2000

# Check network connectivity to Alpaca
ping paper-api.alpaca.markets

# Test API directly
curl -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" \
     https://paper-api.alpaca.markets/v2/orders
```

3. **Insufficient buying power**:
```bash
# Check account status
curl -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" \
     https://paper-api.alpaca.markets/v2/account | jq '.buying_power'

# Reduce order sizes
nano config/risk_limits.toml
# Decrease: max_order_value
```

#### Issue: High Slippage on Orders

**Symptoms**:
- Orders filled at prices significantly different from expected
- Metrics show high slippage values

**Diagnosis**:
```bash
# Check slippage metrics
curl -s http://localhost:9090/metrics | grep execution_slippage

# Review recent fills
python scripts/analyze_fills.py --since "1 hour ago"
```

**Solutions**:

1. **Using market orders in low liquidity**:
```bash
# Switch to limit orders
nano config/system.json
# Change default order type to limit

# Add limit price calculation
# Price = mid_price + (spread * max_slippage_tolerance)
```

2. **Large order size**:
```bash
# Implement TWAP or VWAP execution
python scripts/enable_algo_execution.py --algo twap

# Reduce order size
nano config/risk_limits.toml
# Decrease: max_order_size
```

3. **Trading during volatile periods**:
```bash
# Avoid trading during market open/close
nano config/risk_limits.toml
# Set blackout_periods = ["09:30-09:45", "15:45-16:00"]
```

### Signal Bridge

#### Issue: ML Model Loading Fails

**Symptoms**:
```
ERROR signal_bridge: Failed to load ONNX model: File not found
ERROR signal_bridge: Model inference error: Invalid input shape
```

**Diagnosis**:
```bash
# Check model file
ls -lh models/

# Verify model path in config
grep model_path config/system.json

# Test model loading
python scripts/test_model_loading.py models/trading_model.onnx
```

**Solutions**:

1. **Model file not found**:
```bash
# Verify model exists
ls -l models/trading_model.onnx

# Copy model from backup
cp backups/models/trading_model.onnx models/

# Restart signal bridge
sudo systemctl restart trading-signal-bridge
```

2. **Model version incompatibility**:
```bash
# Re-export model with correct ONNX version
python scripts/export_model.py --onnx-version 14

# Update Rust ONNX runtime version
cd rust/signal-bridge
cargo update -p ort

# Rebuild and restart
cargo build --release
sudo systemctl restart trading-signal-bridge
```

3. **Input shape mismatch**:
```bash
# Check model input requirements
python scripts/inspect_onnx_model.py models/trading_model.onnx

# Ensure feature vector matches expected shape
nano config/system.json
# Verify "features" list matches model input
```

## Network and Connectivity

### Issue: ZeroMQ Binding Fails

**Symptoms**:
```
ERROR common: Failed to bind ZeroMQ socket: Address already in use
```

**Diagnosis**:
```bash
# Check what's using the port
sudo lsof -i :5555

# Check ZeroMQ socket status
ss -tan | grep -E '(5555|5556|5557|5558)'
```

**Solutions**:

1. **Port already in use**:
```bash
# Kill process using the port
sudo kill -9 $(lsof -t -i:5555)

# Or change port in configuration
nano config/system.json
# Change: "zmq_publish_address": "tcp://127.0.0.1:5560"
```

2. **Permission denied**:
```bash
# Use ports above 1024 (no root required)
# Or add capability to binary
sudo setcap cap_net_bind_service=+ep rust/target/release/market-data
```

### Issue: Firewall Blocking Connections

**Symptoms**:
- Cannot connect to external APIs
- WebSocket connections timeout

**Diagnosis**:
```bash
# Check firewall status
sudo ufw status

# Check iptables rules
sudo iptables -L -n

# Test connection
telnet paper-api.alpaca.markets 443
```

**Solutions**:

```bash
# Allow outbound HTTPS connections
sudo ufw allow out 443/tcp

# Allow Alpaca API endpoints
sudo ufw allow out to paper-api.alpaca.markets

# Reload firewall
sudo ufw reload
```

### Issue: High Network Latency

**Symptoms**:
```
WARN execution_engine: API request took 5000ms (expected <1000ms)
```

**Diagnosis**:
```bash
# Measure latency to Alpaca
ping -c 100 paper-api.alpaca.markets | tail -1

# Trace route
traceroute paper-api.alpaca.markets

# Check network interface errors
ifconfig | grep -E "(errors|dropped)"
```

**Solutions**:

1. **Network congestion**:
```bash
# Check bandwidth usage
iftop -i eth0

# Prioritize trading traffic (QoS)
sudo tc qdisc add dev eth0 root handle 1: htb default 12
sudo tc class add dev eth0 parent 1: classid 1:1 htb rate 100mbit
```

2. **Sub-optimal routing**:
```bash
# Consider using VPN closer to exchange
# Or co-locate server in AWS us-east-1 (closer to Alpaca)
```

## API and Authentication

### Issue: API Authentication Fails

**Symptoms**:
```
ERROR execution_engine: 401 Unauthorized
ERROR market_data: Authentication failed: Invalid API key
```

**Diagnosis**:
```bash
# Test API credentials
curl -v -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" \
     https://paper-api.alpaca.markets/v2/account

# Check environment variables
env | grep APCA_
```

**Solutions**:

1. **Invalid or expired keys**:
```bash
# Regenerate API keys at alpaca.markets dashboard
# Update .env file
nano .env
# APCA_API_KEY_ID=new_key
# APCA_API_SECRET_KEY=new_secret

# Restart all services
./scripts/restart_trading_system.sh
```

2. **Keys not loaded**:
```bash
# Ensure .env is sourced
source .env

# Verify systemd service loads environment
sudo systemctl edit trading-market-data
# Add: EnvironmentFile=/opt/RustAlgorithmTrading/.env

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart trading-market-data
```

### Issue: Paper Trading vs Live Trading Mismatch

**Symptoms**:
- Orders submitted to wrong environment
- Cannot find positions in expected account

**Diagnosis**:
```bash
# Check current configuration
grep APCA_API_BASE_URL .env
grep paper_trading config/system.json

# Verify account type
curl -H "APCA-API-KEY-ID: $APCA_API_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $APCA_API_SECRET_KEY" \
     $APCA_API_BASE_URL/v2/account | jq '.account_number'
```

**Solutions**:

```bash
# Ensure paper trading is enabled
nano .env
# APCA_API_BASE_URL=https://paper-api.alpaca.markets

nano config/system.json
# "paper_trading": true

# NEVER switch to live trading without proper testing
# and explicit configuration change
```

## Performance Issues

### Issue: High Memory Usage

**Symptoms**:
```
WARN kernel: Out of memory: Killed process <PID> (market-data)
```

**Diagnosis**:
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check service-specific memory
sudo systemctl status trading-market-data | grep Memory

# Monitor over time
watch -n 1 'ps aux | grep -E "(market-data|risk-manager|execution-engine)"'
```

**Solutions**:

1. **Memory leak**:
```bash
# Check for memory leak in logs
sudo journalctl -u trading-market-data | grep -i "memory\|leak"

# Restart service to clear
sudo systemctl restart trading-market-data

# Update to latest version (may contain fixes)
git pull
cd rust
cargo build --release
sudo systemctl restart trading-*
```

2. **Insufficient system memory**:
```bash
# Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Or upgrade server memory
```

3. **Message queue buildup**:
```bash
# Reduce message retention
nano rust/market-data/src/main.rs
# Set ZMQ_SNDHWM and ZMQ_RCVHWM to lower values

# Rebuild and restart
cd rust
cargo build --release
sudo systemctl restart trading-market-data
```

### Issue: High CPU Usage

**Symptoms**:
- Services consuming >90% CPU
- System unresponsive

**Diagnosis**:
```bash
# Identify CPU-intensive process
top -b -n 1 | head -20

# Check per-thread CPU usage
top -H -p $(pgrep market-data)

# Profile with perf
sudo perf record -p $(pgrep market-data) -g -- sleep 10
sudo perf report
```

**Solutions**:

1. **Tight loop or busy-wait**:
```bash
# Check for recent code changes
git log --oneline -10

# Revert to last known good version
git checkout v1.0.0
cd rust
cargo build --release
```

2. **Excessive logging**:
```bash
# Reduce log level
export RUST_LOG=info  # change from debug

# Restart services
sudo systemctl restart trading-*
```

3. **Too many symbols**:
```bash
# Reduce subscribed symbols
nano config/system.json
# Keep only 5-10 most liquid symbols

sudo systemctl restart trading-market-data
```

### Issue: Slow Order Execution

**Symptoms**:
- Orders taking >1 second to submit
- High execution latency in metrics

**Diagnosis**:
```bash
# Check execution latency
curl -s http://localhost:9090/metrics | grep execution_latency_seconds

# Profile execution path
sudo strace -c -p $(pgrep execution-engine)
```

**Solutions**:

1. **Network latency**:
```bash
# Co-locate closer to exchange
# Use lower-latency network provider
# Enable TCP fast open
sudo sysctl -w net.ipv4.tcp_fastopen=3
```

2. **Synchronous API calls**:
```bash
# Ensure async execution
# Check Rust code uses Tokio async/await properly
cd rust/execution-engine
cargo build --release --features async-execution
```

3. **CPU throttling**:
```bash
# Disable CPU frequency scaling
sudo cpupower frequency-set --governor performance
```

## Data and Configuration

### Issue: Configuration File Parse Error

**Symptoms**:
```
ERROR common: Failed to parse config: expected value at line 45 column 5
```

**Diagnosis**:
```bash
# Validate JSON syntax
jq . config/system.json

# Validate TOML syntax
python -c "import toml; toml.load('config/risk_limits.toml')"
```

**Solutions**:

```bash
# Fix JSON syntax errors
# Common issues:
# - Trailing commas
# - Missing quotes
# - Unescaped special characters

# Restore from backup if needed
cp config/system.json.bak config/system.json

# Verify after fix
jq . config/system.json > /dev/null && echo "Valid JSON"
```

### Issue: Corrupt Data Files

**Symptoms**:
```
ERROR position_tracker: Failed to deserialize position data
ERROR signal_bridge: Cannot read model file
```

**Diagnosis**:
```bash
# Check file integrity
sha256sum data/positions.dat
sha256sum models/trading_model.onnx

# Compare with checksums from backup
```

**Solutions**:

```bash
# Restore from backup
cp backups/data/positions.dat data/
cp backups/models/trading_model.onnx models/

# Verify checksums match
sha256sum -c checksums.txt

# Restart services
sudo systemctl restart trading-*
```

## Emergency Scenarios

### Scenario: System Not Responding

**Immediate Actions**:

```bash
# 1. Activate emergency stop
./scripts/emergency_stop.sh

# 2. Check system resources
top
df -h

# 3. Kill hung processes if needed
sudo killall -9 market-data risk-manager execution-engine signal-bridge

# 4. Check for kernel panic
dmesg | tail -50

# 5. Reboot if necessary
sudo reboot
```

### Scenario: Trading Losses Exceeding Limits

**Immediate Actions**:

```bash
# 1. Activate circuit breaker
curl -X POST http://localhost:8080/api/v1/circuit-breaker/activate

# 2. Cancel all open orders
python scripts/cancel_all_orders.py

# 3. Liquidate positions if needed
python scripts/liquidate_positions.py --confirm

# 4. Review P&L
python scripts/check_pnl.py --detailed

# 5. Investigate cause
sudo journalctl -u trading-* --since "1 hour ago" | grep -i "error\|loss"

# 6. Document incident
./scripts/create_incident_report.sh
```

### Scenario: Data Feed Stopped

**Immediate Actions**:

```bash
# 1. Check WebSocket connection
sudo journalctl -u trading-market-data -n 100 | grep -i "websocket\|connect"

# 2. Verify API status
curl https://status.alpaca.markets/

# 3. Restart market data service
sudo systemctl restart trading-market-data

# 4. If still failing, switch to backup feed
nano config/system.json
# Switch websocket_url to backup

# 5. Halt trading if no data available
curl -X POST http://localhost:8080/api/v1/circuit-breaker/activate
```

## Getting Help

### Collect Diagnostic Information

```bash
# Run diagnostic collection script
./scripts/collect_diagnostics.sh

# This creates: diagnostics-<timestamp>.tar.gz containing:
# - Service logs
# - Configuration files (with secrets redacted)
# - Metrics snapshots
# - System information
# - Recent errors
```

### Support Channels

1. **GitHub Issues**: https://github.com/SamoraDC/RustAlgorithmTrading/issues
2. **Documentation**: https://github.com/SamoraDC/RustAlgorithmTrading/docs
3. **Email**: davi.samora@example.com

### Include in Support Requests

- System information: `uname -a`
- Version: `git describe --tags`
- Logs: `sudo journalctl -u trading-* --since "1 hour ago"`
- Metrics snapshot: `curl localhost:9090/metrics`
- Configuration (redact secrets): `config/system.json`

## Related Documentation

- [Deployment Guide](deployment.md) - Initial setup and deployment
- [Operations Guide](operations.md) - Day-to-day operations
- [Architecture Documentation](../architecture/) - System design
- [API Documentation](../api/) - API reference
