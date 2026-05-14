{license_header}
from typing import Iterator

import pytest

from datadog_checks.base.types import InstanceType


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[None]:
    # When the integration has a real test environment, wire it here.
    # Typical Docker Compose setup:
    #
    # from pathlib import Path
    # from datadog_checks.dev import docker_run
    # from datadog_checks.dev.conditions import CheckEndpoints
    #
    # compose_file = Path(__file__).parent / "docker" / "docker-compose.yml"
    # with docker_run(
    #     compose_file=str(compose_file),
    #     conditions=[CheckEndpoints("http://localhost:1234/health", attempts=60, wait=2)],
    # ):
    #     yield {{"instances": [{{"openmetrics_endpoint": "http://localhost:1234/metrics"}}]}}
    yield


@pytest.fixture
def instance() -> InstanceType:
    return {{}}
