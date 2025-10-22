"""
Logging Configuration - Centralized logging settings

Provides configuration for:
- Log levels per stream
- Output destinations
- Rotation policies
- Retention settings
- Performance tuning
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional


class LoggingConfig:
    """
    Centralized logging configuration

    Manages:
    - Log levels for each logger stream
    - Output destinations (console, file, syslog)
    - File rotation and retention
    - Performance parameters
    """

    def __init__(
        self,
        # Global settings
        base_log_dir: str = "logs",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,

        # Stream-specific levels
        market_data_level: int = logging.DEBUG,
        strategy_level: int = logging.INFO,
        risk_level: int = logging.INFO,
        execution_level: int = logging.INFO,
        system_level: int = logging.INFO,

        # File output settings
        file_output_enabled: bool = True,
        max_file_size: int = 100 * 1024 * 1024,  # 100 MB
        backup_count: int = 10,

        # Performance settings
        async_enabled: bool = True,
        queue_size: int = 10000,
        batch_size: int = 100,
        flush_interval: float = 0.1,

        # Format settings
        json_output: bool = True,
        include_traceback: bool = True,
        colored_output: bool = True,
    ):
        """
        Initialize logging configuration

        Args:
            base_log_dir: Base directory for log files
            console_level: Minimum level for console output
            file_level: Minimum level for file output
            market_data_level: Level for market data logs
            strategy_level: Level for strategy logs
            risk_level: Level for risk logs
            execution_level: Level for execution logs
            system_level: Level for system logs
            file_output_enabled: Enable file output
            max_file_size: Maximum size per log file
            backup_count: Number of backup files to keep
            async_enabled: Enable async logging
            queue_size: Queue size for async handler
            batch_size: Batch size for processing
            flush_interval: Flush interval for batches
            json_output: Output JSON format
            include_traceback: Include exception tracebacks
            colored_output: Use colored console output
        """
        # Global settings
        self.base_log_dir = Path(base_log_dir)
        self.console_level = console_level
        self.file_level = file_level

        # Stream-specific levels
        self.stream_levels = {
            'trading.market_data': market_data_level,
            'trading.strategy': strategy_level,
            'trading.risk': risk_level,
            'trading.execution': execution_level,
            'trading.system': system_level,
        }

        # File output settings
        self.file_output_enabled = file_output_enabled
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        # Performance settings
        self.async_enabled = async_enabled
        self.queue_size = queue_size
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # Format settings
        self.json_output = json_output
        self.include_traceback = include_traceback
        self.colored_output = colored_output

        # Ensure log directory exists
        self.base_log_dir.mkdir(parents=True, exist_ok=True)

    def get_level(self, logger_name: str) -> int:
        """
        Get log level for a specific logger

        Args:
            logger_name: Logger name (e.g., 'trading.market_data')

        Returns:
            Log level (e.g., logging.DEBUG)
        """
        # Check for exact match
        if logger_name in self.stream_levels:
            return self.stream_levels[logger_name]

        # Check for parent match (e.g., 'trading.market_data.binance')
        for parent_name, level in self.stream_levels.items():
            if logger_name.startswith(parent_name + '.'):
                return level

        # Default to INFO
        return logging.INFO

    def get_log_file_path(self, logger_name: str) -> Path:
        """
        Get log file path for a logger

        Args:
            logger_name: Logger name

        Returns:
            Path to log file
        """
        # Create subdirectory for each major stream
        stream_name = logger_name.split('.')[1] if '.' in logger_name else logger_name
        stream_dir = self.base_log_dir / stream_name
        stream_dir.mkdir(parents=True, exist_ok=True)

        # Create log file name
        log_file = stream_dir / f"{logger_name}.log"
        return log_file

    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """
        Create configuration from environment variables

        Environment variables:
        - LOG_DIR: Base log directory
        - LOG_LEVEL: Global log level
        - LOG_CONSOLE_LEVEL: Console log level
        - LOG_FILE_LEVEL: File log level
        - LOG_MARKET_DATA_LEVEL: Market data log level
        - LOG_STRATEGY_LEVEL: Strategy log level
        - LOG_RISK_LEVEL: Risk log level
        - LOG_EXECUTION_LEVEL: Execution log level
        - LOG_SYSTEM_LEVEL: System log level
        - LOG_FILE_ENABLED: Enable file output (true/false)
        - LOG_ASYNC_ENABLED: Enable async logging (true/false)
        - LOG_JSON_OUTPUT: Output JSON format (true/false)
        """
        def get_log_level(env_var: str, default: int) -> int:
            """Get log level from environment variable"""
            level_str = os.getenv(env_var)
            if level_str:
                return getattr(logging, level_str.upper(), default)
            return default

        def get_bool(env_var: str, default: bool) -> bool:
            """Get boolean from environment variable"""
            value = os.getenv(env_var)
            if value:
                return value.lower() in ('true', '1', 'yes', 'on')
            return default

        return cls(
            base_log_dir=os.getenv('LOG_DIR', 'logs'),
            console_level=get_log_level('LOG_CONSOLE_LEVEL', logging.INFO),
            file_level=get_log_level('LOG_FILE_LEVEL', logging.DEBUG),
            market_data_level=get_log_level('LOG_MARKET_DATA_LEVEL', logging.DEBUG),
            strategy_level=get_log_level('LOG_STRATEGY_LEVEL', logging.INFO),
            risk_level=get_log_level('LOG_RISK_LEVEL', logging.INFO),
            execution_level=get_log_level('LOG_EXECUTION_LEVEL', logging.INFO),
            system_level=get_log_level('LOG_SYSTEM_LEVEL', logging.INFO),
            file_output_enabled=get_bool('LOG_FILE_ENABLED', True),
            async_enabled=get_bool('LOG_ASYNC_ENABLED', True),
            json_output=get_bool('LOG_JSON_OUTPUT', True),
        )

    @classmethod
    def get_default(cls) -> 'LoggingConfig':
        """Get default configuration"""
        return cls()

    @classmethod
    def for_development(cls) -> 'LoggingConfig':
        """Get development configuration (more verbose, colored output)"""
        return cls(
            console_level=logging.DEBUG,
            market_data_level=logging.DEBUG,
            strategy_level=logging.DEBUG,
            risk_level=logging.DEBUG,
            execution_level=logging.DEBUG,
            system_level=logging.DEBUG,
            colored_output=True,
            json_output=False,
        )

    @classmethod
    def for_production(cls) -> 'LoggingConfig':
        """Get production configuration (optimized, JSON output)"""
        return cls(
            console_level=logging.INFO,
            file_level=logging.INFO,
            market_data_level=logging.INFO,
            strategy_level=logging.INFO,
            risk_level=logging.WARNING,
            execution_level=logging.INFO,
            system_level=logging.INFO,
            colored_output=False,
            json_output=True,
            async_enabled=True,
            queue_size=50000,
            batch_size=500,
        )

    @classmethod
    def for_testing(cls) -> 'LoggingConfig':
        """Get testing configuration (minimal output)"""
        return cls(
            base_log_dir="test_logs",
            console_level=logging.WARNING,
            file_level=logging.DEBUG,
            file_output_enabled=False,
            async_enabled=False,
        )

    def to_dict(self) -> Dict:
        """Export configuration as dictionary"""
        return {
            'base_log_dir': str(self.base_log_dir),
            'console_level': logging.getLevelName(self.console_level),
            'file_level': logging.getLevelName(self.file_level),
            'stream_levels': {
                name: logging.getLevelName(level)
                for name, level in self.stream_levels.items()
            },
            'file_output_enabled': self.file_output_enabled,
            'max_file_size': self.max_file_size,
            'backup_count': self.backup_count,
            'async_enabled': self.async_enabled,
            'queue_size': self.queue_size,
            'batch_size': self.batch_size,
            'flush_interval': self.flush_interval,
            'json_output': self.json_output,
            'include_traceback': self.include_traceback,
            'colored_output': self.colored_output,
        }
