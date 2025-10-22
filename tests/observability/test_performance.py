"""
Performance and Overhead Tests for Observability Stack.

Tests:
- System overhead <1% on trading system
- Memory usage <200MB
- CPU usage <10%
- Network bandwidth efficiency
- Latency impact on trading operations
"""
import asyncio
import time
from pathlib import Path

import httpx
import psutil
import pytest
import websockets
from loguru import logger


class TestObservabilityPerformance:
    """Performance benchmarks and overhead validation."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    async def api_server(self, project_root: Path):
        """Start API server for performance testing."""
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
    @pytest.mark.performance
    async def test_observability_overhead_under_1_percent(self, api_server):
        """Test that observability adds <1% overhead to system."""
        # Measure baseline CPU usage
        process = psutil.Process(api_server.pid)

        # Let system stabilize
        await asyncio.sleep(2)

        # Sample CPU usage over 10 seconds
        cpu_samples = []

        for _ in range(10):
            cpu_percent = process.cpu_percent(interval=1.0)
            cpu_samples.append(cpu_percent)

        avg_cpu = sum(cpu_samples) / len(cpu_samples)

        logger.info(f"Average CPU usage: {avg_cpu:.2f}%")

        # In idle state, should use very little CPU
        # When streaming metrics, overhead should still be minimal
        assert avg_cpu < 1.0, f"CPU overhead {avg_cpu:.2f}% exceeds 1% target"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_usage_under_200mb(self, api_server):
        """Test that memory usage stays under 200MB."""
        process = psutil.Process(api_server.pid)

        # Let system stabilize
        await asyncio.sleep(2)

        # Measure memory usage
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)

        logger.info(f"Memory usage: {memory_mb:.2f} MB")

        assert memory_mb < 200, f"Memory usage {memory_mb:.2f}MB exceeds 200MB target"

        # Simulate some load and check memory doesn't grow excessively
        async with httpx.AsyncClient() as client:
            for _ in range(100):
                await client.get("http://localhost:8000/health", timeout=2.0)

        # Check memory after load
        memory_info_after = process.memory_info()
        memory_mb_after = memory_info_after.rss / (1024 * 1024)

        logger.info(f"Memory after load: {memory_mb_after:.2f} MB")

        memory_increase = memory_mb_after - memory_mb

        assert memory_increase < 50, (
            f"Memory increased by {memory_increase:.2f}MB after load"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cpu_usage_under_10_percent_under_load(self, api_server):
        """Test CPU usage stays under 10% even under load."""
        process = psutil.Process(api_server.pid)

        # Generate load: multiple concurrent requests
        async def generate_load():
            async with httpx.AsyncClient() as client:
                tasks = []

                for _ in range(100):
                    tasks.append(
                        client.get("http://localhost:8000/health", timeout=5.0)
                    )

                await asyncio.gather(*tasks)

        # Start load generation
        load_task = asyncio.create_task(generate_load())

        # Measure CPU during load
        cpu_samples = []

        for _ in range(5):
            cpu_percent = process.cpu_percent(interval=1.0)
            cpu_samples.append(cpu_percent)

        await load_task

        avg_cpu = sum(cpu_samples) / len(cpu_samples)

        logger.info(f"Average CPU under load: {avg_cpu:.2f}%")

        assert avg_cpu < 10.0, (
            f"CPU usage {avg_cpu:.2f}% exceeds 10% target under load"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_websocket_streaming_bandwidth_efficiency(self, api_server):
        """Test WebSocket streaming is bandwidth efficient."""
        ws_url = "ws://localhost:8000/ws/metrics"

        total_bytes_received = 0
        message_count = 0

        async with websockets.connect(ws_url) as websocket:
            # Receive messages for 2 seconds
            start_time = time.time()

            while time.time() - start_time < 2.0:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=0.2
                    )

                    if message not in ["ping", "pong"]:
                        total_bytes_received += len(message.encode('utf-8'))
                        message_count += 1

                except asyncio.TimeoutError:
                    continue

        # Calculate bandwidth
        duration = 2.0
        bytes_per_second = total_bytes_received / duration
        kb_per_second = bytes_per_second / 1024

        logger.info(
            f"Bandwidth: {kb_per_second:.2f} KB/s "
            f"({message_count} messages in {duration}s)"
        )

        # Should be reasonable bandwidth (<100 KB/s for 10Hz updates)
        assert kb_per_second < 100, (
            f"Bandwidth {kb_per_second:.2f} KB/s exceeds 100 KB/s target"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_api_latency_impact_negligible(self, api_server):
        """Test that API adds negligible latency to requests."""
        async with httpx.AsyncClient() as client:
            latencies = []

            # Measure latency for multiple requests
            for _ in range(100):
                start_time = time.perf_counter()

                response = await client.get(
                    "http://localhost:8000/health",
                    timeout=5.0
                )

                latency_ms = (time.perf_counter() - start_time) * 1000
                latencies.append(latency_ms)

                assert response.status_code == 200

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        logger.info(
            f"Latency - Avg: {avg_latency:.2f}ms, "
            f"P95: {p95_latency:.2f}ms, Max: {max_latency:.2f}ms"
        )

        assert avg_latency < 10, f"Average latency {avg_latency:.2f}ms exceeds 10ms"
        assert p95_latency < 20, f"P95 latency {p95_latency:.2f}ms exceeds 20ms"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_connection_scaling(self, api_server):
        """Test system scales with concurrent connections."""
        ws_url = "ws://localhost:8000/ws/metrics"

        async def test_connection(connection_id: int):
            """Test a single connection."""
            start_time = time.perf_counter()

            try:
                async with websockets.connect(ws_url) as websocket:
                    await websocket.send("ping")
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )

                    connection_time = (time.perf_counter() - start_time) * 1000

                    return {
                        "success": response == "pong",
                        "connection_time_ms": connection_time
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "connection_time_ms": -1
                }

        # Test with increasing concurrent connections
        connection_counts = [10, 50, 100]

        for count in connection_counts:
            start_time = time.perf_counter()

            results = await asyncio.gather(
                *[test_connection(i) for i in range(count)],
                return_exceptions=True
            )

            total_time = (time.perf_counter() - start_time) * 1000

            # Count successes
            successful = sum(
                1 for r in results
                if isinstance(r, dict) and r.get("success")
            )

            success_rate = (successful / count) * 100

            logger.info(
                f"{count} concurrent connections: {success_rate:.1f}% success, "
                f"total time: {total_time:.0f}ms"
            )

            assert success_rate >= 95, (
                f"Success rate {success_rate:.1f}% below 95% for {count} connections"
            )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_disk_io_efficiency(self, api_server, tmp_path: Path):
        """Test disk I/O is efficient for logging and metrics."""
        try:
            import duckdb

            db_path = tmp_path / "perf_test.duckdb"
            conn = duckdb.connect(str(db_path))

            # Create table
            conn.execute(
                """
                CREATE TABLE perf_metrics (
                    timestamp TIMESTAMP,
                    value DOUBLE
                )
                """
            )

            # Measure write performance
            from datetime import datetime

            test_data = [
                (datetime.now(), float(i))
                for i in range(10000)
            ]

            start_time = time.perf_counter()

            conn.executemany(
                "INSERT INTO perf_metrics VALUES (?, ?)",
                test_data
            )

            write_time = (time.perf_counter() - start_time) * 1000

            logger.info(f"Wrote 10k records in {write_time:.2f}ms")

            # Write should be fast
            assert write_time < 500, f"Write time {write_time:.2f}ms exceeds 500ms"

            conn.close()

        except ImportError:
            pytest.skip("DuckDB not installed")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_leak_detection(self, api_server):
        """Test for memory leaks over extended operation."""
        process = psutil.Process(api_server.pid)

        # Baseline memory
        await asyncio.sleep(2)
        baseline_memory = process.memory_info().rss / (1024 * 1024)

        # Generate load for a period
        async with httpx.AsyncClient() as client:
            for cycle in range(10):
                # 100 requests per cycle
                tasks = [
                    client.get("http://localhost:8000/health", timeout=5.0)
                    for _ in range(100)
                ]

                await asyncio.gather(*tasks)

                # Brief pause
                await asyncio.sleep(0.5)

        # Final memory
        final_memory = process.memory_info().rss / (1024 * 1024)

        memory_increase = final_memory - baseline_memory

        logger.info(
            f"Memory: {baseline_memory:.2f}MB → {final_memory:.2f}MB "
            f"(+{memory_increase:.2f}MB)"
        )

        # Memory increase should be minimal (<20MB after 1000 requests)
        assert memory_increase < 20, (
            f"Memory increased by {memory_increase:.2f}MB (possible leak)"
        )

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_startup_time_optimization(self, project_root: Path):
        """Test that API startup time is optimized."""
        start_time = time.perf_counter()

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

        # Wait until service is responsive
        async with httpx.AsyncClient() as client:
            for _ in range(60):
                try:
                    response = await client.get(
                        "http://localhost:8000/health",
                        timeout=2.0
                    )

                    if response.status_code == 200:
                        startup_time = (time.perf_counter() - start_time)

                        logger.info(f"Startup time: {startup_time:.2f}s")

                        assert startup_time < 10, (
                            f"Startup took {startup_time:.2f}s (>10s)"
                        )

                        break

                except (httpx.ConnectError, httpx.TimeoutException):
                    await asyncio.sleep(0.5)

        # Cleanup
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
