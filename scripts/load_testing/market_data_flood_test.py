#!/usr/bin/env python3
"""
Market Data Flood Test
Simulates high-frequency market data updates to test system throughput
Target: 1000 ticks/second sustained
"""

import asyncio
import aiohttp
import time
import random
from dataclasses import dataclass
from typing import List, Dict
import statistics
import json
import os


@dataclass
class TickData:
    """Market tick data structure"""
    symbol: str
    price: float
    volume: float
    timestamp: float
    bid: float
    ask: float


class MarketDataFloodTester:
    def __init__(self, base_url: str, target_tps: int = 1000, duration_sec: int = 300):
        self.base_url = base_url
        self.target_tps = target_tps
        self.duration_sec = duration_sec
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]
        self.results = {
            "ticks_sent": 0,
            "ticks_success": 0,
            "ticks_failed": 0,
            "latencies_ms": [],
            "errors": [],
            "throughput_samples": []
        }

    def generate_tick(self, symbol: str) -> TickData:
        """Generate realistic market tick data"""
        base_price = {
            "BTCUSDT": 45000.0,
            "ETHUSDT": 3000.0,
            "BNBUSDT": 400.0,
            "ADAUSDT": 1.5,
            "DOTUSDT": 25.0
        }.get(symbol, 100.0)

        # Add random price movement
        price = base_price * (1 + random.uniform(-0.001, 0.001))
        spread = base_price * 0.0001  # 0.01% spread

        return TickData(
            symbol=symbol,
            price=price,
            volume=random.uniform(0.1, 10.0),
            timestamp=time.time(),
            bid=price - spread / 2,
            ask=price + spread / 2
        )

    async def send_tick(self, session: aiohttp.ClientSession, tick: TickData) -> Dict:
        """Send a single tick to the trading engine"""
        start_time = time.time()

        try:
            async with session.post(
                f"{self.base_url}/api/v1/market_data",
                json={
                    "symbol": tick.symbol,
                    "price": tick.price,
                    "volume": tick.volume,
                    "timestamp": tick.timestamp,
                    "bid": tick.bid,
                    "ask": tick.ask
                },
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status == 200:
                    self.results["ticks_success"] += 1
                    self.results["latencies_ms"].append(latency_ms)
                    return {"success": True, "latency_ms": latency_ms}
                else:
                    self.results["ticks_failed"] += 1
                    error_text = await response.text()
                    self.results["errors"].append({
                        "status": response.status,
                        "error": error_text,
                        "symbol": tick.symbol
                    })
                    return {"success": False, "error": error_text}

        except asyncio.TimeoutError:
            self.results["ticks_failed"] += 1
            self.results["errors"].append({
                "error": "Timeout",
                "symbol": tick.symbol
            })
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            self.results["ticks_failed"] += 1
            self.results["errors"].append({
                "error": str(e),
                "symbol": tick.symbol
            })
            return {"success": False, "error": str(e)}

    async def flood_worker(self, session: aiohttp.ClientSession, stop_event: asyncio.Event):
        """Worker that continuously sends market data ticks"""
        ticks_sent_local = 0

        while not stop_event.is_set():
            symbol = random.choice(self.symbols)
            tick = self.generate_tick(symbol)

            self.results["ticks_sent"] += 1
            ticks_sent_local += 1

            await self.send_tick(session, tick)

            # Rate limiting to achieve target TPS
            await asyncio.sleep(1.0 / self.target_tps)

    async def monitor_throughput(self, stop_event: asyncio.Event):
        """Monitor and log throughput every second"""
        last_count = 0

        while not stop_event.is_set():
            await asyncio.sleep(1.0)

            current_count = self.results["ticks_success"]
            throughput = current_count - last_count
            last_count = current_count

            self.results["throughput_samples"].append(throughput)

            print(f"Current throughput: {throughput} ticks/sec | "
                  f"Success: {self.results['ticks_success']} | "
                  f"Failed: {self.results['ticks_failed']}")

    async def run_test(self):
        """Execute the flood test"""
        print(f"Starting market data flood test...")
        print(f"Target: {self.target_tps} ticks/sec for {self.duration_sec} seconds")
        print(f"Symbols: {', '.join(self.symbols)}")
        print("-" * 80)

        stop_event = asyncio.Event()

        # Calculate number of concurrent workers needed
        num_workers = max(10, self.target_tps // 100)

        async with aiohttp.ClientSession() as session:
            # Start workers
            workers = [
                asyncio.create_task(self.flood_worker(session, stop_event))
                for _ in range(num_workers)
            ]

            # Start throughput monitor
            monitor = asyncio.create_task(self.monitor_throughput(stop_event))

            # Wait for test duration
            await asyncio.sleep(self.duration_sec)

            # Stop all workers
            stop_event.set()

            # Wait for workers to finish
            await asyncio.gather(*workers, monitor, return_exceptions=True)

        self.print_results()

    def print_results(self):
        """Print test results and statistics"""
        print("\n" + "=" * 80)
        print("MARKET DATA FLOOD TEST RESULTS")
        print("=" * 80)

        print(f"\nTotal ticks sent: {self.results['ticks_sent']}")
        print(f"Successful: {self.results['ticks_success']}")
        print(f"Failed: {self.results['ticks_failed']}")

        success_rate = (self.results['ticks_success'] / self.results['ticks_sent'] * 100) if self.results['ticks_sent'] > 0 else 0
        print(f"Success rate: {success_rate:.2f}%")

        if self.results['latencies_ms']:
            print(f"\nLatency Statistics:")
            print(f"  Min: {min(self.results['latencies_ms']):.2f} ms")
            print(f"  Max: {max(self.results['latencies_ms']):.2f} ms")
            print(f"  Mean: {statistics.mean(self.results['latencies_ms']):.2f} ms")
            print(f"  Median: {statistics.median(self.results['latencies_ms']):.2f} ms")

            sorted_latencies = sorted(self.results['latencies_ms'])
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
            print(f"  P95: {sorted_latencies[p95_idx]:.2f} ms")
            print(f"  P99: {sorted_latencies[p99_idx]:.2f} ms")

        if self.results['throughput_samples']:
            print(f"\nThroughput Statistics:")
            print(f"  Min: {min(self.results['throughput_samples'])} ticks/sec")
            print(f"  Max: {max(self.results['throughput_samples'])} ticks/sec")
            print(f"  Mean: {statistics.mean(self.results['throughput_samples']):.2f} ticks/sec")
            print(f"  Median: {statistics.median(self.results['throughput_samples']):.2f} ticks/sec")

        if self.results['errors']:
            print(f"\nErrors (showing first 10):")
            for error in self.results['errors'][:10]:
                print(f"  - {error}")

        # Pass/Fail criteria
        print("\n" + "-" * 80)
        target_achieved = statistics.mean(self.results['throughput_samples']) >= self.target_tps * 0.9 if self.results['throughput_samples'] else False
        error_rate_ok = success_rate >= 99.0
        latency_ok = statistics.median(self.results['latencies_ms']) <= 100 if self.results['latencies_ms'] else False

        print("PASS/FAIL CRITERIA:")
        print(f"  {'✓' if target_achieved else '✗'} Throughput >= {self.target_tps * 0.9} ticks/sec (90% of target)")
        print(f"  {'✓' if error_rate_ok else '✗'} Success rate >= 99%")
        print(f"  {'✓' if latency_ok else '✗'} Median latency <= 100ms")

        overall_pass = target_achieved and error_rate_ok and latency_ok
        print(f"\nOVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
        print("=" * 80)

        # Save results to file
        results_file = "/results/market_data_flood_test.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                "test_name": "market_data_flood_test",
                "timestamp": time.time(),
                "configuration": {
                    "target_tps": self.target_tps,
                    "duration_sec": self.duration_sec,
                    "symbols": self.symbols
                },
                "results": {
                    "ticks_sent": self.results['ticks_sent'],
                    "ticks_success": self.results['ticks_success'],
                    "ticks_failed": self.results['ticks_failed'],
                    "success_rate": success_rate,
                    "latency_stats": {
                        "min": min(self.results['latencies_ms']) if self.results['latencies_ms'] else 0,
                        "max": max(self.results['latencies_ms']) if self.results['latencies_ms'] else 0,
                        "mean": statistics.mean(self.results['latencies_ms']) if self.results['latencies_ms'] else 0,
                        "median": statistics.median(self.results['latencies_ms']) if self.results['latencies_ms'] else 0,
                        "p95": sorted_latencies[p95_idx] if self.results['latencies_ms'] else 0,
                        "p99": sorted_latencies[p99_idx] if self.results['latencies_ms'] else 0
                    },
                    "throughput_stats": {
                        "min": min(self.results['throughput_samples']) if self.results['throughput_samples'] else 0,
                        "max": max(self.results['throughput_samples']) if self.results['throughput_samples'] else 0,
                        "mean": statistics.mean(self.results['throughput_samples']) if self.results['throughput_samples'] else 0,
                        "median": statistics.median(self.results['throughput_samples']) if self.results['throughput_samples'] else 0
                    }
                },
                "pass": overall_pass
            }, f, indent=2)

        print(f"\nResults saved to {results_file}")


async def main():
    trading_engine_url = os.getenv("TRADING_ENGINE_URL", "http://trading-engine-staging:9000")
    target_tps = int(os.getenv("LOAD_TEST_TARGET_TPS", "1000"))
    duration = int(os.getenv("LOAD_TEST_DURATION", "300"))

    tester = MarketDataFloodTester(
        base_url=trading_engine_url,
        target_tps=target_tps,
        duration_sec=duration
    )

    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
