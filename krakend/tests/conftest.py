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
from datadog_checks.dev.structures import LazyFunction
from datadog_checks.krakend import KrakendCheck
from tests.helpers import BAKEND_API_ENDPOINT, GATEWAY_ENDPOINT, OPEN_METRICS_ENDPOINT, generate_sample_traffic
from tests.types import InstanceBuilder

COMPOSE_FILE_E2E = Path(__file__).parent / "docker" / "docker-compose.yml"
COMPOSE_FILE_LAB = Path(__file__).parent / "lab" / "docker-compose.yml"


@pytest.fixture(scope="session")
def is_lab() -> bool:
    return os.environ.get("KRAKEND_IS_LAB", "false") == "true"


def run_docker_lab(env_vars: dict[str, str], conditions: list[LazyFunction]):
    with docker_run(
        compose_file=str(COMPOSE_FILE_LAB),
        env_vars=env_vars,
        conditions=conditions,
    ):
        yield (
            {
                "instances": [{"openmetrics_endpoint": OPEN_METRICS_ENDPOINT}],
            },
            {
                "docker_volumes": [
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                    "/var/lib/docker/containers:/var/lib/docker/containers:ro",
                    "/opt/datadog-agent/run:/opt/datadog-agent/run:rw",
                ],
            },
        )


def run_docker_e2e(env_vars: dict[str, str], conditions: list[LazyFunction]):
    with docker_run(
        compose_file=str(COMPOSE_FILE_E2E),
        env_vars=env_vars,
        conditions=conditions,
    ):
        asyncio.run(generate_sample_traffic())

        yield {
            "instances": [{"openmetrics_endpoint": OPEN_METRICS_ENDPOINT}],
        }


@pytest.fixture(scope="session")
def dd_environment(dd_save_state, is_lab):
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

    if is_lab:
        yield from run_docker_lab(env_vars, conditions)
    else:
        yield from run_docker_e2e(env_vars, conditions)


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
