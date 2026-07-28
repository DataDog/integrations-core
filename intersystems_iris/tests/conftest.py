# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path
from typing import Iterator

import pytest
import requests

from datadog_checks.base.types import InstanceType
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.dev.docker import get_docker_hostname
from datadog_checks.dev.utils import find_free_port

HERE = Path(__file__).parent
COMPOSE_FILE = HERE / "docker" / "docker-compose.yaml"


def _interop_metrics_present(endpoint: str) -> None:
    # The `iris-init.sh` post-start hook (wired via `--after` in the compose command)
    # enables interoperability, loads a demo production, and pushes test traffic in the
    # background. That happens independently of the container `healthcheck` (which only
    # probes that the endpoint returns 200), so wait until the runtime-gated
    # `iris_interop_*` family actually shows up before yielding, otherwise the check may
    # scrape the endpoint before the production is running.
    response = requests.get(endpoint, timeout=10)
    response.raise_for_status()
    assert 'iris_interop_hosts' in response.text, "interop metrics not present yet"


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[dict]:
    host = get_docker_hostname()
    port = find_free_port(host)
    endpoint = f"http://{host}:{port}/api/monitor/metrics"

    conditions = [
        CheckEndpoints(endpoint, attempts=120, wait=2),
        WaitFor(lambda: _interop_metrics_present(endpoint), attempts=60, wait=5),
    ]

    with docker_run(
        compose_file=str(COMPOSE_FILE),
        env_vars={"IRIS_PORT": str(port)},
        conditions=conditions,
        wait_for_health=True,
    ):
        yield {"instances": [{"openmetrics_endpoint": endpoint}]}


@pytest.fixture
def instance() -> InstanceType:
    # Used only by the offline unit tests, which mock every HTTP call, so the exact host/port
    # here is never actually dialed. Integration/e2e tests use the dynamic, free-port endpoint
    # yielded by `dd_environment` instead (see `test_integration.py`).
    return {"openmetrics_endpoint": "http://localhost:52773/api/monitor/metrics"}
