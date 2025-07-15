# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import os
from pathlib import Path
from typing import Any

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.krakend import KrakendCheck
from tests.helpers import BAKEND_API_ENDPOINT, GATEWAY_ENDPOINT, OPEN_METRICS_ENDPOINT, generate_sample_traffic
from tests.types import InstanceBuilder

COMPOSE_FILE = Path(__file__).parent / "docker" / "docker-compose.yml"


@pytest.fixture(scope="session")
def dd_environment(dd_save_state):
    """
    Integration test fixture that starts KrakenD and FastAPI services using Docker Compose.
    Waits for services to be healthy and generates sample traffic to ensure metrics are available.
    """

    env_vars = {
        'COMPOSE_PROJECT_NAME': 'krakend_test',
        'KRAKEND_VERSION': os.environ['KRAKEND_VERSION'],
    }

    conditions = [
        CheckEndpoints(f"{GATEWAY_ENDPOINT}/__health", attempts=120, wait=2),  # KrakenD health
        CheckEndpoints(OPEN_METRICS_ENDPOINT, attempts=120, wait=2),  # Metrics endpoint
        CheckEndpoints(f"{BAKEND_API_ENDPOINT}/valid/", attempts=120, wait=2),  # FastAPI backend
        CheckEndpoints(f"{GATEWAY_ENDPOINT}/api/valid/", attempts=120, wait=2),  # KrakenD endpoint
    ]

    with docker_run(
        compose_file=str(COMPOSE_FILE),
        env_vars=env_vars,
        conditions=conditions,
    ):
        asyncio.run(generate_sample_traffic())

        yield {"instances": [{"openmetrics_endpoint": OPEN_METRICS_ENDPOINT}]}


@pytest.fixture
def check(instance: InstanceBuilder, request: pytest.FixtureRequest):
    if hasattr(request, "param"):
        params = request.param
        go_metrics = params.get("go_metrics", True)
        process_metrics = params.get("process_metrics", True)
        return KrakendCheck("krakend", {}, [instance(go_metrics=go_metrics, process_metrics=process_metrics)])

    return KrakendCheck("krakend", {}, [instance()])


@pytest.fixture
def instance() -> InstanceBuilder:
    def builder(go_metrics=True, process_metrics=True, host="localhost", port=9090) -> dict[str, Any]:
        return {
            "openmetrics_endpoint": f"http://{host}:{port}/metrics",
            "go_metrics": go_metrics,
            "process_metrics": process_metrics,
        }

    return builder
