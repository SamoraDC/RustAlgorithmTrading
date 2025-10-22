"""
Trade history and execution API routes.
"""
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException
from loguru import logger

from ...models.schemas import (
    Trade,
    TradeFilter,
    TradeHistoryResponse
)

router = APIRouter()


@router.get("/", response_model=TradeHistoryResponse)
async def get_trade_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    side: Optional[str] = Query(None, description="Filter by side (buy/sell)"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    limit: int = Query(100, ge=1, le=1000, description="Max trades to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Get trade history with optional filters.

    Returns:
    - Trade details (symbol, side, quantity, price, timestamp)
    - Execution quality metrics (slippage, latency)
    - P&L per trade
    """
    try:
        from ..main import api_state

        execution_collector = api_state.collectors.get("execution")
        if not execution_collector:
            return TradeHistoryResponse(trades=[], total=0, limit=limit, offset=offset)

        # Build filter
        trade_filter = TradeFilter(
            symbol=symbol,
            side=side,
            start_time=start_time or datetime.utcnow() - timedelta(days=1),
            end_time=end_time or datetime.utcnow()
        )

        # Query trades
        trades = await execution_collector.get_trades(
            filter=trade_filter,
            limit=limit,
            offset=offset
        )

        total = await execution_collector.count_trades(filter=trade_filter)

        return TradeHistoryResponse(
            trades=trades,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trade_id}", response_model=Trade)
async def get_trade_details(trade_id: str):
    """Get detailed information for a specific trade."""
    try:
        from ..main import api_state

        execution_collector = api_state.collectors.get("execution")
        if not execution_collector:
            raise HTTPException(status_code=404, detail="Trade not found")

        trade = await execution_collector.get_trade_by_id(trade_id)

        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

        return trade
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_trade_statistics(
    symbol: Optional[str] = Query(None),
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$")
):
    """
    Get aggregated trade statistics.

    Returns:
    - Total trades and volume
    - Average price and size
    - Buy/sell distribution
    - P&L statistics
    - Execution quality metrics
    """
    try:
        from ..main import api_state

        execution_collector = api_state.collectors.get("execution")
        if not execution_collector:
            return {"error": "Execution collector not available"}

        # Parse time range
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)

        stats = await execution_collector.get_trade_statistics(
            symbol=symbol,
            start_time=start_time,
            end_time=now
        )

        return stats
    except Exception as e:
        logger.error(f"Error getting trade statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/quality")
async def get_execution_quality_metrics():
    """
    Get execution quality analysis.

    Returns:
    - Fill rate (% of orders filled)
    - Average slippage (bps)
    - Average latency (ms)
    - Rejection rate
    - Market impact analysis
    """
    try:
        from ..main import api_state

        execution_collector = api_state.collectors.get("execution")
        if not execution_collector:
            return {"error": "Execution collector not available"}

        quality_metrics = await execution_collector.get_execution_quality()

        return quality_metrics
    except Exception as e:
        logger.error(f"Error getting execution quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
