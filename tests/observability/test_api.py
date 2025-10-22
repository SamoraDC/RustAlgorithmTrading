"""
API Endpoint and WebSocket Tests.

Tests:
- REST endpoints return 200
- WebSocket connection and streaming
- Metric streaming at 10Hz
- Concurrent connections (100+)
"""
import asyncio
import json
import time
from pathlib import Path
from typing import List

import httpx
import pytest
import websockets
from loguru import logger


class TestObservabilityAPI:
    """Test REST API endpoints and WebSocket streaming."""

    @pytest.fixture
    def api_base_url(self) -> str:
        """Base URL for API."""
        return "http://localhost:8000"

    @pytest.fixture
    async def api_server(self):
        """Start API server for testing."""
        project_root = Path(__file__).parent.parent.parent

        process = await asyncio.create_subprocess_exec(
            "python",
            "-m",
            "uvicorn",
            "src.observability.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for startup
        await asyncio.sleep(3)

        yield process

        # Cleanup
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_health_endpoint_returns_200(self, api_server, api_base_url: str):
        """Test /health endpoint returns 200."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/health", timeout=5.0)

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_root_endpoint_returns_service_info(
        self, api_server, api_base_url: str
    ):
        """Test root endpoint returns API information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/", timeout=5.0)

            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            assert "version" in data
            assert "endpoints" in data
            assert data["service"] == "Trading Observability API"

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_readiness_endpoint(self, api_server, api_base_url: str):
        """Test /health/ready endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/health/ready", timeout=5.0)

            # Status can be 200 (ready) or 503 (not ready)
            assert response.status_code in [200, 503]
            data = response.json()
            assert "ready" in data
            assert "collectors" in data

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_liveness_endpoint(self, api_server, api_base_url: str):
        """Test /health/live endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/health/live", timeout=5.0)

            assert response.status_code == 200
            data = response.json()
            assert "alive" in data
            assert data["alive"] is True
            assert "websocket_connections" in data
            assert "uptime_seconds" in data

    @pytest.mark.asyncio
    @pytest.mark.websocket
    async def test_websocket_connection_succeeds(self, api_server):
        """Test WebSocket connection establishment."""
        ws_url = "ws://localhost:8000/ws/metrics"

        try:
            async with websockets.connect(ws_url) as websocket:
                # Send ping
                await websocket.send("ping")

                # Receive pong
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5.0
                )

                assert response == "pong"

        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_metric_streaming_at_10hz(self, api_server):
        """Test that metrics are streamed at 10Hz (every 100ms)."""
        ws_url = "ws://localhost:8000/ws/metrics"

        received_messages: List[float] = []

        async with websockets.connect(ws_url) as websocket:
            # Collect messages for 2 seconds
            start_time = time.time()
            duration = 2.0

            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=0.2
                    )

                    # Record receive timestamp
                    received_messages.append(time.time())

                except asyncio.TimeoutError:
                    continue

        # Should receive ~20 messages in 2 seconds (10Hz)
        expected_count = int(duration * 10)
        tolerance = 0.3  # 30% tolerance

        logger.info(
            f"Received {len(received_messages)} messages in {duration}s "
            f"(expected ~{expected_count})"
        )

        assert len(received_messages) >= expected_count * (1 - tolerance)
        assert len(received_messages) <= expected_count * (1 + tolerance)

        # Verify timing intervals (should be ~100ms)
        if len(received_messages) > 1:
            intervals = [
                (received_messages[i] - received_messages[i-1]) * 1000
                for i in range(1, len(received_messages))
            ]

            avg_interval = sum(intervals) / len(intervals)
            logger.info(f"Average interval: {avg_interval:.2f}ms")

            # Should be close to 100ms with some tolerance
            assert 80 <= avg_interval <= 150, (
                f"Average interval {avg_interval:.2f}ms not in 80-150ms range"
            )

    @pytest.mark.asyncio
    @pytest.mark.websocket
    @pytest.mark.performance
    async def test_concurrent_websocket_connections(self, api_server):
        """Test handling 100+ concurrent WebSocket connections."""
        ws_url = "ws://localhost:8000/ws/metrics"
        num_connections = 100

        async def create_connection(connection_id: int):
            """Create and maintain a WebSocket connection."""
            try:
                async with websockets.connect(ws_url) as websocket:
                    # Send ping to verify connection
                    await websocket.send("ping")
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    return response == "pong"
            except Exception as e:
                logger.error(f"Connection {connection_id} failed: {e}")
                return False

        # Create connections concurrently
        start_time = time.time()

        results = await asyncio.gather(
            *[create_connection(i) for i in range(num_connections)],
            return_exceptions=True
        )

        elapsed = time.time() - start_time

        # Count successful connections
        successful = sum(1 for r in results if r is True)

        logger.info(
            f"Established {successful}/{num_connections} connections "
            f"in {elapsed:.2f}s"
        )

        # Should successfully handle at least 95% of connections
        assert successful >= num_connections * 0.95, (
            f"Only {successful}/{num_connections} connections succeeded"
        )

    @pytest.mark.asyncio
    @pytest.mark.websocket
    async def test_websocket_message_format(self, api_server):
        """Test that WebSocket messages have correct JSON format."""
        ws_url = "ws://localhost:8000/ws/metrics"

        async with websockets.connect(ws_url) as websocket:
            # Wait for a metric message
            for _ in range(10):
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=1.0
                    )

                    # Skip ping/pong messages
                    if message in ["ping", "pong"]:
                        continue

                    # Parse JSON
                    data = json.loads(message)

                    # Verify structure
                    assert "timestamp" in data
                    assert isinstance(data["timestamp"], (int, float))

                    # Should have metric categories
                    assert any(
                        key in data
                        for key in ["market_data", "strategy", "execution", "system"]
                    )

                    logger.info(f"Received valid metric message: {len(message)} bytes")
                    return

                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in WebSocket message: {e}")

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_api_metrics_endpoint(self, api_server, api_base_url: str):
        """Test /api/metrics endpoint (if exists)."""
        async with httpx.AsyncClient() as client:
            # Try to get metrics
            try:
                response = await client.get(
                    f"{api_base_url}/api/metrics",
                    timeout=5.0
                )

                # Endpoint should exist or return 404
                assert response.status_code in [200, 404]

                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, (dict, list))

            except httpx.ConnectError:
                pytest.skip("Metrics endpoint not implemented")

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_cors_headers(self, api_server, api_base_url: str):
        """Test that CORS headers are properly set."""
        async with httpx.AsyncClient() as client:
            response = await client.options(
                f"{api_base_url}/health",
                headers={"Origin": "http://localhost:3000"},
                timeout=5.0
            )

            # CORS preflight should succeed
            assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_response_latency(self, api_server, api_base_url: str):
        """Test that API responses are under 50ms."""
        async with httpx.AsyncClient() as client:
            endpoints = ["/health", "/health/live", "/"]

            for endpoint in endpoints:
                start_time = time.perf_counter()

                response = await client.get(
                    f"{api_base_url}{endpoint}",
                    timeout=5.0
                )

                latency_ms = (time.perf_counter() - start_time) * 1000

                assert response.status_code == 200
                assert latency_ms < 50, (
                    f"{endpoint} latency {latency_ms:.2f}ms > 50ms"
                )

                logger.info(f"{endpoint} responded in {latency_ms:.2f}ms")

    @pytest.mark.asyncio
    @pytest.mark.websocket
    async def test_websocket_reconnection(self, api_server):
        """Test WebSocket automatic reconnection handling."""
        ws_url = "ws://localhost:8000/ws/metrics"

        # First connection
        async with websockets.connect(ws_url) as ws1:
            await ws1.send("ping")
            response1 = await ws1.recv()
            assert response1 == "pong"

        # Wait briefly
        await asyncio.sleep(0.5)

        # Second connection (reconnect)
        async with websockets.connect(ws_url) as ws2:
            await ws2.send("ping")
            response2 = await ws2.recv()
            assert response2 == "pong"
