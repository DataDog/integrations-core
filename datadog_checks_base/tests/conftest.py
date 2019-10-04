import os

import pytest

from datadog_checks.dev import docker_run, get_here

HERE = get_here()


@pytest.fixture(scope="session")
def socks5_proxy():
    with docker_run(compose_file=os.path.join(HERE, "compose", "socks5-proxy.yaml"), sleep=5):
        yield "proxy_user:proxy_password@localhost:1080"
