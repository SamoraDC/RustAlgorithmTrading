#!/usr/bin/env python3
"""
Database Throughput Test
Tests database write/read performance under high load
Target: 1000 writes/sec sustained
"""

import asyncio
import asyncpg
import time
import random
from typing import List, Dict
import statistics
import json
import os


class DatabaseThroughputTester:
    def __init__(self, postgres_url: str, target_wps: int = 1000, duration_sec: int = 300):
        self.postgres_url = postgres_url
        self.target_wps = target_wps
        self.duration_sec = duration_sec
        self.results = {
            "writes_attempted": 0,
            "writes_success": 0,
            "writes_failed": 0,
            "reads_attempted": 0,
            "reads_success": 0,
            "reads_failed": 0,
            "write_latencies_ms": [],
            "read_latencies_ms": [],
            "errors": [],
            "wps_samples": [],
            "rps_samples": []
        }

    async def setup_database(self, conn: asyncpg.Connection):
        """Create test table if it doesn't exist"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS load_test_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                price DECIMAL(20, 8) NOT NULL,
                volume DECIMAL(20, 8) NOT NULL,
                timestamp BIGINT NOT NULL,
                data JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create index for faster queries
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_load_test_symbol_timestamp
            ON load_test_data(symbol, timestamp DESC)
        """)

    async def write_data(self, conn: asyncpg.Connection) -> Dict:
        """Write a single record to the database"""
        start_time = time.time()

        symbol = random.choice(["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"])
        price = random.uniform(100, 50000)
        volume = random.uniform(0.1, 100)
        timestamp = int(time.time() * 1000)
        data = {
            "bid": price * 0.9995,
            "ask": price * 1.0005,
            "high_24h": price * 1.05,
            "low_24h": price * 0.95,
            "volume_24h": volume * 1000
        }

        try:
            await conn.execute("""
                INSERT INTO load_test_data (symbol, price, volume, timestamp, data)
                VALUES ($1, $2, $3, $4, $5)
            """, symbol, price, volume, timestamp, json.dumps(data))

            latency_ms = (time.time() - start_time) * 1000
            self.results["writes_success"] += 1
            self.results["write_latencies_ms"].append(latency_ms)
            return {"success": True, "latency_ms": latency_ms}

        except Exception as e:
            self.results["writes_failed"] += 1
            self.results["errors"].append({
                "operation": "write",
                "error": str(e)
            })
            return {"success": False, "error": str(e)}

    async def read_data(self, conn: asyncpg.Connection) -> Dict:
        """Read data from the database"""
        start_time = time.time()

        symbol = random.choice(["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"])

        try:
            rows = await conn.fetch("""
                SELECT * FROM load_test_data
                WHERE symbol = $1
                ORDER BY timestamp DESC
                LIMIT 100
            """, symbol)

            latency_ms = (time.time() - start_time) * 1000
            self.results["reads_success"] += 1
            self.results["read_latencies_ms"].append(latency_ms)
            return {"success": True, "latency_ms": latency_ms, "rows": len(rows)}

        except Exception as e:
            self.results["reads_failed"] += 1
            self.results["errors"].append({
                "operation": "read",
                "error": str(e)
            })
            return {"success": False, "error": str(e)}

    async def write_worker(self, pool: asyncpg.Pool, stop_event: asyncio.Event):
        """Worker that continuously writes data"""
        async with pool.acquire() as conn:
            while not stop_event.is_set():
                self.results["writes_attempted"] += 1
                await self.write_data(conn)

                # Rate limiting
                await asyncio.sleep(1.0 / self.target_wps)

    async def read_worker(self, pool: asyncpg.Pool, stop_event: asyncio.Event):
        """Worker that continuously reads data"""
        async with pool.acquire() as conn:
            while not stop_event.is_set():
                self.results["reads_attempted"] += 1
                await self.read_data(conn)

                # Read at 10% of write rate
                await asyncio.sleep(10.0 / self.target_wps)

    async def monitor_throughput(self, stop_event: asyncio.Event):
        """Monitor writes and reads per second"""
        last_writes = 0
        last_reads = 0

        while not stop_event.is_set():
            await asyncio.sleep(1.0)

            current_writes = self.results["writes_success"]
            current_reads = self.results["reads_success"]

            wps = current_writes - last_writes
            rps = current_reads - last_reads

            last_writes = current_writes
            last_reads = current_reads

            self.results["wps_samples"].append(wps)
            self.results["rps_samples"].append(rps)

            print(f"Writes/sec: {wps} | Reads/sec: {rps} | "
                  f"Write failures: {self.results['writes_failed']} | "
                  f"Read failures: {self.results['reads_failed']}")

    async def run_test(self):
        """Execute the throughput test"""
        print(f"Starting database throughput test...")
        print(f"Target: {self.target_wps} writes/sec for {self.duration_sec} seconds")
        print("-" * 80)

        # Create connection pool
        pool = await asyncpg.create_pool(
            self.postgres_url,
            min_size=10,
            max_size=50,
            command_timeout=10
        )

        # Setup database
        async with pool.acquire() as conn:
            await self.setup_database(conn)

        stop_event = asyncio.Event()

        # Calculate number of workers
        num_write_workers = max(10, self.target_wps // 100)
        num_read_workers = max(2, num_write_workers // 5)

        # Start workers
        write_workers = [
            asyncio.create_task(self.write_worker(pool, stop_event))
            for _ in range(num_write_workers)
        ]

        read_workers = [
            asyncio.create_task(self.read_worker(pool, stop_event))
            for _ in range(num_read_workers)
        ]

        # Start monitor
        monitor = asyncio.create_task(self.monitor_throughput(stop_event))

        # Wait for test duration
        await asyncio.sleep(self.duration_sec)

        # Stop all workers
        stop_event.set()

        # Wait for workers to finish
        await asyncio.gather(
            *write_workers,
            *read_workers,
            monitor,
            return_exceptions=True
        )

        # Close pool
        await pool.close()

        self.print_results()

    def print_results(self):
        """Print test results and statistics"""
        print("\n" + "=" * 80)
        print("DATABASE THROUGHPUT TEST RESULTS")
        print("=" * 80)

        print(f"\nWrite Operations:")
        print(f"  Attempted: {self.results['writes_attempted']}")
        print(f"  Successful: {self.results['writes_success']}")
        print(f"  Failed: {self.results['writes_failed']}")

        write_success_rate = (self.results['writes_success'] / self.results['writes_attempted'] * 100) if self.results['writes_attempted'] > 0 else 0
        print(f"  Success rate: {write_success_rate:.2f}%")

        print(f"\nRead Operations:")
        print(f"  Attempted: {self.results['reads_attempted']}")
        print(f"  Successful: {self.results['reads_success']}")
        print(f"  Failed: {self.results['reads_failed']}")

        read_success_rate = (self.results['reads_success'] / self.results['reads_attempted'] * 100) if self.results['reads_attempted'] > 0 else 0
        print(f"  Success rate: {read_success_rate:.2f}%")

        if self.results['write_latencies_ms']:
            print(f"\nWrite Latency Statistics:")
            print(f"  Min: {min(self.results['write_latencies_ms']):.2f} ms")
            print(f"  Max: {max(self.results['write_latencies_ms']):.2f} ms")
            print(f"  Mean: {statistics.mean(self.results['write_latencies_ms']):.2f} ms")
            print(f"  Median: {statistics.median(self.results['write_latencies_ms']):.2f} ms")

            sorted_write_lat = sorted(self.results['write_latencies_ms'])
            p95_idx = int(len(sorted_write_lat) * 0.95)
            p99_idx = int(len(sorted_write_lat) * 0.99)
            print(f"  P95: {sorted_write_lat[p95_idx]:.2f} ms")
            print(f"  P99: {sorted_write_lat[p99_idx]:.2f} ms")

        if self.results['read_latencies_ms']:
            print(f"\nRead Latency Statistics:")
            print(f"  Min: {min(self.results['read_latencies_ms']):.2f} ms")
            print(f"  Max: {max(self.results['read_latencies_ms']):.2f} ms")
            print(f"  Mean: {statistics.mean(self.results['read_latencies_ms']):.2f} ms")
            print(f"  Median: {statistics.median(self.results['read_latencies_ms']):.2f} ms")

            sorted_read_lat = sorted(self.results['read_latencies_ms'])
            p95_idx = int(len(sorted_read_lat) * 0.95)
            p99_idx = int(len(sorted_read_lat) * 0.99)
            print(f"  P95: {sorted_read_lat[p95_idx]:.2f} ms")
            print(f"  P99: {sorted_read_lat[p99_idx]:.2f} ms")

        if self.results['wps_samples']:
            print(f"\nWrite Throughput Statistics:")
            print(f"  Min: {min(self.results['wps_samples'])} writes/sec")
            print(f"  Max: {max(self.results['wps_samples'])} writes/sec")
            print(f"  Mean: {statistics.mean(self.results['wps_samples']):.2f} writes/sec")
            print(f"  Median: {statistics.median(self.results['wps_samples']):.2f} writes/sec")

        if self.results['rps_samples']:
            print(f"\nRead Throughput Statistics:")
            print(f"  Min: {min(self.results['rps_samples'])} reads/sec")
            print(f"  Max: {max(self.results['rps_samples'])} reads/sec")
            print(f"  Mean: {statistics.mean(self.results['rps_samples']):.2f} reads/sec")
            print(f"  Median: {statistics.median(self.results['rps_samples']):.2f} reads/sec")

        if self.results['errors']:
            print(f"\nErrors (showing first 10):")
            for error in self.results['errors'][:10]:
                print(f"  - {error}")

        # Pass/Fail criteria
        print("\n" + "-" * 80)
        write_target_ok = statistics.mean(self.results['wps_samples']) >= self.target_wps * 0.9 if self.results['wps_samples'] else False
        write_success_ok = write_success_rate >= 99.0
        write_latency_ok = statistics.median(self.results['write_latencies_ms']) <= 50 if self.results['write_latencies_ms'] else False
        read_latency_ok = statistics.median(self.results['read_latencies_ms']) <= 100 if self.results['read_latencies_ms'] else False

        print("PASS/FAIL CRITERIA:")
        print(f"  {'✓' if write_target_ok else '✗'} Write throughput >= {self.target_wps * 0.9} writes/sec")
        print(f"  {'✓' if write_success_ok else '✗'} Write success rate >= 99%")
        print(f"  {'✓' if write_latency_ok else '✗'} Write median latency <= 50ms")
        print(f"  {'✓' if read_latency_ok else '✗'} Read median latency <= 100ms")

        overall_pass = write_target_ok and write_success_ok and write_latency_ok and read_latency_ok
        print(f"\nOVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
        print("=" * 80)

        # Save results
        results_file = "/results/database_throughput_test.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                "test_name": "database_throughput_test",
                "timestamp": time.time(),
                "configuration": {
                    "target_wps": self.target_wps,
                    "duration_sec": self.duration_sec
                },
                "results": {
                    "writes": {
                        "attempted": self.results['writes_attempted'],
                        "success": self.results['writes_success'],
                        "failed": self.results['writes_failed'],
                        "success_rate": write_success_rate
                    },
                    "reads": {
                        "attempted": self.results['reads_attempted'],
                        "success": self.results['reads_success'],
                        "failed": self.results['reads_failed'],
                        "success_rate": read_success_rate
                    },
                    "write_latency_stats": {
                        "min": min(self.results['write_latencies_ms']) if self.results['write_latencies_ms'] else 0,
                        "max": max(self.results['write_latencies_ms']) if self.results['write_latencies_ms'] else 0,
                        "mean": statistics.mean(self.results['write_latencies_ms']) if self.results['write_latencies_ms'] else 0,
                        "median": statistics.median(self.results['write_latencies_ms']) if self.results['write_latencies_ms'] else 0,
                        "p95": sorted_write_lat[p95_idx] if self.results['write_latencies_ms'] else 0,
                        "p99": sorted_write_lat[p99_idx] if self.results['write_latencies_ms'] else 0
                    },
                    "read_latency_stats": {
                        "min": min(self.results['read_latencies_ms']) if self.results['read_latencies_ms'] else 0,
                        "max": max(self.results['read_latencies_ms']) if self.results['read_latencies_ms'] else 0,
                        "mean": statistics.mean(self.results['read_latencies_ms']) if self.results['read_latencies_ms'] else 0,
                        "median": statistics.median(self.results['read_latencies_ms']) if self.results['read_latencies_ms'] else 0,
                        "p95": sorted_read_lat[p95_idx] if self.results['read_latencies_ms'] else 0,
                        "p99": sorted_read_lat[p99_idx] if self.results['read_latencies_ms'] else 0
                    },
                    "throughput_stats": {
                        "writes": {
                            "min": min(self.results['wps_samples']) if self.results['wps_samples'] else 0,
                            "max": max(self.results['wps_samples']) if self.results['wps_samples'] else 0,
                            "mean": statistics.mean(self.results['wps_samples']) if self.results['wps_samples'] else 0,
                            "median": statistics.median(self.results['wps_samples']) if self.results['wps_samples'] else 0
                        },
                        "reads": {
                            "min": min(self.results['rps_samples']) if self.results['rps_samples'] else 0,
                            "max": max(self.results['rps_samples']) if self.results['rps_samples'] else 0,
                            "mean": statistics.mean(self.results['rps_samples']) if self.results['rps_samples'] else 0,
                            "median": statistics.median(self.results['rps_samples']) if self.results['rps_samples'] else 0
                        }
                    }
                },
                "pass": overall_pass
            }, f, indent=2)

        print(f"\nResults saved to {results_file}")


async def main():
    postgres_url = os.getenv("POSTGRES_URL", "postgresql://trading_user:staging_password_change_me@postgres-staging:5432/trading_staging")
    target_wps = int(os.getenv("LOAD_TEST_TARGET_WPS", "1000"))
    duration = int(os.getenv("LOAD_TEST_DURATION", "300"))

    tester = DatabaseThroughputTester(
        postgres_url=postgres_url,
        target_wps=target_wps,
        duration_sec=duration
    )

    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
