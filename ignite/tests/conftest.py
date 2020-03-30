# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here, run_command
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.utils import load_jmx_config

E2E_METADATA = {
    'use_jmx': True,
}


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        os.path.join(get_here(), 'compose', 'docker-compose.yml'),
        conditions=[WaitFor(setup_ignite)],
        log_patterns="Ignite node started OK",
    ):
        instance = load_jmx_config()
        instance['instances'][0]['port'] = 49112
        instance['instances'][0]['host'] = get_docker_hostname()
        yield instance, E2E_METADATA


def setup_ignite():
    result = run_command("docker exec dd-ignite /opt/ignite/apache-ignite/bin/control.sh --activate", capture=True)
    if result.stderr:
        raise Exception(result.stderr)
