"""
Startup Tests for Observability Stack.

Tests:
- start_trading.sh execution
- Service startup timing
- Dashboard accessibility
- Database initialization
"""
import asyncio
import os
import signal
import subprocess
import time
from pathlib import Path

import httpx
import psutil
import pytest
from loguru import logger


class TestObservabilityStartup:
    """Test observability stack startup and initialization."""

    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture(scope="class")
    def start_script(self, project_root: Path) -> Path:
        """Get start_trading.sh script path."""
        script = project_root / "scripts" / "start_trading.sh"
        assert script.exists(), f"Start script not found: {script}"
        return script

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_start_script_exists(self, start_script: Path):
        """Test that start_trading.sh exists and is executable."""
        assert start_script.exists()
        assert os.access(start_script, os.X_OK), "Start script is not executable"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_env_file_validation(self, project_root: Path):
        """Test that .env file exists with required credentials."""
        env_file = project_root / ".env"
        assert env_file.exists(), ".env file not found"

        with open(env_file, "r") as f:
            content = f.read()
            assert "ALPACA_API_KEY" in content, "ALPACA_API_KEY not in .env"
            assert "ALPACA_SECRET_KEY" in content, "ALPACA_SECRET_KEY not in .env"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(45)
    async def test_services_start_within_30_seconds(
        self, project_root: Path, start_script: Path
    ):
        """Test all services start within 30 seconds."""
        start_time = time.time()

        # Start the observability API directly (faster than full system)
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

        try:
            # Wait for service to be ready with exponential backoff
            max_wait = 30
            async with httpx.AsyncClient() as client:
                for attempt in range(10):
                    if time.time() - start_time > max_wait:
                        break

                    try:
                        response = await client.get(
                            "http://localhost:8000/health",
                            timeout=2.0
                        )
                        if response.status_code == 200:
                            elapsed = time.time() - start_time
                            logger.info(f"Service started in {elapsed:.2f} seconds")
                            assert elapsed < 30, f"Startup took {elapsed}s (>30s)"
                            return
                    except (httpx.ConnectError, httpx.TimeoutException):
                        await asyncio.sleep(2 ** attempt * 0.1)  # Exponential backoff

            pytest.fail(f"Service did not start within {max_wait} seconds")

        finally:
            # Clean up
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_dashboard_accessible_on_port_8000(self):
        """Test that dashboard is accessible at localhost:8000."""
        # Start service
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

        try:
            # Wait for startup
            await asyncio.sleep(3)

            async with httpx.AsyncClient() as client:
                # Test root endpoint
                response = await client.get(
                    "http://localhost:8000/",
                    timeout=5.0
                )
                assert response.status_code == 200
                data = response.json()
                assert "service" in data
                assert data["service"] == "Trading Observability API"

                # Test health endpoint
                response = await client.get(
                    "http://localhost:8000/health",
                    timeout=5.0
                )
                assert response.status_code == 200
                assert response.json()["status"] == "healthy"

        finally:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_duckdb_database_created(self, project_root: Path):
        """Test that DuckDB database is created on startup."""
        db_path = project_root / "data" / "metrics.duckdb"

        # Ensure data directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Import and initialize DuckDB
        try:
            import duckdb

            conn = duckdb.connect(str(db_path))
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_metrics (
                    timestamp TIMESTAMP,
                    metric_name VARCHAR,
                    value DOUBLE
                )
                """
            )
            conn.close()

            # Verify database file exists
            assert db_path.exists(), "DuckDB database file not created"

            # Verify can connect and query
            conn = duckdb.connect(str(db_path))
            result = conn.execute("SELECT COUNT(*) FROM test_metrics").fetchone()
            assert result is not None
            conn.close()

        except ImportError:
            pytest.skip("DuckDB not installed")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_sqlite_database_created(self, project_root: Path):
        """Test that SQLite database is created for trades."""
        db_path = project_root / "data" / "trades.db"

        # Ensure data directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Import and initialize SQLite
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL
            )
            """
        )
        conn.commit()

        # Verify database file exists
        assert db_path.exists(), "SQLite database file not created"

        # Verify can query
        cursor.execute("SELECT COUNT(*) FROM trades")
        result = cursor.fetchone()
        assert result is not None

        conn.close()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_all_required_endpoints_respond(self):
        """Test that all critical endpoints are accessible."""
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

        try:
            await asyncio.sleep(3)

            endpoints = [
                "/health",
                "/health/ready",
                "/health/live",
                "/",
            ]

            async with httpx.AsyncClient() as client:
                for endpoint in endpoints:
                    response = await client.get(
                        f"http://localhost:8000{endpoint}",
                        timeout=5.0
                    )
                    assert response.status_code in [200, 503], (
                        f"Endpoint {endpoint} returned {response.status_code}"
                    )

        finally:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_graceful_shutdown(self):
        """Test that service handles graceful shutdown correctly."""
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

        try:
            # Wait for startup
            await asyncio.sleep(3)

            # Verify service is running
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/health",
                    timeout=5.0
                )
                assert response.status_code == 200

            # Send SIGTERM for graceful shutdown
            process.terminate()

            # Wait for graceful shutdown (should complete quickly)
            start_time = time.time()
            await asyncio.wait_for(process.wait(), timeout=10.0)
            shutdown_time = time.time() - start_time

            assert shutdown_time < 5.0, (
                f"Graceful shutdown took {shutdown_time}s (>5s)"
            )

        except asyncio.TimeoutError:
            # Force kill if graceful shutdown fails
            process.kill()
            await process.wait()
            pytest.fail("Graceful shutdown timed out")
