"""
Specialized Log Streams - Domain-specific loggers for trading system

Provides specialized loggers for:
- MarketDataLogger: Market data ingestion and processing
- StrategyLogger: Strategy signals and decisions
- RiskLogger: Risk management checks and violations
- ExecutionLogger: Order execution lifecycle
- SystemLogger: System health and errors
"""

from typing import Any, Dict, Optional
from .structured_logger import StructuredLogger, get_logger
from ..config.logging_config import LoggingConfig


class MarketDataLogger(StructuredLogger):
    """
    Logger for market data ingestion and processing

    Specialized logging for:
    - Price updates
    - Order book changes
    - Trade executions (market)
    - Data feed connectivity
    - Data quality issues
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        """Initialize market data logger"""
        super().__init__("trading.market_data", config)

    def log_price_update(
        self,
        symbol: str,
        price: float,
        volume: float,
        source: str,
        **kwargs
    ):
        """Log price update event"""
        self.debug(
            f"Price update: {symbol} @ {price}",
            extra={
                'event_type': 'price_update',
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'source': source,
                **kwargs
            }
        )

    def log_orderbook_update(
        self,
        symbol: str,
        bid_price: float,
        ask_price: float,
        bid_size: float,
        ask_size: float,
        **kwargs
    ):
        """Log order book update"""
        self.debug(
            f"Order book: {symbol} bid={bid_price}/{bid_size} ask={ask_price}/{ask_size}",
            extra={
                'event_type': 'orderbook_update',
                'symbol': symbol,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'spread': ask_price - bid_price,
                **kwargs
            }
        )

    def log_trade(
        self,
        symbol: str,
        price: float,
        quantity: float,
        side: str,
        **kwargs
    ):
        """Log market trade execution"""
        self.info(
            f"Trade: {symbol} {side} {quantity} @ {price}",
            extra={
                'event_type': 'market_trade',
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'side': side,
                **kwargs
            }
        )

    def log_feed_status(
        self,
        source: str,
        status: str,
        message: Optional[str] = None,
        **kwargs
    ):
        """Log data feed connectivity status"""
        level_map = {
            'connected': self.info,
            'disconnected': self.warning,
            'error': self.error,
            'reconnecting': self.warning,
        }
        log_func = level_map.get(status, self.info)

        log_func(
            f"Feed {source}: {status}" + (f" - {message}" if message else ""),
            extra={
                'event_type': 'feed_status',
                'source': source,
                'status': status,
                'message': message,
                **kwargs
            }
        )

    def log_data_quality_issue(
        self,
        issue_type: str,
        symbol: Optional[str] = None,
        details: Optional[str] = None,
        **kwargs
    ):
        """Log data quality issue"""
        self.warning(
            f"Data quality issue: {issue_type}" + (f" for {symbol}" if symbol else ""),
            extra={
                'event_type': 'data_quality_issue',
                'issue_type': issue_type,
                'symbol': symbol,
                'details': details,
                **kwargs
            }
        )


class StrategyLogger(StructuredLogger):
    """
    Logger for strategy signals and decisions

    Specialized logging for:
    - Signal generation
    - Trade decisions
    - Position updates
    - Strategy state changes
    - Performance metrics
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        """Initialize strategy logger"""
        super().__init__("trading.strategy", config)

    def log_signal(
        self,
        strategy_name: str,
        symbol: str,
        signal_type: str,
        strength: float,
        reason: Optional[str] = None,
        **kwargs
    ):
        """Log trading signal generation"""
        self.info(
            f"Signal: {strategy_name} - {signal_type} {symbol} (strength: {strength})",
            extra={
                'event_type': 'signal',
                'strategy': strategy_name,
                'symbol': symbol,
                'signal_type': signal_type,
                'strength': strength,
                'reason': reason,
                **kwargs
            }
        )

    def log_trade_decision(
        self,
        strategy_name: str,
        symbol: str,
        action: str,
        quantity: float,
        price: Optional[float] = None,
        rationale: Optional[str] = None,
        **kwargs
    ):
        """Log trade decision"""
        self.info(
            f"Decision: {strategy_name} - {action} {quantity} {symbol}" +
            (f" @ {price}" if price else ""),
            extra={
                'event_type': 'trade_decision',
                'strategy': strategy_name,
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'rationale': rationale,
                **kwargs
            }
        )

    def log_position_update(
        self,
        strategy_name: str,
        symbol: str,
        position: float,
        pnl: Optional[float] = None,
        **kwargs
    ):
        """Log position update"""
        self.debug(
            f"Position: {strategy_name} - {symbol} {position}" +
            (f" (PnL: {pnl})" if pnl is not None else ""),
            extra={
                'event_type': 'position_update',
                'strategy': strategy_name,
                'symbol': symbol,
                'position': position,
                'pnl': pnl,
                **kwargs
            }
        )

    def log_strategy_state(
        self,
        strategy_name: str,
        state: str,
        reason: Optional[str] = None,
        **kwargs
    ):
        """Log strategy state change"""
        self.info(
            f"Strategy {strategy_name}: {state}" + (f" - {reason}" if reason else ""),
            extra={
                'event_type': 'strategy_state',
                'strategy': strategy_name,
                'state': state,
                'reason': reason,
                **kwargs
            }
        )

    def log_performance_metric(
        self,
        strategy_name: str,
        metric_name: str,
        value: float,
        period: Optional[str] = None,
        **kwargs
    ):
        """Log performance metric"""
        self.info(
            f"Performance: {strategy_name} - {metric_name}={value}" +
            (f" ({period})" if period else ""),
            extra={
                'event_type': 'performance_metric',
                'strategy': strategy_name,
                'metric_name': metric_name,
                'value': value,
                'period': period,
                **kwargs
            }
        )


class RiskLogger(StructuredLogger):
    """
    Logger for risk management checks and violations

    Specialized logging for:
    - Risk checks (pre-trade, post-trade)
    - Limit violations
    - Exposure updates
    - Risk alerts
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        """Initialize risk logger"""
        super().__init__("trading.risk", config)

    def log_risk_check(
        self,
        check_type: str,
        result: str,
        symbol: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log risk check result"""
        level_map = {
            'passed': self.debug,
            'warning': self.warning,
            'failed': self.error,
        }
        log_func = level_map.get(result, self.info)

        log_func(
            f"Risk check {check_type}: {result}" + (f" for {symbol}" if symbol else ""),
            extra={
                'event_type': 'risk_check',
                'check_type': check_type,
                'result': result,
                'symbol': symbol,
                'details': details or {},
                **kwargs
            }
        )

    def log_limit_violation(
        self,
        limit_type: str,
        limit_value: float,
        current_value: float,
        symbol: Optional[str] = None,
        action_taken: Optional[str] = None,
        **kwargs
    ):
        """Log risk limit violation"""
        self.error(
            f"LIMIT VIOLATION: {limit_type} - limit={limit_value}, current={current_value}" +
            (f" ({symbol})" if symbol else ""),
            extra={
                'event_type': 'limit_violation',
                'limit_type': limit_type,
                'limit_value': limit_value,
                'current_value': current_value,
                'excess': current_value - limit_value,
                'symbol': symbol,
                'action_taken': action_taken,
                **kwargs
            }
        )

    def log_exposure_update(
        self,
        exposure_type: str,
        value: float,
        limit: Optional[float] = None,
        **kwargs
    ):
        """Log exposure update"""
        self.debug(
            f"Exposure {exposure_type}: {value}" +
            (f" / {limit}" if limit else ""),
            extra={
                'event_type': 'exposure_update',
                'exposure_type': exposure_type,
                'value': value,
                'limit': limit,
                'utilization': (value / limit if limit else None),
                **kwargs
            }
        )

    def log_risk_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        **kwargs
    ):
        """Log risk alert"""
        level_map = {
            'info': self.info,
            'warning': self.warning,
            'critical': self.critical,
        }
        log_func = level_map.get(severity, self.warning)

        log_func(
            f"Risk Alert [{alert_type}]: {message}",
            extra={
                'event_type': 'risk_alert',
                'alert_type': alert_type,
                'severity': severity,
                'message': message,
                **kwargs
            }
        )


class ExecutionLogger(StructuredLogger):
    """
    Logger for order execution lifecycle

    Specialized logging for:
    - Order submission
    - Order status updates
    - Fills and partial fills
    - Execution quality metrics
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        """Initialize execution logger"""
        super().__init__("trading.execution", config)

    def log_order_submitted(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None,
        **kwargs
    ):
        """Log order submission"""
        self.info(
            f"Order submitted: {order_id} - {side} {quantity} {symbol} ({order_type})" +
            (f" @ {price}" if price else ""),
            extra={
                'event_type': 'order_submitted',
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                **kwargs
            }
        )

    def log_order_status(
        self,
        order_id: str,
        status: str,
        filled_quantity: Optional[float] = None,
        remaining_quantity: Optional[float] = None,
        **kwargs
    ):
        """Log order status update"""
        self.info(
            f"Order {order_id}: {status}" +
            (f" (filled: {filled_quantity})" if filled_quantity else ""),
            extra={
                'event_type': 'order_status',
                'order_id': order_id,
                'status': status,
                'filled_quantity': filled_quantity,
                'remaining_quantity': remaining_quantity,
                **kwargs
            }
        )

    def log_fill(
        self,
        order_id: str,
        symbol: str,
        quantity: float,
        price: float,
        is_partial: bool = False,
        **kwargs
    ):
        """Log order fill"""
        self.info(
            f"Fill: {order_id} - {quantity} {symbol} @ {price}" +
            (" (partial)" if is_partial else " (complete)"),
            extra={
                'event_type': 'order_fill',
                'order_id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'is_partial': is_partial,
                **kwargs
            }
        )

    def log_execution_quality(
        self,
        order_id: str,
        metric_name: str,
        value: float,
        **kwargs
    ):
        """Log execution quality metric"""
        self.debug(
            f"Execution quality: {order_id} - {metric_name}={value}",
            extra={
                'event_type': 'execution_quality',
                'order_id': order_id,
                'metric_name': metric_name,
                'value': value,
                **kwargs
            }
        )

    def log_order_error(
        self,
        order_id: str,
        error_code: str,
        error_message: str,
        **kwargs
    ):
        """Log order execution error"""
        self.error(
            f"Order error: {order_id} - {error_code}: {error_message}",
            extra={
                'event_type': 'order_error',
                'order_id': order_id,
                'error_code': error_code,
                'error_message': error_message,
                **kwargs
            }
        )


class SystemLogger(StructuredLogger):
    """
    Logger for system health and errors

    Specialized logging for:
    - System startup/shutdown
    - Component health checks
    - Resource usage
    - Configuration changes
    - Critical errors
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        """Initialize system logger"""
        super().__init__("trading.system", config)

    def log_startup(self, component: str, version: str, **kwargs):
        """Log component startup"""
        self.info(
            f"Starting {component} v{version}",
            extra={
                'event_type': 'startup',
                'component': component,
                'version': version,
                **kwargs
            }
        )

    def log_shutdown(self, component: str, reason: Optional[str] = None, **kwargs):
        """Log component shutdown"""
        self.info(
            f"Shutting down {component}" + (f": {reason}" if reason else ""),
            extra={
                'event_type': 'shutdown',
                'component': component,
                'reason': reason,
                **kwargs
            }
        )

    def log_health_check(
        self,
        component: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log health check result"""
        level_map = {
            'healthy': self.debug,
            'degraded': self.warning,
            'unhealthy': self.error,
        }
        log_func = level_map.get(status, self.info)

        log_func(
            f"Health check: {component} is {status}",
            extra={
                'event_type': 'health_check',
                'component': component,
                'status': status,
                'details': details or {},
                **kwargs
            }
        )

    def log_resource_usage(
        self,
        resource_type: str,
        value: float,
        unit: str,
        threshold: Optional[float] = None,
        **kwargs
    ):
        """Log resource usage"""
        level = self.warning if (threshold and value > threshold) else self.debug
        level(
            f"Resource usage: {resource_type}={value}{unit}",
            extra={
                'event_type': 'resource_usage',
                'resource_type': resource_type,
                'value': value,
                'unit': unit,
                'threshold': threshold,
                **kwargs
            }
        )

    def log_config_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        changed_by: Optional[str] = None,
        **kwargs
    ):
        """Log configuration change"""
        self.info(
            f"Config changed: {config_key} = {new_value} (was: {old_value})",
            extra={
                'event_type': 'config_change',
                'config_key': config_key,
                'old_value': old_value,
                'new_value': new_value,
                'changed_by': changed_by,
                **kwargs
            }
        )

    def log_critical_error(
        self,
        component: str,
        error: str,
        recovery_action: Optional[str] = None,
        **kwargs
    ):
        """Log critical system error"""
        self.critical(
            f"CRITICAL ERROR in {component}: {error}" +
            (f" - Recovery: {recovery_action}" if recovery_action else ""),
            extra={
                'event_type': 'critical_error',
                'component': component,
                'error': error,
                'recovery_action': recovery_action,
                **kwargs
            }
        )
