# Load Testing Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-21

---

## Table of Contents

1. [Overview](#overview)
2. [Test Scenarios](#test-scenarios)
3. [Tools and Setup](#tools-and-setup)
4. [Running Load Tests](#running-load-tests)
5. [Performance Targets](#performance-targets)
6. [Monitoring](#monitoring)
7. [Results Analysis](#results-analysis)
8. [Optimization](#optimization)

---

## Overview

Load testing ensures the trading system can handle production workloads without degradation. We test:

- **Market data throughput:** 100,000+ ticks/second
- **Order processing:** 1,000+ orders/second
- **Database writes:** 10,000+ metrics/second
- **WebSocket connections:** 100+ concurrent clients
- **API endpoints:** 10,000+ requests/minute

---

## Test Scenarios

### Scenario 1: Market Data Flood

**Objective:** Test market data processing at maximum throughput

**Load Profile:**
- 100,000 ticks/second
- 50 symbols
- Duration: 10 minutes
- Expected: No drops, <10ms processing latency

**Test Script:** `tests/load/test_market_data_flood.py`

```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import websocket
import json

async def generate_ticks(symbol: str, rate: int, duration: int):
    """Generate market ticks at specified rate"""
    ws = websocket.create_connection("ws://localhost:5001/stream")

    start_time = time.time()
    tick_count = 0

    while time.time() - start_time < duration:
        tick = {
            "type": "tick",
            "symbol": symbol,
            "price": 100.0 + (tick_count % 100) * 0.1,
            "volume": 1000,
            "timestamp": time.time()
        }

        ws.send(json.dumps(tick))
        tick_count += 1

        # Control rate
        await asyncio.sleep(1.0 / rate)

    ws.close()
    return tick_count

async def run_market_data_flood():
    """Run market data flood test"""
    symbols = [f"SYM{i}" for i in range(50)]
    rate_per_symbol = 2000  # 2000 ticks/sec/symbol = 100,000 total

    tasks = [
        generate_ticks(symbol, rate_per_symbol, duration=600)
        for symbol in symbols
    ]

    results = await asyncio.gather(*tasks)
    total_ticks = sum(results)

    print(f"Total ticks generated: {total_ticks:,}")
    print(f"Average rate: {total_ticks / 600:.2f} ticks/sec")

if __name__ == "__main__":
    asyncio.run(run_market_data_flood())
```

**Run Test:**
```bash
# Start system
./scripts/start_trading.sh

# Run load test
python3 tests/load/test_market_data_flood.py

# Monitor metrics
curl http://localhost:8000/api/metrics/market-data | jq .
```

### Scenario 2: Order Processing Stress

**Objective:** Test order processing under heavy load

**Load Profile:**
- 1,000 orders/second
- Mix: 60% limit, 30% market, 10% stop
- Duration: 5 minutes
- Expected: <100ms order latency (P95)

**Test Script:** `tests/load/test_order_stress.py`

```python
import asyncio
import httpx
import random
import time
from typing import List, Dict

class OrderGenerator:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.client = httpx.AsyncClient(base_url="http://localhost:5002")

    async def generate_order(self) -> Dict:
        """Generate random order"""
        symbol = random.choice(self.symbols)
        side = random.choice(["buy", "sell"])

        # Order type distribution: 60% limit, 30% market, 10% stop
        rand = random.random()
        if rand < 0.6:
            order_type = "limit"
            price = 100.0 + random.uniform(-10, 10)
        elif rand < 0.9:
            order_type = "market"
            price = None
        else:
            order_type = "stop"
            price = 100.0 + random.uniform(-5, 5)

        return {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": random.randint(1, 100),
            "price": price
        }

    async def submit_order(self) -> Dict:
        """Submit order and measure latency"""
        order = await self.generate_order()
        start = time.time()

        try:
            response = await self.client.post("/orders", json=order)
            latency = (time.time() - start) * 1000  # ms
            return {"success": True, "latency": latency}
        except Exception as e:
            latency = (time.time() - start) * 1000
            return {"success": False, "latency": latency, "error": str(e)}

    async def run_stress_test(self, rate: int, duration: int):
        """Run order stress test"""
        start_time = time.time()
        results = []

        while time.time() - start_time < duration:
            batch_start = time.time()

            # Submit orders at target rate
            batch_size = rate  # 1 second batch
            tasks = [self.submit_order() for _ in range(batch_size)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            # Calculate sleep time to maintain rate
            batch_duration = time.time() - batch_start
            sleep_time = max(0, 1.0 - batch_duration)
            await asyncio.sleep(sleep_time)

        return results

async def analyze_results(results: List[Dict]):
    """Analyze test results"""
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    latencies = [r["latency"] for r in successful]
    latencies.sort()

    print(f"=== Order Stress Test Results ===")
    print(f"Total orders: {len(results):,}")
    print(f"Successful: {len(successful):,} ({len(successful)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failed):,} ({len(failed)/len(results)*100:.1f}%)")
    print()
    print(f"Latency Stats:")
    print(f"  P50: {latencies[len(latencies)//2]:.2f} ms")
    print(f"  P95: {latencies[int(len(latencies)*0.95)]:.2f} ms")
    print(f"  P99: {latencies[int(len(latencies)*0.99)]:.2f} ms")
    print(f"  Max: {max(latencies):.2f} ms")

async def main():
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    generator = OrderGenerator(symbols)

    results = await generator.run_stress_test(
        rate=1000,      # 1000 orders/sec
        duration=300    # 5 minutes
    )

    await analyze_results(results)

if __name__ == "__main__":
    asyncio.run(main())
```

**Run Test:**
```bash
python3 tests/load/test_order_stress.py
```

### Scenario 3: Database Write Throughput

**Objective:** Test database write performance

**Load Profile:**
- 10,000 metrics/second
- Batch size: 1,000 records
- Duration: 10 minutes
- Expected: <50ms batch insert latency

**Test Script:** `tests/load/test_database_throughput.py`

```python
import asyncio
import time
from database import DatabaseManager, MetricRecord

async def benchmark_inserts(batch_size: int, total_batches: int):
    """Benchmark database insert performance"""
    db = await DatabaseManager.new(":memory:")
    await db.initialize()

    latencies = []

    for batch_num in range(total_batches):
        # Generate batch of metrics
        metrics = [
            MetricRecord.new(
                f"metric_{i % 100}",
                float(i),
                labels={"batch": str(batch_num)}
            )
            for i in range(batch_size)
        ]

        # Measure insert latency
        start = time.time()
        await db.insert_metrics(metrics)
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)

        if batch_num % 10 == 0:
            avg_latency = sum(latencies[-10:]) / len(latencies[-10:])
            rate = (batch_size / avg_latency) * 1000
            print(f"Batch {batch_num}: {avg_latency:.2f}ms, {rate:.0f} records/sec")

    # Calculate statistics
    latencies.sort()
    total_records = batch_size * total_batches

    print(f"\n=== Database Throughput Test Results ===")
    print(f"Total records: {total_records:,}")
    print(f"Batch size: {batch_size}")
    print(f"Total batches: {total_batches}")
    print(f"\nLatency Stats:")
    print(f"  P50: {latencies[len(latencies)//2]:.2f} ms")
    print(f"  P95: {latencies[int(len(latencies)*0.95)]:.2f} ms")
    print(f"  P99: {latencies[int(len(latencies)*0.99)]:.2f} ms")
    print(f"\nThroughput:")
    avg_latency = sum(latencies) / len(latencies)
    throughput = (batch_size / avg_latency) * 1000
    print(f"  Average: {throughput:.0f} records/sec")

if __name__ == "__main__":
    asyncio.run(benchmark_inserts(
        batch_size=1000,
        total_batches=600  # 600k total records
    ))
```

**Run Test:**
```bash
cargo run --release --example observability_integration
```

### Scenario 4: WebSocket Concurrency

**Objective:** Test WebSocket server under concurrent connections

**Load Profile:**
- 100 concurrent WebSocket clients
- Each client subscribes to 10 symbols
- Duration: 10 minutes
- Expected: All clients receive updates, <100ms message latency

**Test Script:** `tests/load/test_websocket_concurrency.py`

```python
import asyncio
import websockets
import json
import time
from typing import List

class WebSocketClient:
    def __init__(self, client_id: int, symbols: List[str]):
        self.client_id = client_id
        self.symbols = symbols
        self.messages_received = 0
        self.total_latency = 0.0

    async def run(self, duration: int):
        """Run WebSocket client"""
        uri = "ws://localhost:8000/ws/metrics"

        async with websockets.connect(uri) as ws:
            # Subscribe to symbols
            for symbol in self.symbols:
                await ws.send(json.dumps({"action": "subscribe", "symbol": symbol}))

            start_time = time.time()

            while time.time() - start_time < duration:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.parse(message)

                    # Calculate message latency
                    if "timestamp" in data:
                        latency = time.time() - data["timestamp"]
                        self.total_latency += latency * 1000  # ms

                    self.messages_received += 1

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await ws.send("ping")

        avg_latency = self.total_latency / self.messages_received if self.messages_received > 0 else 0
        return {
            "client_id": self.client_id,
            "messages": self.messages_received,
            "avg_latency": avg_latency
        }

async def run_websocket_load_test(num_clients: int, duration: int):
    """Run WebSocket concurrency test"""
    symbols = [f"SYM{i}" for i in range(50)]

    # Create clients
    clients = [
        WebSocketClient(
            client_id=i,
            symbols=symbols[i*10:(i+1)*10]  # 10 symbols per client
        )
        for i in range(num_clients)
    ]

    # Run all clients concurrently
    print(f"Starting {num_clients} WebSocket clients...")
    results = await asyncio.gather(*[client.run(duration) for client in clients])

    # Analyze results
    total_messages = sum(r["messages"] for r in results)
    avg_latency = sum(r["avg_latency"] for r in results) / len(results)

    print(f"\n=== WebSocket Concurrency Test Results ===")
    print(f"Concurrent clients: {num_clients}")
    print(f"Total messages: {total_messages:,}")
    print(f"Messages/client: {total_messages / num_clients:.0f}")
    print(f"Average latency: {avg_latency:.2f} ms")

if __name__ == "__main__":
    asyncio.run(run_websocket_load_test(
        num_clients=100,
        duration=600  # 10 minutes
    ))
```

**Run Test:**
```bash
python3 tests/load/test_websocket_concurrency.py
```

---

## Performance Targets

### Critical Path Targets

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Order creation | <100ns | TBD | ⏳ |
| OrderBook update | <500ns | TBD | ⏳ |
| Risk check | <1μs | TBD | ⏳ |
| Order routing | <100μs | TBD | ⏳ |
| Database insert (1k batch) | <50ms | ~10ms | ✅ |
| API latency (P95) | <10ms | TBD | ⏳ |
| WebSocket latency (P95) | <50ms | TBD | ⏳ |

### Throughput Targets

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| Market data ticks/sec | 100,000+ | TBD | ⏳ |
| Orders/sec | 1,000+ | TBD | ⏳ |
| Database writes/sec | 10,000+ | ~10,000 | ✅ |
| API requests/min | 10,000+ | TBD | ⏳ |
| WebSocket clients | 100+ | TBD | ⏳ |

---

## Monitoring

### Real-Time Monitoring During Tests

```bash
# Terminal 1: System metrics
watch -n 1 'curl -s http://localhost:8000/api/metrics/system | jq .'

# Terminal 2: Database stats
watch -n 5 'python3 -c "
import duckdb
conn = duckdb.connect(\"data/metrics.duckdb\")
result = conn.execute(\"SELECT COUNT(*) FROM trading_metrics\").fetchone()
print(f\"Total metrics: {result[0]:,}\")
conn.close()
"'

# Terminal 3: Process stats
watch -n 2 'ps aux | grep -E "(market-data|execution-engine|risk-manager)" | grep -v grep'

# Terminal 4: Network stats
watch -n 1 'netstat -an | grep -E ":(5001|5002|5003|8000)" | wc -l'
```

### Grafana Dashboard (Optional)

```yaml
# docker-compose.observability.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

---

## Results Analysis

### Analyzing Load Test Results

```python
# scripts/analyze_load_test.py
import pandas as pd
import matplotlib.pyplot as plt

def analyze_load_test(results_file: str):
    """Analyze load test results"""
    df = pd.read_csv(results_file)

    # Calculate statistics
    stats = {
        "total_requests": len(df),
        "successful": len(df[df["success"] == True]),
        "failed": len(df[df["success"] == False]),
        "p50_latency": df["latency"].quantile(0.5),
        "p95_latency": df["latency"].quantile(0.95),
        "p99_latency": df["latency"].quantile(0.99),
        "max_latency": df["latency"].max(),
        "throughput": len(df) / df["duration"].max()
    }

    # Print results
    print("=== Load Test Analysis ===")
    for key, value in stats.items():
        if "latency" in key:
            print(f"{key}: {value:.2f} ms")
        elif key == "throughput":
            print(f"{key}: {value:.2f} req/sec")
        else:
            print(f"{key}: {value}")

    # Plot latency distribution
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.hist(df["latency"], bins=50, edgecolor='black')
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    plt.title("Latency Distribution")

    plt.subplot(1, 2, 2)
    plt.plot(df["timestamp"], df["latency"])
    plt.xlabel("Time")
    plt.ylabel("Latency (ms)")
    plt.title("Latency Over Time")

    plt.tight_layout()
    plt.savefig("load_test_results.png")
    print("\nPlot saved to load_test_results.png")

if __name__ == "__main__":
    analyze_load_test("test_results.csv")
```

---

## Optimization

### Performance Optimization Checklist

**Database:**
- ✅ Use batch inserts (1000+ records)
- ✅ Enable connection pooling (10 connections)
- ✅ Add indexes on frequently queried fields
- ⏳ Implement query result caching
- ⏳ Use prepared statements for repeated queries

**Network:**
- ⏳ Enable TCP_NODELAY for WebSocket
- ⏳ Use connection keep-alive
- ⏳ Implement request batching
- ⏳ Add response compression (gzip)

**System:**
- ⏳ Use release builds only (`cargo build --release`)
- ⏳ Enable LTO (Link-Time Optimization)
- ⏳ Reduce allocations in hot paths
- ⏳ Use SIMD for calculations
- ⏳ Implement zero-copy deserialization

### Profiling

```bash
# CPU profiling
cargo flamegraph --bin market-data

# Memory profiling
valgrind --tool=massif ./target/release/market-data

# Lock contention
cargo build --release
perf record -g ./target/release/market-data
perf report
```

---

## Summary

Load testing is critical for ensuring production readiness:

1. **Run all scenarios** before deployment
2. **Monitor key metrics** during tests
3. **Analyze results** for bottlenecks
4. **Optimize** based on findings
5. **Repeat** until targets met

For more information, see:
- [Testing Strategy](/docs/testing/TEST_STRATEGY.md)
- [Performance Analysis](/docs/PERFORMANCE_ANALYSIS.md)
- [Deployment Guide](/docs/deployment/STAGING_DEPLOYMENT.md)
