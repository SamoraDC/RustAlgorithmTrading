#!/usr/bin/env python3
"""
WebSocket Concurrency Test
Tests WebSocket connection handling and streaming performance
Target: 50 concurrent WebSocket connections
"""

import asyncio
import websockets
import time
import json
import os
import statistics
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class WebSocketMetrics:
    """Metrics for a single WebSocket connection"""
    connection_id: int
    connected_at: float
    messages_received: int = 0
    messages_sent: int = 0
    latencies_ms: List[float] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.latencies_ms is None:
            self.latencies_ms = []
        if self.errors is None:
            self.errors = []


class WebSocketConcurrencyTester:
    def __init__(self, ws_url: str, num_connections: int = 50, duration_sec: int = 300):
        self.ws_url = ws_url
        self.num_connections = num_connections
        self.duration_sec = duration_sec
        self.connections: List[WebSocketMetrics] = []
        self.results = {
            "connections_attempted": 0,
            "connections_successful": 0,
            "connections_failed": 0,
            "total_messages_received": 0,
            "total_messages_sent": 0,
            "connection_latencies_ms": [],
            "message_latencies_ms": [],
            "errors": []
        }

    async def websocket_client(self, connection_id: int, stop_event: asyncio.Event):
        """Maintain a WebSocket connection and handle messages"""
        metrics = WebSocketMetrics(
            connection_id=connection_id,
            connected_at=time.time()
        )
        self.connections.append(metrics)

        ws_uri = f"{self.ws_url}/ws/market_data"

        try:
            connect_start = time.time()
            async with websockets.connect(ws_uri) as websocket:
                connect_latency_ms = (time.time() - connect_start) * 1000
                self.results["connection_latencies_ms"].append(connect_latency_ms)
                self.results["connections_successful"] += 1

                print(f"Connection {connection_id}: Connected (latency: {connect_latency_ms:.2f}ms)")

                # Subscribe to market data
                subscribe_msg = {
                    "action": "subscribe",
                    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                metrics.messages_sent += 1
                self.results["total_messages_sent"] += 1

                # Receive messages until stop event
                while not stop_event.is_set():
                    try:
                        message_start = time.time()
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=1.0
                        )

                        message_latency_ms = (time.time() - message_start) * 1000

                        metrics.messages_received += 1
                        metrics.latencies_ms.append(message_latency_ms)
                        self.results["total_messages_received"] += 1
                        self.results["message_latencies_ms"].append(message_latency_ms)

                        # Periodically send ping
                        if metrics.messages_received % 100 == 0:
                            await websocket.send(json.dumps({"action": "ping"}))
                            metrics.messages_sent += 1
                            self.results["total_messages_sent"] += 1

                    except asyncio.TimeoutError:
                        # No message received in timeout window, continue
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print(f"Connection {connection_id}: Closed by server")
                        break

        except Exception as e:
            self.results["connections_failed"] += 1
            error_msg = f"Connection {connection_id} error: {str(e)}"
            print(error_msg)
            metrics.errors.append(error_msg)
            self.results["errors"].append(error_msg)

    async def monitor_connections(self, stop_event: asyncio.Event):
        """Monitor connection health and message rates"""
        last_messages = 0

        while not stop_event.is_set():
            await asyncio.sleep(5.0)

            current_messages = self.results["total_messages_received"]
            messages_per_sec = (current_messages - last_messages) / 5.0
            last_messages = current_messages

            active_connections = sum(1 for m in self.connections if len(m.errors) == 0)

            print(f"\n--- Status Update ---")
            print(f"Active connections: {active_connections}/{self.num_connections}")
            print(f"Messages/sec: {messages_per_sec:.2f}")
            print(f"Total messages received: {current_messages}")
            print(f"Total messages sent: {self.results['total_messages_sent']}")
            print("-" * 80)

    async def run_test(self):
        """Execute the WebSocket concurrency test"""
        print(f"Starting WebSocket concurrency test...")
        print(f"Concurrent connections: {self.num_connections}")
        print(f"Duration: {self.duration_sec} seconds")
        print(f"WebSocket URL: {self.ws_url}")
        print("-" * 80)

        stop_event = asyncio.Event()

        # Start all WebSocket clients
        clients = [
            asyncio.create_task(self.websocket_client(i, stop_event))
            for i in range(self.num_connections)
        ]

        # Start monitor
        monitor = asyncio.create_task(self.monitor_connections(stop_event))

        # Wait for test duration
        await asyncio.sleep(self.duration_sec)

        # Stop all clients
        stop_event.set()

        # Wait for clients to finish
        await asyncio.gather(*clients, monitor, return_exceptions=True)

        self.print_results()

    def print_results(self):
        """Print test results and statistics"""
        print("\n" + "=" * 80)
        print("WEBSOCKET CONCURRENCY TEST RESULTS")
        print("=" * 80)

        print(f"\nConnections:")
        print(f"  Attempted: {self.num_connections}")
        print(f"  Successful: {self.results['connections_successful']}")
        print(f"  Failed: {self.results['connections_failed']}")

        success_rate = (self.results['connections_successful'] / self.num_connections * 100) if self.num_connections > 0 else 0
        print(f"  Success rate: {success_rate:.2f}%")

        print(f"\nMessages:")
        print(f"  Total received: {self.results['total_messages_received']}")
        print(f"  Total sent: {self.results['total_messages_sent']}")

        avg_messages_per_conn = self.results['total_messages_received'] / self.results['connections_successful'] if self.results['connections_successful'] > 0 else 0
        print(f"  Average per connection: {avg_messages_per_conn:.2f}")

        if self.results['connection_latencies_ms']:
            print(f"\nConnection Latency Statistics:")
            print(f"  Min: {min(self.results['connection_latencies_ms']):.2f} ms")
            print(f"  Max: {max(self.results['connection_latencies_ms']):.2f} ms")
            print(f"  Mean: {statistics.mean(self.results['connection_latencies_ms']):.2f} ms")
            print(f"  Median: {statistics.median(self.results['connection_latencies_ms']):.2f} ms")

        if self.results['message_latencies_ms']:
            print(f"\nMessage Latency Statistics:")
            print(f"  Min: {min(self.results['message_latencies_ms']):.2f} ms")
            print(f"  Max: {max(self.results['message_latencies_ms']):.2f} ms")
            print(f"  Mean: {statistics.mean(self.results['message_latencies_ms']):.2f} ms")
            print(f"  Median: {statistics.median(self.results['message_latencies_ms']):.2f} ms")

            sorted_msg_lat = sorted(self.results['message_latencies_ms'])
            p95_idx = int(len(sorted_msg_lat) * 0.95)
            p99_idx = int(len(sorted_msg_lat) * 0.99)
            print(f"  P95: {sorted_msg_lat[p95_idx]:.2f} ms")
            print(f"  P99: {sorted_msg_lat[p99_idx]:.2f} ms")

        # Per-connection statistics
        print(f"\nPer-Connection Statistics:")
        successful_connections = [m for m in self.connections if len(m.errors) == 0]

        if successful_connections:
            messages_per_conn = [m.messages_received for m in successful_connections]
            print(f"  Min messages: {min(messages_per_conn)}")
            print(f"  Max messages: {max(messages_per_conn)}")
            print(f"  Mean messages: {statistics.mean(messages_per_conn):.2f}")
            print(f"  Median messages: {statistics.median(messages_per_conn):.2f}")

        if self.results['errors']:
            print(f"\nErrors (showing first 10):")
            for error in self.results['errors'][:10]:
                print(f"  - {error}")

        # Pass/Fail criteria
        print("\n" + "-" * 80)
        connection_success_ok = success_rate >= 95.0
        message_throughput_ok = self.results['total_messages_received'] > 0
        message_latency_ok = statistics.median(self.results['message_latencies_ms']) <= 100 if self.results['message_latencies_ms'] else False
        stable_connections = len(successful_connections) >= self.num_connections * 0.9

        print("PASS/FAIL CRITERIA:")
        print(f"  {'✓' if connection_success_ok else '✗'} Connection success rate >= 95%")
        print(f"  {'✓' if message_throughput_ok else '✗'} Messages received > 0")
        print(f"  {'✓' if message_latency_ok else '✗'} Median message latency <= 100ms")
        print(f"  {'✓' if stable_connections else '✗'} Stable connections >= 90% of target")

        overall_pass = connection_success_ok and message_throughput_ok and message_latency_ok and stable_connections
        print(f"\nOVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
        print("=" * 80)

        # Save results
        results_file = "/results/websocket_concurrency_test.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                "test_name": "websocket_concurrency_test",
                "timestamp": time.time(),
                "configuration": {
                    "num_connections": self.num_connections,
                    "duration_sec": self.duration_sec,
                    "ws_url": self.ws_url
                },
                "results": {
                    "connections": {
                        "attempted": self.num_connections,
                        "successful": self.results['connections_successful'],
                        "failed": self.results['connections_failed'],
                        "success_rate": success_rate
                    },
                    "messages": {
                        "total_received": self.results['total_messages_received'],
                        "total_sent": self.results['total_messages_sent'],
                        "avg_per_connection": avg_messages_per_conn
                    },
                    "connection_latency_stats": {
                        "min": min(self.results['connection_latencies_ms']) if self.results['connection_latencies_ms'] else 0,
                        "max": max(self.results['connection_latencies_ms']) if self.results['connection_latencies_ms'] else 0,
                        "mean": statistics.mean(self.results['connection_latencies_ms']) if self.results['connection_latencies_ms'] else 0,
                        "median": statistics.median(self.results['connection_latencies_ms']) if self.results['connection_latencies_ms'] else 0
                    },
                    "message_latency_stats": {
                        "min": min(self.results['message_latencies_ms']) if self.results['message_latencies_ms'] else 0,
                        "max": max(self.results['message_latencies_ms']) if self.results['message_latencies_ms'] else 0,
                        "mean": statistics.mean(self.results['message_latencies_ms']) if self.results['message_latencies_ms'] else 0,
                        "median": statistics.median(self.results['message_latencies_ms']) if self.results['message_latencies_ms'] else 0,
                        "p95": sorted_msg_lat[p95_idx] if self.results['message_latencies_ms'] else 0,
                        "p99": sorted_msg_lat[p99_idx] if self.results['message_latencies_ms'] else 0
                    }
                },
                "pass": overall_pass
            }, f, indent=2)

        print(f"\nResults saved to {results_file}")


async def main():
    # Convert HTTP URL to WebSocket URL
    trading_engine_url = os.getenv("TRADING_ENGINE_URL", "http://trading-engine-staging:9000")
    ws_url = trading_engine_url.replace("http://", "ws://").replace("https://", "wss://")

    num_connections = int(os.getenv("LOAD_TEST_WS_CONNECTIONS", "50"))
    duration = int(os.getenv("LOAD_TEST_DURATION", "300"))

    tester = WebSocketConcurrencyTester(
        ws_url=ws_url,
        num_connections=num_connections,
        duration_sec=duration
    )

    await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())
