"""
Tests for Specialized Log Streams

Tests each specialized logger:
- MarketDataLogger
- StrategyLogger
- RiskLogger
- ExecutionLogger
- SystemLogger
"""

import logging
import pytest

from src.observability.logging.streams import (
    MarketDataLogger,
    StrategyLogger,
    RiskLogger,
    ExecutionLogger,
    SystemLogger,
)
from src.observability.config.logging_config import LoggingConfig


@pytest.fixture
def test_config():
    """Create test configuration"""
    return LoggingConfig.for_testing()


class TestMarketDataLogger:
    """Test MarketDataLogger functionality"""

    @pytest.fixture
    def logger(self, test_config):
        return MarketDataLogger(config=test_config)

    def test_price_update(self, logger, caplog):
        """Test price update logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_price_update(
                symbol="BTCUSDT",
                price=45000.0,
                volume=1.5,
                source="binance"
            )

        assert "Price update" in caplog.text
        assert "BTCUSDT" in caplog.text

    def test_orderbook_update(self, logger, caplog):
        """Test order book update logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_orderbook_update(
                symbol="ETHUSDT",
                bid_price=3000.0,
                ask_price=3001.0,
                bid_size=10.0,
                ask_size=8.0
            )

        assert "Order book" in caplog.text
        assert "ETHUSDT" in caplog.text

    def test_trade_logging(self, logger, caplog):
        """Test trade logging"""
        with caplog.at_level(logging.INFO):
            logger.log_trade(
                symbol="BTCUSDT",
                price=45000.0,
                quantity=0.5,
                side="buy"
            )

        assert "Trade" in caplog.text
        assert "BTCUSDT" in caplog.text
        assert "buy" in caplog.text

    def test_feed_status(self, logger, caplog):
        """Test feed status logging"""
        with caplog.at_level(logging.INFO):
            logger.log_feed_status(
                source="binance",
                status="connected",
                message="Successfully connected"
            )

        assert "binance" in caplog.text
        assert "connected" in caplog.text

    def test_data_quality_issue(self, logger, caplog):
        """Test data quality issue logging"""
        with caplog.at_level(logging.WARNING):
            logger.log_data_quality_issue(
                issue_type="stale_data",
                symbol="BTCUSDT",
                details="No updates for 10 seconds"
            )

        assert "Data quality issue" in caplog.text
        assert "stale_data" in caplog.text


class TestStrategyLogger:
    """Test StrategyLogger functionality"""

    @pytest.fixture
    def logger(self, test_config):
        return StrategyLogger(config=test_config)

    def test_signal_logging(self, logger, caplog):
        """Test signal logging"""
        with caplog.at_level(logging.INFO):
            logger.log_signal(
                strategy_name="momentum",
                symbol="BTCUSDT",
                signal_type="buy",
                strength=0.85,
                reason="Strong upward momentum"
            )

        assert "Signal" in caplog.text
        assert "momentum" in caplog.text
        assert "buy" in caplog.text

    def test_trade_decision(self, logger, caplog):
        """Test trade decision logging"""
        with caplog.at_level(logging.INFO):
            logger.log_trade_decision(
                strategy_name="mean_reversion",
                symbol="ETHUSDT",
                action="sell",
                quantity=2.0,
                price=3000.0,
                rationale="Price above upper band"
            )

        assert "Decision" in caplog.text
        assert "mean_reversion" in caplog.text
        assert "sell" in caplog.text

    def test_position_update(self, logger, caplog):
        """Test position update logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_position_update(
                strategy_name="momentum",
                symbol="BTCUSDT",
                position=0.5,
                pnl=250.0
            )

        assert "Position" in caplog.text
        assert "momentum" in caplog.text

    def test_strategy_state(self, logger, caplog):
        """Test strategy state logging"""
        with caplog.at_level(logging.INFO):
            logger.log_strategy_state(
                strategy_name="momentum",
                state="active",
                reason="Market conditions favorable"
            )

        assert "Strategy" in caplog.text
        assert "active" in caplog.text

    def test_performance_metric(self, logger, caplog):
        """Test performance metric logging"""
        with caplog.at_level(logging.INFO):
            logger.log_performance_metric(
                strategy_name="momentum",
                metric_name="sharpe_ratio",
                value=1.8,
                period="30d"
            )

        assert "Performance" in caplog.text
        assert "sharpe_ratio" in caplog.text


class TestRiskLogger:
    """Test RiskLogger functionality"""

    @pytest.fixture
    def logger(self, test_config):
        return RiskLogger(config=test_config)

    def test_risk_check(self, logger, caplog):
        """Test risk check logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_risk_check(
                check_type="position_limit",
                result="passed",
                symbol="BTCUSDT",
                details={'current': 0.5, 'limit': 1.0}
            )

        assert "Risk check" in caplog.text
        assert "passed" in caplog.text

    def test_limit_violation(self, logger, caplog):
        """Test limit violation logging"""
        with caplog.at_level(logging.ERROR):
            logger.log_limit_violation(
                limit_type="max_position",
                limit_value=1.0,
                current_value=1.5,
                symbol="BTCUSDT",
                action_taken="position_reduced"
            )

        assert "LIMIT VIOLATION" in caplog.text
        assert "max_position" in caplog.text

    def test_exposure_update(self, logger, caplog):
        """Test exposure update logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_exposure_update(
                exposure_type="total_notional",
                value=50000.0,
                limit=100000.0
            )

        assert "Exposure" in caplog.text
        assert "total_notional" in caplog.text

    def test_risk_alert(self, logger, caplog):
        """Test risk alert logging"""
        with caplog.at_level(logging.WARNING):
            logger.log_risk_alert(
                alert_type="high_volatility",
                severity="warning",
                message="Market volatility exceeds threshold"
            )

        assert "Risk Alert" in caplog.text
        assert "high_volatility" in caplog.text


class TestExecutionLogger:
    """Test ExecutionLogger functionality"""

    @pytest.fixture
    def logger(self, test_config):
        return ExecutionLogger(config=test_config)

    def test_order_submitted(self, logger, caplog):
        """Test order submission logging"""
        with caplog.at_level(logging.INFO):
            logger.log_order_submitted(
                order_id="order-123",
                symbol="BTCUSDT",
                side="buy",
                quantity=0.5,
                order_type="limit",
                price=45000.0
            )

        assert "Order submitted" in caplog.text
        assert "order-123" in caplog.text

    def test_order_status(self, logger, caplog):
        """Test order status logging"""
        with caplog.at_level(logging.INFO):
            logger.log_order_status(
                order_id="order-123",
                status="filled",
                filled_quantity=0.5
            )

        assert "order-123" in caplog.text
        assert "filled" in caplog.text

    def test_fill_logging(self, logger, caplog):
        """Test fill logging"""
        with caplog.at_level(logging.INFO):
            logger.log_fill(
                order_id="order-123",
                symbol="BTCUSDT",
                quantity=0.5,
                price=45000.0,
                is_partial=False
            )

        assert "Fill" in caplog.text
        assert "order-123" in caplog.text

    def test_execution_quality(self, logger, caplog):
        """Test execution quality logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_execution_quality(
                order_id="order-123",
                metric_name="slippage",
                value=0.02
            )

        assert "Execution quality" in caplog.text
        assert "slippage" in caplog.text

    def test_order_error(self, logger, caplog):
        """Test order error logging"""
        with caplog.at_level(logging.ERROR):
            logger.log_order_error(
                order_id="order-123",
                error_code="INSUFFICIENT_BALANCE",
                error_message="Not enough funds"
            )

        assert "Order error" in caplog.text
        assert "INSUFFICIENT_BALANCE" in caplog.text


class TestSystemLogger:
    """Test SystemLogger functionality"""

    @pytest.fixture
    def logger(self, test_config):
        return SystemLogger(config=test_config)

    def test_startup(self, logger, caplog):
        """Test startup logging"""
        with caplog.at_level(logging.INFO):
            logger.log_startup(
                component="trading_engine",
                version="1.0.0"
            )

        assert "Starting" in caplog.text
        assert "trading_engine" in caplog.text

    def test_shutdown(self, logger, caplog):
        """Test shutdown logging"""
        with caplog.at_level(logging.INFO):
            logger.log_shutdown(
                component="trading_engine",
                reason="User requested"
            )

        assert "Shutting down" in caplog.text
        assert "trading_engine" in caplog.text

    def test_health_check(self, logger, caplog):
        """Test health check logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_health_check(
                component="database",
                status="healthy",
                details={'latency_ms': 5}
            )

        assert "Health check" in caplog.text
        assert "database" in caplog.text
        assert "healthy" in caplog.text

    def test_resource_usage(self, logger, caplog):
        """Test resource usage logging"""
        with caplog.at_level(logging.DEBUG):
            logger.log_resource_usage(
                resource_type="memory",
                value=512.0,
                unit="MB",
                threshold=1024.0
            )

        assert "Resource usage" in caplog.text
        assert "memory" in caplog.text

    def test_config_change(self, logger, caplog):
        """Test config change logging"""
        with caplog.at_level(logging.INFO):
            logger.log_config_change(
                config_key="max_position",
                old_value=1.0,
                new_value=2.0,
                changed_by="admin"
            )

        assert "Config changed" in caplog.text
        assert "max_position" in caplog.text

    def test_critical_error(self, logger, caplog):
        """Test critical error logging"""
        with caplog.at_level(logging.CRITICAL):
            logger.log_critical_error(
                component="order_manager",
                error="Database connection lost",
                recovery_action="Attempting reconnection"
            )

        assert "CRITICAL ERROR" in caplog.text
        assert "order_manager" in caplog.text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
