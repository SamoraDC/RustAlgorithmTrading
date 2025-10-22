"""
Base collector interface for metrics collection.

All metric collectors inherit from BaseCollector and implement
the standard interface for lifecycle management and data retrieval.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from loguru import logger


class BaseCollector(ABC):
    """
    Abstract base class for metric collectors.

    Defines the interface that all collectors must implement:
    - Lifecycle: start(), stop()
    - Status: is_ready(), get_status()
    - Data: get_current_metrics(), get_statistics()
    """

    def __init__(self, name: str):
        self.name = name
        self.started = False
        self.start_time: Optional[datetime] = None
        self.metrics_collected = 0
        self.errors = 0

    async def start(self):
        """
        Start the collector.

        Override in subclass to implement initialization logic
        (e.g., connect to data sources, start background tasks).
        """
        logger.info(f"Starting {self.name} collector...")
        self.started = True
        self.start_time = datetime.utcnow()
        await self._start_impl()
        logger.info(f"{self.name} collector started")

    async def stop(self):
        """
        Stop the collector gracefully.

        Override in subclass to implement cleanup logic
        (e.g., disconnect from data sources, stop background tasks).
        """
        logger.info(f"Stopping {self.name} collector...")
        await self._stop_impl()
        self.started = False
        logger.info(f"{self.name} collector stopped")

    @abstractmethod
    async def _start_impl(self):
        """Subclass-specific start implementation."""
        pass

    @abstractmethod
    async def _stop_impl(self):
        """Subclass-specific stop implementation."""
        pass

    def is_ready(self) -> bool:
        """
        Check if collector is ready to serve data.

        Returns:
            bool: True if ready, False otherwise
        """
        return self.started

    async def get_status(self) -> Dict[str, Any]:
        """
        Get collector status.

        Returns:
            dict: Status information including:
                - status: "ready", "starting", "stopped", "error"
                - uptime: seconds since start
                - metrics_collected: total metrics collected
                - errors: total errors encountered
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()

        status = "ready" if self.is_ready() else "stopped"

        return {
            "name": self.name,
            "status": status,
            "uptime_seconds": uptime,
            "metrics_collected": self.metrics_collected,
            "errors": self.errors
        }

    @abstractmethod
    async def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            dict: Current metrics data
        """
        pass

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get collector statistics.

        Returns:
            dict: Statistical summary of collector operation
        """
        status = await self.get_status()
        return {
            "name": self.name,
            "status": status["status"],
            "uptime": status["uptime_seconds"],
            "metrics_collected": self.metrics_collected,
            "errors": self.errors,
            "error_rate": self.errors / max(self.metrics_collected, 1)
        }

    def _increment_metrics_count(self):
        """Increment the metrics collected counter."""
        self.metrics_collected += 1

    def _increment_error_count(self):
        """Increment the error counter."""
        self.errors += 1
