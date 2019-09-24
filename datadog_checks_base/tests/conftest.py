import os

import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

HERE = get_here()


@pytest.fixture(scope="session")
def socks5_proxy():
    with docker_run(compose_file=os.path.join(HERE, "compose", "socks5-proxy.yaml")):
        yield "proxy_user:proxy_password@localhost:1080"


@pytest.fixture(scope="session")
def kerberos():

    realm = "EXAMPLE.COM"
    webserver_hostname = "web.example.com"
    common_config = {
      "url": "http://localhost:80",
      "keytab": os.path.join("/tmp", "shared-volume", "http.keytab"),
      "cache": os.path.join("/tmp", "shared-volume", "krbc5ccname"),
      "realm": realm,
      "hostname": webserver_hostname,
      "principal": "HTTP/{}@{}".format(webserver_hostname, realm)
    }

    compose_file = os.path.join(HERE, "compose", "kerberos.yaml")

    with docker_run(compose_file=compose_file, conditions=[CheckDockerLogs(compose_file, "ReadyToConnect")]):
        yield common_config
