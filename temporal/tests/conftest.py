# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

from datadog_checks.dev import EnvVars, TempDir, docker_run, get_docker_hostname, get_here, run_command
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.temporal import TemporalCheck

INSTANCE = {
    "openmetrics_endpoint": f"http://{get_docker_hostname()}:8000/metrics",
}

INTEGRATIONS_CORE_ROOT = Path(__file__).resolve().parents[2]
TEMPORAL_AUTOCONF = Path(__file__).parent.parent / "datadog_checks" / "temporal" / "data" / "auto_conf_discovery.yaml"
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


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), "compose", "docker-compose.yaml")

    with docker_run(
        compose_file=compose_file,
        conditions=(
            CheckEndpoints(f"http://{get_docker_hostname()}:8000/metrics"),
            CheckEndpoints(f"http://{get_docker_hostname()}:8001/metrics"),
        ),
        wrappers=[create_log_volumes()],
    ):
        # Run the workflow a couple of times.
        for param in ("World", "Datadog", "Agent Integrations"):
            run_command(
                "docker exec temporal-admin-tools tctl workflow start "
                "   --taskqueue python-task-queue "
                "   --workflow_type SayHello "
                f"  --input '\"{param}\"'"
            )

        time.sleep(2)

        yield copy.deepcopy(INSTANCE)


@contextmanager
def create_log_volumes():
    env_vars = {}
    docker_volumes = get_state("docker_volumes", [])

    with TempDir("temporal") as d:
        os.chmod(d, 0o777)
        docker_volumes.append(f"{d}:/var/log/temporal")
        env_vars["TEMPORAL_LOG_FOLDER"] = d

        config = [
            {
                "type": "file",
                "path": "/var/log/temporal/temporal-server.log",
                "source": "temporal",
                "service": "temporal",
            },
        ]

        docker_volumes.extend(
            [
                f"{TEMPORAL_AUTOCONF}:/etc/datadog-agent/conf.d/temporal.d/auto_conf_discovery.yaml:ro",
                f"{DISCOVERY_HELPERS_DIR}:{SITE_PACKAGES}/datadog_checks/base/utils/discovery:ro",
                f"{OPENMETRICS_V2_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/openmetrics/v2/base.py:ro",
                f"{AGENTCHECK_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/base.py:ro",
                "/var/run/docker.sock:/var/run/docker.sock:ro",
            ]
        )

        save_state("logs_config", config)
        save_state("docker_volumes", docker_volumes)

        with EnvVars(env_vars):
            yield


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def check(instance):
    return TemporalCheck('temporal.server', {}, [instance])


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.Session.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
