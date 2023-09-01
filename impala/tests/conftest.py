# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack, contextmanager
from unittest import mock

import pytest

from datadog_checks.dev import EnvVars, TempDir, docker_run, get_docker_hostname, get_here
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.impala import ImpalaCheck


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "metrics_file(directory, name): The path of the fixture file to use for this test"
    )


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(get_here(), "compose", "docker-compose.yaml")
    conditions = []

    # daemon, statestore, catalog
    for port in [25000, 25010, 25020]:
        conditions.append(CheckEndpoints(f"http://{get_docker_hostname()}:{port}/metrics_prometheus"))

    with docker_run(
        compose_file=compose_file,
        conditions=conditions,
        wrappers=[create_log_volumes()],
        sleep=10,
    ):

        yield {
            'instances': [
                {
                    "openmetrics_endpoint": f"http://{get_docker_hostname()}:25000/metrics_prometheus",
                    "service_type": "daemon",
                },
                {
                    "openmetrics_endpoint": f"http://{get_docker_hostname()}:25010/metrics_prometheus",
                    "service_type": "statestore",
                },
                {
                    "openmetrics_endpoint": f"http://{get_docker_hostname()}:25020/metrics_prometheus",
                    "service_type": "catalog",
                },
            ]
        }


@pytest.fixture
def daemon_instance():
    return {
        "openmetrics_endpoint": f"http://{get_docker_hostname()}:25000/metrics_prometheus",
        "service_type": "daemon",
    }


@pytest.fixture
def daemon_check(daemon_instance):
    return ImpalaCheck("impala", {}, [daemon_instance])


@pytest.fixture
def statestore_instance():
    return {
        "openmetrics_endpoint": f"http://{get_docker_hostname()}:25010/metrics_prometheus",
        "service_type": "statestore",
    }


@pytest.fixture
def statestore_check(statestore_instance):
    return ImpalaCheck("impala", {}, [statestore_instance])


@pytest.fixture
def catalog_instance():
    return {
        "openmetrics_endpoint": f"http://{get_docker_hostname()}:25020/metrics_prometheus",
        "service_type": "catalog",
    }


@pytest.fixture
def catalog_check(catalog_instance):
    return ImpalaCheck("impala", {}, [catalog_instance])


@pytest.fixture()
def mock_metrics(request):
    metrics_file = request.node.get_closest_marker("metrics_file")
    with open(
        os.path.join(os.path.dirname(__file__), "fixtures", metrics_file.args[0], metrics_file.args[1]), "r"
    ) as fixture_file:
        content = fixture_file.read()

    with mock.patch(
        "requests.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: content.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield


@contextmanager
def create_log_volumes():
    env_vars = {}
    docker_volumes = get_state('docker_volumes', [])

    with ExitStack() as stack:
        for service in ["impalad", "catalogd", "statestored"]:
            d = stack.enter_context(TempDir(service))
            os.chmod(d, 0o777)
            docker_volumes.append(f'{d}:/var/log/{service}')
            env_vars[f"{service.upper()}_LOG_FOLDER"] = d

        save_state('logs_config', get_logs_config())
        save_state('docker_volumes', docker_volumes)

        with EnvVars(env_vars):
            yield


def get_logs_config():
    config = []
    for service in [
        {"name": "impalad", "type": "daemon"},
        {"name": "catalogd", "type": "catalog"},
        {"name": "statestored", "type": "statestore"},
    ]:
        for level in ["WARNING", "ERROR", "INFO", "FATAL"]:
            config.append(
                {
                    'type': 'file',
                    'path': f'/var/log/{service["name"]}/{service["name"]}.{level}',
                    'source': 'impala',
                    'service': service["name"],
                    'tags': [f'service_type:{service["type"]}'],
                    'log_processing_rules': [
                        {
                            'type': 'multi_line',
                            'pattern': '^[IWEF]\\d{4} (\\d{2}:){2}\\d{2}',
                            'name': 'new_log_start_with_log_level_and_date',
                        }
                    ],
                },
            )

    return config
