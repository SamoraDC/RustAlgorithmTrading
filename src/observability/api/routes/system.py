"""
System health and performance API routes.
"""
from typing import Dict

from fastapi import APIRouter, HTTPException
from loguru import logger

from ...models.schemas import SystemHealth, PerformanceMetrics

router = APIRouter()


@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """
    Get comprehensive system health status.

    Returns:
    - Overall health status (healthy/degraded/unhealthy)
    - Component status (market data, strategy, execution, risk)
    - Resource usage (CPU, memory, disk)
    - Connection status (APIs, databases, message queues)
    - Error rates and alerts
    """
    try:
        from ..main import api_state

        system_collector = api_state.collectors.get("system")
        if not system_collector:
            return SystemHealth(
                status="unknown",
                components={},
                resources={},
                connections={}
            )

        health = await system_collector.get_system_health()

        return health
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """
    Get system performance metrics.

    Returns:
    - Latency percentiles (p50, p95, p99)
    - Throughput (messages/sec, requests/sec)
    - Resource utilization
    - Queue depths and backlogs
    """
    try:
        from ..main import api_state

        system_collector = api_state.collectors.get("system")
        if not system_collector:
            raise HTTPException(status_code=503, detail="System collector not available")

        performance = await system_collector.get_performance_metrics()

        return performance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components")
async def get_component_status():
    """Get status of all system components."""
    try:
        from ..main import api_state

        components = {}

        for name, collector in api_state.collectors.items():
            try:
                status = await collector.get_status()
                components[name] = status
            except Exception as e:
                logger.error(f"Error getting {name} collector status: {e}")
                components[name] = {
                    "status": "error",
                    "error": str(e)
                }

        # Add WebSocket manager status
        components["websocket"] = {
            "status": "healthy" if api_state.websocket_manager.connection_count() >= 0 else "error",
            "connections": api_state.websocket_manager.connection_count(),
            "stats": api_state.websocket_manager.get_stats()
        }

        # Overall status
        all_healthy = all(
            comp.get("status") in ["healthy", "ready"]
            for comp in components.values()
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "components": components,
            "timestamp": "utcnow"
        }
    except Exception as e:
        logger.error(f"Error getting component status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/recent")
async def get_recent_logs(
    level: str = "INFO",
    limit: int = 100
):
    """
    Get recent log entries.

    Args:
        level: Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        limit: Maximum number of log entries
    """
    try:
        from ..main import api_state

        system_collector = api_state.collectors.get("system")
        if not system_collector:
            return {"logs": [], "count": 0}

        logs = await system_collector.get_recent_logs(level=level, limit=limit)

        return {
            "logs": logs,
            "count": len(logs),
            "level": level
        }
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Acknowledge a system alert."""
    try:
        from ..main import api_state

        system_collector = api_state.collectors.get("system")
        if not system_collector:
            raise HTTPException(status_code=503, detail="System collector not available")

        await system_collector.acknowledge_alert(alert_id)

        return {"status": "acknowledged", "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_system_statistics():
    """
    Get comprehensive system statistics.

    Returns aggregate stats across all components.
    """
    try:
        from ..main import api_state

        stats = {
            "api": {
                "running": api_state.running,
                "websocket_connections": api_state.websocket_manager.connection_count(),
                "total_messages_sent": api_state.websocket_manager.total_messages_sent
            },
            "collectors": {}
        }

        for name, collector in api_state.collectors.items():
            try:
                collector_stats = await collector.get_statistics()
                stats["collectors"][name] = collector_stats
            except Exception as e:
                logger.error(f"Error getting {name} stats: {e}")
                stats["collectors"][name] = {"error": str(e)}

        return stats
    except Exception as e:
        logger.error(f"Error getting system statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
