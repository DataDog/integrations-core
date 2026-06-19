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
    # from datadog_checks.dev.docker import get_docker_hostname
    # from datadog_checks.dev.utils import find_free_port
    #
    # host = get_docker_hostname()
    # port = find_free_port(host)
    # compose_file = Path(__file__).parent / "docker" / "docker-compose.yml"
    # with docker_run(
    #     compose_file=str(compose_file),
    #     env_vars={{"PORT": str(port)}},
    #     conditions=[CheckEndpoints(f"http://{{host}}:{{port}}/health", attempts=60, wait=2)],
    # ):
    #     yield {{"instances": [{{"openmetrics_endpoint": f"http://{{host}}:{{port}}/metrics"}}]}}
    yield


@pytest.fixture
def instance() -> InstanceType:
    return {{}}
