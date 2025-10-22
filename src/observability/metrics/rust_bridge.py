"""
Rust Metrics Bridge - Connect Python collectors to Rust service endpoints.

This module provides a bridge between Rust services emitting Prometheus metrics
and the Python observability system, allowing seamless data collection and
storage in DuckDB.
"""
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

class RustMetricsBridge:
    """
    Bridge to collect metrics from Rust services via HTTP endpoints.

    Each Rust service exposes a /metrics endpoint in Prometheus text format.
    This bridge scrapes those endpoints and transforms the data for DuckDB storage.
    """

    def __init__(self, service_endpoints: Dict[str, str]):
        """
        Initialize the metrics bridge.

        Args:
            service_endpoints: Dictionary mapping service names to endpoint URLs
                Example: {
                    "market_data": "http://127.0.0.1:9091/metrics",
                    "execution": "http://127.0.0.1:9092/metrics",
                    "risk": "http://127.0.0.1:9093/metrics"
                }
        """
        self.service_endpoints = service_endpoints
        self.session: Optional[aiohttp.ClientSession] = None
        self.scrape_interval = 1.0  # seconds
        self.running = False

        logger.info(f"Initialized RustMetricsBridge with {len(service_endpoints)} services")

    async def start(self):
        """Start the metrics bridge and HTTP session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=5.0)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Metrics bridge started")

    async def stop(self):
        """Stop the metrics bridge and cleanup."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Metrics bridge stopped")

    async def scrape_service(self, service_name: str, endpoint_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape metrics from a single Rust service endpoint.

        Args:
            service_name: Name of the service (e.g., "market_data")
            endpoint_url: HTTP endpoint URL

        Returns:
            Dictionary of parsed metrics or None if scraping failed
        """
        if not self.session:
            logger.error("Session not initialized. Call start() first.")
            return None

        try:
            async with self.session.get(endpoint_url) as response:
                if response.status == 200:
                    text = await response.text()
                    metrics = self._parse_prometheus_text(text, service_name)
                    logger.debug(f"Scraped {len(metrics)} metrics from {service_name}")
                    return metrics
                else:
                    logger.warning(
                        f"Failed to scrape {service_name}: HTTP {response.status}"
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.debug(f"Connection error scraping {service_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {service_name}: {e}")
            return None

    def _parse_prometheus_text(
        self, text: str, service_name: str
    ) -> Dict[str, Any]:
        """
        Parse Prometheus text format into structured metrics.

        Args:
            text: Prometheus text format metrics
            service_name: Name of the source service

        Returns:
            Dictionary of parsed metrics
        """
        metrics = {
            "timestamp": datetime.utcnow(),
            "service": service_name,
            "counters": {},
            "gauges": {},
            "histograms": {},
        }

        current_metric_name = None
        current_metric_type = None

        for line in text.split('\n'):
            line = line.strip()

            # Skip empty lines and comments that aren't HELP/TYPE
            if not line or (line.startswith('#') and not line.startswith('# TYPE') and not line.startswith('# HELP')):
                continue

            # Parse TYPE declarations
            if line.startswith('# TYPE'):
                parts = line.split()
                if len(parts) >= 4:
                    current_metric_name = parts[2]
                    current_metric_type = parts[3]
                continue

            # Parse HELP declarations (just skip for now)
            if line.startswith('# HELP'):
                continue

            # Parse metric values
            if not line.startswith('#'):
                # Format: metric_name{labels} value [timestamp]
                # or:     metric_name value [timestamp]
                try:
                    # Split on first space to separate name+labels from value
                    parts = line.split(None, 1)
                    if len(parts) < 2:
                        continue

                    name_and_labels = parts[0]
                    value_str = parts[1].split()[0]  # Take first part (value, ignore timestamp)

                    # Parse metric name and labels
                    if '{' in name_and_labels:
                        metric_name = name_and_labels[:name_and_labels.index('{')]
                        labels_str = name_and_labels[name_and_labels.index('{')+1:name_and_labels.index('}')]
                        labels = self._parse_labels(labels_str)
                    else:
                        metric_name = name_and_labels
                        labels = {}

                    # Parse value
                    try:
                        value = float(value_str)
                    except ValueError:
                        logger.warning(f"Invalid metric value: {value_str}")
                        continue

                    # Store in appropriate category
                    metric_key = metric_name
                    if labels:
                        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
                        metric_key = f"{metric_name}{{{label_str}}}"

                    # Determine type (use declared type or infer from name)
                    metric_type = current_metric_type or self._infer_metric_type(metric_name)

                    if metric_type == "counter":
                        metrics["counters"][metric_key] = {
                            "name": metric_name,
                            "value": value,
                            "labels": labels
                        }
                    elif metric_type == "gauge":
                        metrics["gauges"][metric_key] = {
                            "name": metric_name,
                            "value": value,
                            "labels": labels
                        }
                    elif metric_type == "histogram":
                        if metric_key not in metrics["histograms"]:
                            metrics["histograms"][metric_key] = {
                                "name": metric_name,
                                "values": [],
                                "labels": labels
                            }
                        metrics["histograms"][metric_key]["values"].append(value)

                except Exception as e:
                    logger.debug(f"Failed to parse metric line '{line}': {e}")
                    continue

        return metrics

    def _parse_labels(self, labels_str: str) -> Dict[str, str]:
        """Parse Prometheus label string into dictionary."""
        labels = {}
        if not labels_str:
            return labels

        # Split by comma, but handle quoted values
        parts = []
        current = []
        in_quotes = False

        for char in labels_str:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                if current:
                    parts.append(''.join(current).strip())
                    current = []
                continue
            current.append(char)

        if current:
            parts.append(''.join(current).strip())

        # Parse each label
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                labels[key] = value

        return labels

    def _infer_metric_type(self, metric_name: str) -> str:
        """Infer metric type from name if not declared."""
        if "_total" in metric_name or "_count" in metric_name:
            return "counter"
        elif "_bucket" in metric_name or "_sum" in metric_name:
            return "histogram"
        else:
            return "gauge"

    async def scrape_all_services(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Scrape metrics from all configured services concurrently.

        Returns:
            Dictionary mapping service names to their metrics
        """
        tasks = [
            self.scrape_service(name, url)
            for name, url in self.service_endpoints.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        metrics_by_service = {}
        for (service_name, _), result in zip(self.service_endpoints.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Error scraping {service_name}: {result}")
                metrics_by_service[service_name] = None
            else:
                metrics_by_service[service_name] = result

        return metrics_by_service

    async def continuous_scrape(self, callback=None):
        """
        Continuously scrape metrics at regular intervals.

        Args:
            callback: Optional async function to call with scraped metrics
                     Signature: async def callback(metrics: Dict[str, Any])
        """
        self.running = True
        logger.info(f"Starting continuous scrape (interval: {self.scrape_interval}s)")

        while self.running:
            try:
                metrics = await self.scrape_all_services()

                if callback:
                    await callback(metrics)

                await asyncio.sleep(self.scrape_interval)
            except asyncio.CancelledError:
                logger.info("Continuous scrape cancelled")
                break
            except Exception as e:
                logger.error(f"Error in continuous scrape: {e}")
                await asyncio.sleep(self.scrape_interval)

    def stop_continuous_scrape(self):
        """Stop the continuous scraping loop."""
        self.running = False
        logger.info("Stopping continuous scrape")


# Singleton instance for easy access
_bridge_instance: Optional[RustMetricsBridge] = None

def get_rust_metrics_bridge() -> RustMetricsBridge:
    """Get or create the global RustMetricsBridge instance."""
    global _bridge_instance

    if _bridge_instance is None:
        endpoints = {
            "market_data": "http://127.0.0.1:9091/metrics",
            "execution": "http://127.0.0.1:9092/metrics",
            "risk": "http://127.0.0.1:9093/metrics",
        }
        _bridge_instance = RustMetricsBridge(endpoints)

    return _bridge_instance
