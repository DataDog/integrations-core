# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from contextlib import suppress

import httpx
from rich import print

from datadog_checks.base.stubs.common import MetricStubBase
from datadog_checks.dev.utils import get_metadata_metrics

WARM_UP_REQUESTS = 3
OPEN_METRICS_ENDPOINT = "http://localhost:9090/metrics"
BAKEND_API_ENDPOINT = "http://localhost:8000"
GATEWAY_ENDPOINT = "http://localhost:8080"
METADATA_METRICS_TO_EXCLUDE = ["krakend.api.http_client.request_read_errors.count"]


async def generate_sample_traffic(number_of_requests: int = WARM_UP_REQUESTS):
    """Generate sample traffic to KrakenD."""

    endpoints = [
        "/api/valid",
        "/api/invalid",
        "/api/timeout",
        "/api/cancelled",
        "/api/no-content-length",
    ]

    requests = [generate_traffic_for_endpoint(endpoint, number_of_requests) for endpoint in endpoints]
    requests.append(generate_cancelled_requests(number_of_requests))

    await asyncio.gather(*requests)

    print("✅ Sample traffic generated")


async def generate_traffic_for_endpoint(endpoint: str, number_of_requests: int = WARM_UP_REQUESTS):
    """Generate traffic for a specific endpoint."""
    print(f"🔄 Generating {number_of_requests} requests for {endpoint}...")
    with suppress(httpx.TimeoutException):
        async with httpx.AsyncClient() as client:
            for _ in range(number_of_requests):
                await client.get(f"{GATEWAY_ENDPOINT}{endpoint}", timeout=5)

    print(f"✅ Requests sent to {endpoint}")


async def generate_cancelled_requests(number_of_requests: int = WARM_UP_REQUESTS):
    """Generate cancelled requests by using short timeout to force client disconnection."""
    print("🔄 Generating cancelled requests...")

    for _ in range(number_of_requests):
        with suppress(httpx.TimeoutException):
            async with httpx.AsyncClient() as client:
                await client.get(
                    f"{GATEWAY_ENDPOINT}/api/cancelled",
                    timeout=0.1,  # Much shorter than KrakenD's 1s timeout
                )

    print("✅ Cancelled requests sent")


def get_metrics_from_metadata() -> dict[str, MetricStubBase]:
    """Get metrics from metadata."""
    metadata_metrics = get_metadata_metrics()
    for metric in METADATA_METRICS_TO_EXCLUDE:
        metadata_metrics.pop(metric)

    return metadata_metrics
