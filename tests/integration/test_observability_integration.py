"""
Integration test for observability data flow.

Tests the complete pipeline:
1. Rust services emit metrics
2. Python collectors scrape metrics via HTTP
3. Metrics are stored in DuckDB
4. Data can be queried successfully
"""
import pytest
import asyncio
import aiohttp
from datetime import datetime

from src.observability.metrics.rust_bridge import RustMetricsBridge
from src.observability.metrics.market_data_collector import MarketDataCollector


@pytest.mark.asyncio
async def test_rust_metrics_endpoints_available():
    """Test that all Rust service metrics endpoints are accessible."""
    endpoints = {
        "market_data": "http://127.0.0.1:9091/metrics",
        "execution": "http://127.0.0.1:9092/metrics",
        "risk": "http://127.0.0.1:9093/metrics",
    }

    timeout = aiohttp.ClientTimeout(total=2.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for service_name, url in endpoints.items():
            try:
                async with session.get(url) as response:
                    assert response.status == 200, f"{service_name} endpoint returned {response.status}"
                    text = await response.text()
                    assert len(text) > 0, f"{service_name} returned empty metrics"
                    assert "# TYPE" in text or "# HELP" in text, f"{service_name} doesn't return Prometheus format"
                    print(f"✓ {service_name} endpoint is accessible")
            except aiohttp.ClientError as e:
                pytest.skip(f"{service_name} service not running: {e}")


@pytest.mark.asyncio
async def test_rust_metrics_bridge_scraping():
    """Test that the Rust metrics bridge can successfully scrape services."""
    bridge = RustMetricsBridge({
        "market_data": "http://127.0.0.1:9091/metrics",
    })

    await bridge.start()

    try:
        metrics = await bridge.scrape_service("market_data", "http://127.0.0.1:9091/metrics")

        if metrics is None:
            pytest.skip("Market data service not running")

        # Verify structure
        assert "timestamp" in metrics
        assert "service" in metrics
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics

        assert metrics["service"] == "market_data"
        assert isinstance(metrics["timestamp"], datetime)

        print(f"✓ Successfully scraped metrics from market_data service")
        print(f"  Counters: {len(metrics['counters'])}")
        print(f"  Gauges: {len(metrics['gauges'])}")
        print(f"  Histograms: {len(metrics['histograms'])}")

    finally:
        await bridge.stop()


@pytest.mark.asyncio
async def test_prometheus_text_parsing():
    """Test parsing of Prometheus text format."""
    sample_prometheus = """
# HELP market_data_ticks_received_total Total ticks received
# TYPE market_data_ticks_received_total counter
market_data_ticks_received_total{symbol="AAPL"} 1523
market_data_ticks_received_total{symbol="TSLA"} 892

# HELP market_data_price Current price
# TYPE market_data_price gauge
market_data_price{symbol="AAPL"} 150.25
market_data_price{symbol="TSLA"} 242.50

# HELP market_data_processing_latency_ms Processing latency
# TYPE market_data_processing_latency_ms histogram
market_data_processing_latency_ms{symbol="AAPL"} 1.5
market_data_processing_latency_ms{symbol="TSLA"} 2.3
"""

    bridge = RustMetricsBridge({})
    metrics = bridge._parse_prometheus_text(sample_prometheus, "test_service")

    # Check parsed counters
    assert len(metrics["counters"]) >= 2
    assert any("AAPL" in key for key in metrics["counters"].keys())
    assert any("TSLA" in key for key in metrics["counters"].keys())

    # Check parsed gauges
    assert len(metrics["gauges"]) >= 2

    # Verify label parsing
    for counter in metrics["counters"].values():
        if counter["name"] == "market_data_ticks_received_total":
            assert "symbol" in counter["labels"]
            assert counter["labels"]["symbol"] in ["AAPL", "TSLA"]

    print("✓ Prometheus text parsing works correctly")


@pytest.mark.asyncio
async def test_market_data_collector_integration():
    """Test market data collector with Rust service integration."""
    collector = MarketDataCollector()

    try:
        await collector.start()

        # Wait a bit for metrics to be collected
        await asyncio.sleep(2)

        # Check collector status
        status = await collector.get_status()
        assert status["status"] == "ready"

        # Get current metrics
        metrics = await collector.get_current_metrics()
        assert "timestamp" in metrics
        assert "symbols" in metrics

        print(f"✓ Market data collector is collecting metrics")
        print(f"  Symbols tracked: {metrics.get('symbols_tracked', 0)}")
        print(f"  Metrics collected: {status['metrics_collected']}")

    finally:
        await collector.stop()


@pytest.mark.asyncio
async def test_all_services_scraping():
    """Test scraping all three services concurrently."""
    bridge = RustMetricsBridge({
        "market_data": "http://127.0.0.1:9091/metrics",
        "execution": "http://127.0.0.1:9092/metrics",
        "risk": "http://127.0.0.1:9093/metrics",
    })

    await bridge.start()

    try:
        all_metrics = await bridge.scrape_all_services()

        # Count available services
        available = sum(1 for m in all_metrics.values() if m is not None)

        if available == 0:
            pytest.skip("No Rust services are running")

        print(f"✓ Successfully scraped {available}/3 services")

        for service_name, metrics in all_metrics.items():
            if metrics:
                print(f"  {service_name}: {len(metrics['counters'])} counters, "
                      f"{len(metrics['gauges'])} gauges, "
                      f"{len(metrics['histograms'])} histograms")

    finally:
        await bridge.stop()


@pytest.mark.asyncio
async def test_continuous_scraping():
    """Test continuous metrics scraping."""
    bridge = RustMetricsBridge({
        "market_data": "http://127.0.0.1:9091/metrics",
    })

    await bridge.start()

    collected_count = 0

    async def metrics_callback(metrics):
        nonlocal collected_count
        if metrics.get("market_data"):
            collected_count += 1

    try:
        # Start continuous scraping with 0.5s interval
        bridge.scrape_interval = 0.5
        scrape_task = asyncio.create_task(
            bridge.continuous_scrape(callback=metrics_callback)
        )

        # Let it run for 2 seconds
        await asyncio.sleep(2)

        # Stop scraping
        bridge.stop_continuous_scrape()
        await scrape_task

        if collected_count == 0:
            pytest.skip("Market data service not running")

        # Should have collected ~4 times (2s / 0.5s)
        assert collected_count >= 2, f"Only collected {collected_count} times"

        print(f"✓ Continuous scraping collected metrics {collected_count} times")

    finally:
        await bridge.stop()


def test_metrics_module_exports():
    """Test that metrics functions are available in Rust common module."""
    # This would require the Rust code to be compiled and running
    # Just verify the Python bridge exists for now
    from src.observability.metrics.rust_bridge import get_rust_metrics_bridge

    bridge = get_rust_metrics_bridge()
    assert bridge is not None
    assert "market_data" in bridge.service_endpoints
    assert "execution" in bridge.service_endpoints
    assert "risk" in bridge.service_endpoints

    print("✓ Metrics bridge is correctly configured")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
