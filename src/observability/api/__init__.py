"""
FastAPI backend for real-time observability dashboard.
"""
from .main import app, lifespan
from .websocket_manager import WebSocketManager

__all__ = ["app", "lifespan", "WebSocketManager"]
