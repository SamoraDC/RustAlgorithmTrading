"""
Metrics API routes for current and historical metrics.
"""
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException
from loguru import logger

from ...models.schemas import (
    MetricsSnapshot,
    MetricsHistoryRequest,
    MetricsHistoryResponse,
    TimeRange
)

router = APIRouter()


@router.get("/current", response_model=MetricsSnapshot)
async def get_current_metrics():
    """
    Get current metrics snapshot across all collectors.

    Returns real-time metrics for:
    - Market data (prices, volumes, spreads)
    - Strategy performance (P&L, positions, signals)
    - Execution metrics (order stats, fills, rejections)
    - System health (CPU, memory, latency)
    """
    try:
        # Import here to avoid circular dependency
        from ..main import api_state

        metrics = await api_state._collect_all_metrics()

        return MetricsSnapshot(
            timestamp=datetime.utcnow(),
            market_data=metrics.get("market_data", {}),
            strategy=metrics.get("strategy", {}),
            execution=metrics.get("execution", {}),
            system=metrics.get("system", {})
        )
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history", response_model=MetricsHistoryResponse)
async def get_metrics_history(request: MetricsHistoryRequest):
    """
    Query historical metrics with time range and filters.

    Supports:
    - Custom time ranges (last hour, day, week, or custom)
    - Metric type filtering (market_data, strategy, execution, system)
    - Symbol filtering
    - Aggregation intervals (1m, 5m, 15m, 1h, 1d)
    """
    try:
        from ..main import api_state

        # Determine time range
        if request.time_range:
            end_time = datetime.utcnow()
            if request.time_range == TimeRange.HOUR_1:
                start_time = end_time - timedelta(hours=1)
            elif request.time_range == TimeRange.HOURS_24:
                start_time = end_time - timedelta(hours=24)
            elif request.time_range == TimeRange.DAYS_7:
                start_time = end_time - timedelta(days=7)
            elif request.time_range == TimeRange.DAYS_30:
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(hours=1)
        else:
            start_time = request.start_time or datetime.utcnow() - timedelta(hours=1)
            end_time = request.end_time or datetime.utcnow()

        # Query from DuckDB
        from ...database import get_db
        db = get_db()

        data = []

        # Query each requested metric type
        if not request.metric_types or "market_data" in request.metric_types:
            market_data = await db.query_market_data(
                start_time,
                end_time,
                symbol=request.symbol,
                interval=request.interval or "1m"
            )
            data.extend([{"type": "market_data", **record} for record in market_data])

        if not request.metric_types or "strategy" in request.metric_types:
            strategy_data = await db.query_strategy_metrics(
                start_time,
                end_time
            )
            data.extend([{"type": "strategy", **record} for record in strategy_data])

        logger.info(
            f"Querying metrics history: {start_time} to {end_time}, "
            f"types={request.metric_types}, interval={request.interval}, "
            f"found {len(data)} records"
        )

        return MetricsHistoryResponse(
            start_time=start_time,
            end_time=end_time,
            interval=request.interval,
            data=data,
            count=len(data)
        )
    except Exception as e:
        logger.error(f"Error querying metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols")
async def get_tracked_symbols():
    """Get list of symbols currently being tracked."""
    try:
        from ..main import api_state

        market_data_collector = api_state.collectors.get("market_data")
        if not market_data_collector:
            return {"symbols": []}

        symbols = await market_data_collector.get_tracked_symbols()

        return {
            "symbols": symbols,
            "count": len(symbols)
        }
    except Exception as e:
        logger.error(f"Error getting tracked symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_metrics_summary():
    """
    Get high-level metrics summary.

    Returns aggregated statistics across all metrics.
    """
    try:
        from ..main import api_state

        metrics = await api_state._collect_all_metrics()

        # Calculate summary statistics
        summary = {
            "timestamp": datetime.utcnow(),
            "market": {
                "symbols_tracked": len(metrics.get("market_data", {}).get("symbols", [])),
                "total_trades": metrics.get("market_data", {}).get("total_trades", 0),
                "total_volume": metrics.get("market_data", {}).get("total_volume", 0.0)
            },
            "strategy": {
                "active_strategies": len(metrics.get("strategy", {}).get("strategies", [])),
                "total_pnl": metrics.get("strategy", {}).get("total_pnl", 0.0),
                "daily_pnl": metrics.get("strategy", {}).get("daily_pnl", 0.0),
                "open_positions": metrics.get("strategy", {}).get("open_positions", 0)
            },
            "execution": {
                "orders_today": metrics.get("execution", {}).get("orders_today", 0),
                "fills_today": metrics.get("execution", {}).get("fills_today", 0),
                "fill_rate": metrics.get("execution", {}).get("fill_rate", 0.0),
                "avg_latency_ms": metrics.get("execution", {}).get("avg_latency_ms", 0.0)
            },
            "system": {
                "cpu_usage": metrics.get("system", {}).get("cpu_percent", 0.0),
                "memory_usage": metrics.get("system", {}).get("memory_percent", 0.0),
                "uptime_seconds": metrics.get("system", {}).get("uptime", 0.0),
                "health_status": metrics.get("system", {}).get("health", "unknown")
            }
        }

        return summary
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
