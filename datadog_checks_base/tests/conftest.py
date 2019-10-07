import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

HERE = get_here()


@pytest.fixture(scope="session")
def socks5_proxy():
    compose_file = os.path.join(HERE, "compose", "socks5-proxy.yaml")
    with docker_run(
        compose_file=compose_file, log_patterns=['Start listening proxy service on port']
    ):
        yield "proxy_user:proxy_password@localhost:1080"
