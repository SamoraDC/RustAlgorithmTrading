"""
Python-Rust bridge module for algorithmic trading system.

This module provides integration between Python ML components
and Rust trading engines through:
  - PyO3 bindings for direct function calls
  - ZeroMQ messaging for async communication
"""

from .rust_bridge import (
    MarketBar,
    RustFeatureComputer,
    test_rust_bridge
)

from .zmq_bridge import (
    ZMQPublisher,
    ZMQSubscriber,
    MessageType,
    Signal,
    Position,
    test_zmq_bridge
)

__all__ = [
    # Rust bridge
    "MarketBar",
    "RustFeatureComputer",
    "test_rust_bridge",
    # ZMQ bridge
    "ZMQPublisher",
    "ZMQSubscriber",
    "MessageType",
    "Signal",
    "Position",
    "test_zmq_bridge",
]
