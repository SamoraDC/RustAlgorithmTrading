# Logging Infrastructure Guide

## Overview

The observability logging infrastructure provides production-grade, structured logging with:

- **Async, non-blocking logging** (< 1ms overhead)
- **Correlation ID tracking** for distributed tracing
- **Specialized log streams** for different system components
- **Performance metrics** and monitoring
- **Graceful degradation** on errors
- **Thread-safe** concurrent operations

## Quick Start

### Basic Usage

```python
from src.observability import get_logger, correlation_id

# Get a logger instance
logger = get_logger("trading.my_component")

# Basic logging
logger.info("Processing started")
logger.debug("Detailed debug information")
logger.warning("Something unusual happened")
logger.error("An error occurred", exc_info=True)

# Structured logging with context
logger.info(
    "Trade executed",
    extra={
        'symbol': 'BTCUSDT',
        'price': 45000.0,
        'quantity': 0.5,
    }
)

# Correlation ID tracking
with correlation_id("req-123"):
    logger.info("Processing request")  # Includes correlation_id
    process_data()  # Nested calls inherit correlation_id
```

### Using Specialized Loggers

```python
from src.observability import (
    MarketDataLogger,
    StrategyLogger,
    RiskLogger,
    ExecutionLogger,
    SystemLogger,
)

# Market data logging
market_logger = MarketDataLogger()
market_logger.log_price_update(
    symbol="BTCUSDT",
    price=45000.0,
    volume=1.5,
    source="binance"
)

# Strategy logging
strategy_logger = StrategyLogger()
strategy_logger.log_signal(
    strategy_name="momentum",
    symbol="BTCUSDT",
    signal_type="buy",
    strength=0.85,
    reason="Strong upward momentum"
)

# Risk logging
risk_logger = RiskLogger()
risk_logger.log_limit_violation(
    limit_type="max_position",
    limit_value=1.0,
    current_value=1.5,
    symbol="BTCUSDT"
)

# Execution logging
exec_logger = ExecutionLogger()
exec_logger.log_order_submitted(
    order_id="order-123",
    symbol="BTCUSDT",
    side="buy",
    quantity=0.5,
    order_type="limit",
    price=45000.0
)

# System logging
system_logger = SystemLogger()
system_logger.log_startup(
    component="trading_engine",
    version="1.0.0"
)
```

## Configuration

### Environment-Based Configuration

```bash
# Set via environment variables
export LOG_DIR="logs"
export LOG_LEVEL="INFO"
export LOG_CONSOLE_LEVEL="INFO"
export LOG_FILE_LEVEL="DEBUG"
export LOG_MARKET_DATA_LEVEL="DEBUG"
export LOG_STRATEGY_LEVEL="INFO"
export LOG_FILE_ENABLED="true"
export LOG_ASYNC_ENABLED="true"
export LOG_JSON_OUTPUT="true"
```

```python
from src.observability.config import LoggingConfig

# Load from environment
config = LoggingConfig.from_env()
logger = get_logger("my_component", config=config)
```

### Programmatic Configuration

```python
from src.observability.config import LoggingConfig
import logging

# Development configuration
config = LoggingConfig.for_development()

# Production configuration
config = LoggingConfig.for_production()

# Custom configuration
config = LoggingConfig(
    base_log_dir="custom_logs",
    console_level=logging.INFO,
    file_level=logging.DEBUG,
    market_data_level=logging.DEBUG,
    strategy_level=logging.INFO,
    max_file_size=200 * 1024 * 1024,  # 200 MB
    backup_count=20,
    async_enabled=True,
    json_output=True,
)

logger = get_logger("my_component", config=config)
```

## Advanced Features

### Correlation ID Tracking

Correlation IDs enable tracking requests across async operations and service boundaries:

```python
from src.observability import correlation_id, get_logger

logger = get_logger("trading.api")

async def handle_request(request_id: str):
    # Set correlation ID for entire request lifecycle
    with correlation_id(request_id) as cid:
        logger.info(f"Processing request {cid}")

        # All nested calls inherit correlation ID
        await validate_request()
        await execute_trade()
        await send_response()

        logger.info(f"Request {cid} completed")

# Extract from HTTP headers
from src.observability.logging.correlations import (
    extract_correlation_id_from_headers,
    inject_correlation_id_into_headers,
)

# Incoming request
cid = extract_correlation_id_from_headers(request.headers)
with correlation_id(cid):
    process_request()

# Outgoing request
headers = inject_correlation_id_into_headers(headers)
```

### Performance Monitoring

```python
from src.observability import log_execution_time

# Decorator to log execution time
@log_execution_time(threshold_ms=100, log_args=True)
async def fetch_market_data(symbol: str):
    """Only logs if execution exceeds 100ms"""
    data = await api.fetch(symbol)
    return data

# Get logger metrics
logger = get_logger("trading.engine")
metrics = logger.get_metrics()
print(f"Total logs: {metrics['total_logs']}")
print(f"Average latency: {metrics['average_latency_ms']:.2f}ms")
print(f"Error rate: {metrics['error_rate']:.2%}")

# Reset metrics
logger.reset_metrics()
```

### Error Logging with Context

```python
from src.observability import log_error_with_context

try:
    execute_trade(order)
except Exception as e:
    log_error_with_context(
        error=e,
        context={
            'operation': 'execute_trade',
            'order_id': order.id,
            'symbol': order.symbol,
            'quantity': order.quantity,
        },
        logger_name="trading.execution",
        severity="critical"
    )
```

### Custom Context Enrichment

```python
from src.observability.logging.decorators import LogContext

# Add context to all logs within block
with LogContext({'user_id': '123', 'session_id': 'abc'}):
    logger.info("User action")  # Includes user_id and session_id
    process_user_request()

# Decorator for automatic correlation ID
from src.observability.logging.decorators import with_correlation_id

@with_correlation_id
async def handle_request(data):
    logger.info("Processing")  # Automatically has correlation_id
    await process(data)
```

## Log Streams

### MarketDataLogger

For market data ingestion and processing:

```python
market_logger = MarketDataLogger()

# Price updates
market_logger.log_price_update(symbol, price, volume, source)

# Order book updates
market_logger.log_orderbook_update(symbol, bid_price, ask_price, bid_size, ask_size)

# Market trades
market_logger.log_trade(symbol, price, quantity, side)

# Feed connectivity
market_logger.log_feed_status(source, status, message)

# Data quality issues
market_logger.log_data_quality_issue(issue_type, symbol, details)
```

### StrategyLogger

For strategy signals and decisions:

```python
strategy_logger = StrategyLogger()

# Trading signals
strategy_logger.log_signal(strategy_name, symbol, signal_type, strength, reason)

# Trade decisions
strategy_logger.log_trade_decision(strategy_name, symbol, action, quantity, price, rationale)

# Position updates
strategy_logger.log_position_update(strategy_name, symbol, position, pnl)

# Strategy state changes
strategy_logger.log_strategy_state(strategy_name, state, reason)

# Performance metrics
strategy_logger.log_performance_metric(strategy_name, metric_name, value, period)
```

### RiskLogger

For risk management checks:

```python
risk_logger = RiskLogger()

# Risk checks
risk_logger.log_risk_check(check_type, result, symbol, details)

# Limit violations
risk_logger.log_limit_violation(limit_type, limit_value, current_value, symbol, action_taken)

# Exposure updates
risk_logger.log_exposure_update(exposure_type, value, limit)

# Risk alerts
risk_logger.log_risk_alert(alert_type, severity, message)
```

### ExecutionLogger

For order execution lifecycle:

```python
exec_logger = ExecutionLogger()

# Order submission
exec_logger.log_order_submitted(order_id, symbol, side, quantity, order_type, price)

# Order status updates
exec_logger.log_order_status(order_id, status, filled_quantity, remaining_quantity)

# Fills
exec_logger.log_fill(order_id, symbol, quantity, price, is_partial)

# Execution quality
exec_logger.log_execution_quality(order_id, metric_name, value)

# Order errors
exec_logger.log_order_error(order_id, error_code, error_message)
```

### SystemLogger

For system health and errors:

```python
system_logger = SystemLogger()

# Component lifecycle
system_logger.log_startup(component, version)
system_logger.log_shutdown(component, reason)

# Health checks
system_logger.log_health_check(component, status, details)

# Resource usage
system_logger.log_resource_usage(resource_type, value, unit, threshold)

# Configuration changes
system_logger.log_config_change(config_key, old_value, new_value, changed_by)

# Critical errors
system_logger.log_critical_error(component, error, recovery_action)
```

## Output Formats

### JSON Format (Production)

```json
{
  "timestamp": "2025-10-21T22:10:00.000Z",
  "level": "INFO",
  "logger": "trading.strategy",
  "message": "Trade Decision: momentum - buy 0.5 BTCUSDT @ 45000.0",
  "correlation_id": "req-123",
  "module": "strategy_engine",
  "function": "execute_strategy",
  "line": 42,
  "extra": {
    "event_type": "trade_decision",
    "strategy": "momentum",
    "symbol": "BTCUSDT",
    "action": "buy",
    "quantity": 0.5,
    "price": 45000.0
  }
}
```

### Human-Readable Format (Development)

```
[2025-10-21 22:10:00.000] INFO [trading.strategy] [req-123] Trade Decision: momentum - buy 0.5 BTCUSDT @ 45000.0
  → event_type: trade_decision
  → strategy: momentum
  → symbol: BTCUSDT
  → action: buy
  → quantity: 0.5
  → price: 45000.0
```

## Performance Characteristics

- **Logging overhead**: < 1ms per log entry
- **Async queue processing**: Non-blocking, batch-based
- **Queue size**: 10,000 records (configurable)
- **Batch size**: 100 records (configurable)
- **Flush interval**: 0.1 seconds (configurable)
- **Thread-safe**: Supports concurrent logging
- **Graceful degradation**: Continues on disk full or handler errors

## File Organization

Logs are organized by stream:

```
logs/
  market_data/
    trading.market_data.log
    trading.market_data.log.1
    trading.market_data.log.2
  strategy/
    trading.strategy.log
    trading.strategy.log.1
  risk/
    trading.risk.log
  execution/
    trading.execution.log
  system/
    trading.system.log
```

## Integration with Log Aggregation

### Elasticsearch/Logstash

```python
# JSON output is compatible with ELK stack
config = LoggingConfig(
    json_output=True,
    file_output_enabled=True
)

# Logstash can tail log files or use syslog handler
```

### Syslog

```python
from src.observability.logging.handlers import SyslogHandlerAsync

# Add syslog handler to logger
syslog_handler = SyslogHandlerAsync(
    address=('logs.example.com', 514)
)
logger._logger.addHandler(syslog_handler)
```

## Best Practices

1. **Use correlation IDs**: Always use correlation IDs for request tracking
2. **Choose appropriate log levels**: DEBUG for detailed info, INFO for key events, WARNING for issues, ERROR for failures
3. **Use specialized loggers**: Use domain-specific loggers (MarketDataLogger, StrategyLogger, etc.) for consistent format
4. **Include context**: Always add relevant context via `extra` parameter
5. **Monitor metrics**: Regularly check logger metrics for performance issues
6. **Test log output**: Write tests that verify log output for critical operations
7. **Structured logging**: Use structured logs with consistent field names
8. **Avoid PII**: Don't log sensitive personal information
9. **Performance-critical paths**: Use async logging in hot paths
10. **Error handling**: Always include `exc_info=True` when logging exceptions

## Troubleshooting

### High latency

Check logger metrics and adjust configuration:

```python
metrics = logger.get_metrics()
if metrics['average_latency_ms'] > 1.0:
    # Increase queue size or batch size
    config.queue_size = 50000
    config.batch_size = 500
```

### Dropped logs

Check queue status:

```python
# Logs are dropped when queue is full
metrics = logger.get_metrics()
print(f"Drop rate: {metrics['drop_rate']:.2%}")

# Increase queue size if drops occur
config.queue_size = 50000
```

### Disk full

Logging gracefully handles disk full errors:

```python
# Configure rotation to prevent disk full
config.max_file_size = 100 * 1024 * 1024  # 100 MB
config.backup_count = 10  # Keep 10 backups
```

## Testing

```python
import pytest
from src.observability import get_logger

def test_logging(caplog):
    logger = get_logger("test")

    with caplog.at_level(logging.INFO):
        logger.info("Test message")

    assert "Test message" in caplog.text
```

## Summary

The logging infrastructure provides:

✅ **Production-ready**: Async, performant, reliable
✅ **Structured**: Consistent JSON output
✅ **Traceable**: Correlation ID tracking
✅ **Specialized**: Domain-specific loggers
✅ **Observable**: Built-in metrics
✅ **Resilient**: Graceful error handling

For questions or issues, refer to the implementation in `/src/observability/logging/`.
