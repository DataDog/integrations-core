import os

import pytest

from datadog_checks.dev import TempDir, docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

HERE = get_here()


@pytest.fixture(scope="session")
def socks5_proxy():
    compose_file = os.path.join(HERE, "compose", "socks5-proxy.yaml")
    with docker_run(compose_file=compose_file, log_patterns=['Start listening proxy service on port']):
        yield "proxy_user:proxy_password@localhost:1080"


@pytest.fixture(scope="session")
def kerberos():

    with TempDir() as tmp_dir:
        shared_volume = os.path.join(tmp_dir, "shared-volume")
        compose_file = os.path.join(HERE, "compose", "kerberos.yaml")
        realm = "EXAMPLE.COM"
        svc = "HTTP"
        webserver_hostname = "web.example.com"
        webserver_port = "8080"
        krb5_conf = os.path.join(HERE, "fixtures", "kerberos", "krb5.conf")

        common_config = {
            "url": "http://localhost:{}".format(webserver_port),
            "keytab": os.path.join(shared_volume, "http.keytab"),
            "cache": os.path.join(shared_volume),
            "realm": realm,
            "svc": svc,
            "hostname": webserver_hostname,
            "principal": "user/inkeytab@{}".format(realm),
            "tmp_dir": tmp_dir,
        }

        with docker_run(
            compose_file=compose_file,
            env_vars={
                'SHARED_VOLUME': shared_volume,
                'KRB5_CONFIG': krb5_conf,
                'KRB5_KEYTAB': common_config['keytab'],
                'KRB5_CCNAME': common_config['cache'],
                'KRB5_REALM': common_config['realm'],
                'KRB5_SVC': common_config['svc'],
                'WEBHOST': common_config['hostname'],
                'WEBPORT': webserver_port,
            },
            conditions=[CheckDockerLogs(compose_file, "ReadyToConnect")],
        ):
            yield common_config
