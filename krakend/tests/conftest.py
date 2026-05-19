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

INTEGRATIONS_CORE_ROOT = Path(__file__).resolve().parents[2]
KRAKEND_AUTOCONF = Path(__file__).parent.parent / "datadog_checks" / "krakend" / "data" / "auto_conf.yaml"
DISCOVERY_HELPERS_DIR = (
    INTEGRATIONS_CORE_ROOT / "datadog_checks_base" / "datadog_checks" / "base" / "utils" / "discovery"
)
OPENMETRICS_V2_BASE_PY = (
    INTEGRATIONS_CORE_ROOT
    / "datadog_checks_base"
    / "datadog_checks"
    / "base"
    / "checks"
    / "openmetrics"
    / "v2"
    / "base.py"
)
AGENTCHECK_BASE_PY = INTEGRATIONS_CORE_ROOT / "datadog_checks_base" / "datadog_checks" / "base" / "checks" / "base.py"
SITE_PACKAGES = "/opt/datadog-agent/embedded/lib/python3.13/site-packages"


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

        yield (
            {
                "instances": [{"openmetrics_endpoint": OPEN_METRICS_ENDPOINT}],
            },
            {
                # The autoconfig YAML + base helpers overlay let the
                # discovery test exercise AD + discover() in this same
                # env. They are no-ops for the regular test_e2e, which
                # passes its own explicit config to dd_agent_check.
                "docker_volumes": [
                    f"{KRAKEND_AUTOCONF}:/etc/datadog-agent/conf.d/krakend.d/auto_conf.yaml:ro",
                    f"{DISCOVERY_HELPERS_DIR}:{SITE_PACKAGES}/datadog_checks/base/utils/discovery:ro",
                    f"{OPENMETRICS_V2_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/openmetrics/v2/base.py:ro",
                    f"{AGENTCHECK_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/base.py:ro",
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                ],
            },
        )


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
