#!/usr/bin/env python3
"""
Order Stress Test
Simulates concurrent order placement to test order processing capacity
Target: 100 concurrent orders without degradation
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
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"


@dataclass
class Order:
    """Order data structure"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float = None
    stop_price: float = None
    client_order_id: str = None


class OrderStressTester:
    def __init__(self, base_url: str, concurrent_orders: int = 100, total_orders: int = 10000):
        self.base_url = base_url
        self.concurrent_orders = concurrent_orders
        self.total_orders = total_orders
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]
        self.results = {
            "orders_sent": 0,
            "orders_success": 0,
            "orders_failed": 0,
            "orders_rejected": 0,
            "latencies_ms": [],
            "errors": [],
            "orders_per_second": []
        }

    def generate_order(self) -> Order:
        """Generate a random order"""
        symbol = random.choice(self.symbols)
        side = random.choice([OrderSide.BUY, OrderSide.SELL])
        order_type = random.choice([OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_LOSS])

        base_price = {
            "BTCUSDT": 45000.0,
            "ETHUSDT": 3000.0,
            "BNBUSDT": 400.0,
            "ADAUSDT": 1.5,
            "DOTUSDT": 25.0
        }.get(symbol, 100.0)

        quantity = random.uniform(0.01, 1.0)

        order = Order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            client_order_id=f"test_{int(time.time() * 1000000)}_{random.randint(0, 999999)}"
        )

        if order_type in [OrderType.LIMIT, OrderType.STOP_LOSS]:
            # Set price slightly above/below market for limit orders
            if side == OrderSide.BUY:
                order.price = base_price * random.uniform(0.995, 0.999)
            else:
                order.price = base_price * random.uniform(1.001, 1.005)

        if order_type == OrderType.STOP_LOSS:
            if side == OrderSide.BUY:
                order.stop_price = base_price * random.uniform(1.005, 1.010)
            else:
                order.stop_price = base_price * random.uniform(0.990, 0.995)

        return order

    async def send_order(self, session: aiohttp.ClientSession, order: Order) -> Dict:
        """Send a single order to the trading engine"""
        start_time = time.time()

        payload = {
            "symbol": order.symbol,
            "side": order.side.value,
            "type": order.order_type.value,
            "quantity": order.quantity,
            "client_order_id": order.client_order_id
        }

        if order.price is not None:
            payload["price"] = order.price
        if order.stop_price is not None:
            payload["stop_price"] = order.stop_price

        try:
            async with session.post(
                f"{self.base_url}/api/v1/orders",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                if response.status == 200:
                    self.results["orders_success"] += 1
                    self.results["latencies_ms"].append(latency_ms)
                    result = await response.json()
                    return {
                        "success": True,
                        "latency_ms": latency_ms,
                        "order_id": result.get("order_id")
                    }
                elif response.status == 400:
                    self.results["orders_rejected"] += 1
                    error_text = await response.text()
                    return {
                        "success": False,
                        "rejected": True,
                        "error": error_text
                    }
                else:
                    self.results["orders_failed"] += 1
                    error_text = await response.text()
                    self.results["errors"].append({
                        "status": response.status,
                        "error": error_text,
                        "order": payload
                    })
                    return {"success": False, "error": error_text}

        except asyncio.TimeoutError:
            self.results["orders_failed"] += 1
            self.results["errors"].append({
                "error": "Timeout",
                "order": payload
            })
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            self.results["orders_failed"] += 1
            self.results["errors"].append({
                "error": str(e),
                "order": payload
            })
            return {"success": False, "error": str(e)}

    async def order_worker(self, session: aiohttp.ClientSession, order_queue: asyncio.Queue):
        """Worker that processes orders from the queue"""
        while True:
            try:
                order = await asyncio.wait_for(order_queue.get(), timeout=1.0)
                if order is None:  # Sentinel value to stop worker
                    break

                self.results["orders_sent"] += 1
                await self.send_order(session, order)
                order_queue.task_done()

            except asyncio.TimeoutError:
                continue

    async def monitor_throughput(self, stop_event: asyncio.Event):
        """Monitor orders per second"""
        last_count = 0

        while not stop_event.is_set():
            await asyncio.sleep(1.0)

            current_count = self.results["orders_success"]
            orders_per_sec = current_count - last_count
            last_count = current_count

            self.results["orders_per_second"].append(orders_per_sec)

            print(f"Orders/sec: {orders_per_sec} | "
                  f"Success: {self.results['orders_success']} | "
                  f"Rejected: {self.results['orders_rejected']} | "
                  f"Failed: {self.results['orders_failed']}")

    async def run_test(self):
        """Execute the stress test"""
        print(f"Starting order stress test...")
        print(f"Concurrent orders: {self.concurrent_orders}")
        print(f"Total orders: {self.total_orders}")
        print(f"Symbols: {', '.join(self.symbols)}")
        print("-" * 80)

        order_queue = asyncio.Queue(maxsize=self.concurrent_orders * 2)
        stop_event = asyncio.Event()

        async with aiohttp.ClientSession() as session:
            # Start workers
            workers = [
                asyncio.create_task(self.order_worker(session, order_queue))
                for _ in range(self.concurrent_orders)
            ]

            # Start throughput monitor
            monitor = asyncio.create_task(self.monitor_throughput(stop_event))

            # Generate and queue orders
            for _ in range(self.total_orders):
                order = self.generate_order()
                await order_queue.put(order)

            # Wait for all orders to be processed
            await order_queue.join()

            # Stop workers
            for _ in range(self.concurrent_orders):
                await order_queue.put(None)

            stop_event.set()

            # Wait for workers to finish
            await asyncio.gather(*workers, monitor, return_exceptions=True)

        self.print_results()

    def print_results(self):
        """Print test results and statistics"""
        print("\n" + "=" * 80)
        print("ORDER STRESS TEST RESULTS")
        print("=" * 80)

        print(f"\nTotal orders sent: {self.results['orders_sent']}")
        print(f"Successful: {self.results['orders_success']}")
        print(f"Rejected: {self.results['orders_rejected']}")
        print(f"Failed: {self.results['orders_failed']}")

        success_rate = (self.results['orders_success'] / self.results['orders_sent'] * 100) if self.results['orders_sent'] > 0 else 0
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

        if self.results['orders_per_second']:
            print(f"\nThroughput Statistics:")
            print(f"  Min: {min(self.results['orders_per_second'])} orders/sec")
            print(f"  Max: {max(self.results['orders_per_second'])} orders/sec")
            print(f"  Mean: {statistics.mean(self.results['orders_per_second']):.2f} orders/sec")
            print(f"  Median: {statistics.median(self.results['orders_per_second']):.2f} orders/sec")

        if self.results['errors']:
            print(f"\nErrors (showing first 10):")
            for error in self.results['errors'][:10]:
                print(f"  - {error}")

        # Pass/Fail criteria
        print("\n" + "-" * 80)
        latency_ok = statistics.mean(self.results['latencies_ms']) <= 100 if self.results['latencies_ms'] else False
        p99_ok = sorted_latencies[p99_idx] <= 500 if self.results['latencies_ms'] else False
        success_rate_ok = success_rate >= 95.0
        throughput_ok = statistics.mean(self.results['orders_per_second']) >= 50 if self.results['orders_per_second'] else False

        print("PASS/FAIL CRITERIA:")
        print(f"  {'✓' if latency_ok else '✗'} Mean latency <= 100ms")
        print(f"  {'✓' if p99_ok else '✗'} P99 latency <= 500ms")
        print(f"  {'✓' if success_rate_ok else '✗'} Success rate >= 95%")
        print(f"  {'✓' if throughput_ok else '✗'} Mean throughput >= 50 orders/sec")

        overall_pass = latency_ok and p99_ok and success_rate_ok and throughput_ok
        print(f"\nOVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
        print("=" * 80)

        # Save results
        results_file = "/results/order_stress_test.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                "test_name": "order_stress_test",
                "timestamp": time.time(),
                "configuration": {
                    "concurrent_orders": self.concurrent_orders,
                    "total_orders": self.total_orders,
                    "symbols": self.symbols
                },
                "results": {
                    "orders_sent": self.results['orders_sent'],
                    "orders_success": self.results['orders_success'],
                    "orders_rejected": self.results['orders_rejected'],
                    "orders_failed": self.results['orders_failed'],
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
                        "min": min(self.results['orders_per_second']) if self.results['orders_per_second'] else 0,
                        "max": max(self.results['orders_per_second']) if self.results['orders_per_second'] else 0,
                        "mean": statistics.mean(self.results['orders_per_second']) if self.results['orders_per_second'] else 0,
                        "median": statistics.median(self.results['orders_per_second']) if self.results['orders_per_second'] else 0
                    }
                },
                "pass": overall_pass
            }, f, indent=2)

        print(f"\nResults saved to {results_file}")


async def main():
    trading_engine_url = os.getenv("TRADING_ENGINE_URL", "http://trading-engine-staging:9000")
    concurrent_orders = int(os.getenv("LOAD_TEST_USERS", "100"))
    total_orders = int(os.getenv("LOAD_TEST_TOTAL_ORDERS", "10000"))

    tester = OrderStressTester(
        base_url=trading_engine_url,
        concurrent_orders=concurrent_orders,
        total_orders=total_orders
    )

    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
