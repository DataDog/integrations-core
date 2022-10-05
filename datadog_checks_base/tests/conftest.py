import os

import pytest
import requests

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev import TempDir, docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor

HERE = get_here()


@pytest.fixture(scope="session")
def socks5_proxy():
    proxy = "localhost:1080"
    auth = "proxy_user:proxy_password"

    def check_proxy():
        proxies = {'http': 'socks5h://{}@{}'.format(auth, proxy)}
        url = 'http://www.google.com'
        resp = requests.get(url, proxies=proxies)
        resp.raise_for_status()

    compose_file = os.path.join(HERE, "compose", "socks5-proxy.yaml")
    with docker_run(
        compose_file=compose_file,
        log_patterns=['Start listening proxy service on port'],
        conditions=[WaitFor(check_proxy)],
        attempts=2,
    ):
        yield "proxy_user:proxy_password@localhost:1080"


@pytest.fixture(scope="session")
def kerberos():
    with TempDir() as tmp_dir:
        shared_volume = os.path.join(tmp_dir, "shared-volume")
        compose_file = os.path.join(HERE, "compose", "kerberos", "kerberos.yaml")
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
            attempts=2,
        ):
            yield common_config


@pytest.fixture(scope="session")
def kerberos_agent():
    with TempDir() as tmp_dir:
        shared_volume = os.path.join(tmp_dir, "shared-volume")
        compose_file = os.path.join(HERE, "compose", "kerberos-agent.yaml")
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
            "dd_api_key": os.getenv('DD_API_KEY'),
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
                'DD_API_KEY': common_config['dd_api_key'],
            },
            conditions=[CheckDockerLogs(compose_file, "ReadyToConnect")],
        ):
            yield common_config


@pytest.fixture(scope="session")
def uds_path():
    if Platform.is_mac():
        # See: https://github.com/docker/for-mac/issues/483
        pytest.skip('Sharing Unix sockets is not supported by Docker for Mac.')

    with TempDir() as tmp_dir:
        compose_file = os.path.join(HERE, 'compose', 'uds', 'uds.yaml')
        uds_filename = 'tmp.sock'
        uds_path = os.path.join(tmp_dir, uds_filename)
        with docker_run(
            compose_file=compose_file,
            env_vars={
                "UDS_HOST_DIRECTORY": tmp_dir,
                'UDS_FILENAME': uds_filename,
            },
            conditions=[WaitFor(lambda: os.path.exists(uds_path))],
            attempts=2,
        ):
            yield uds_path


def pytest_configure(config):
    config.addinivalue_line('markers', 'openmetrics: base/checks/openmetrics/v2/*')
    config.addinivalue_line('markers', 'openmetrics_transformers: base/checks/openmetrics/v2/transformers/*')
