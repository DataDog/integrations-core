# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here, run_command
from datadog_checks.dev.utils import load_jmx_config

E2E_METADATA = {
    'use_jmx': True,
}


@pytest.fixture(scope="session")
def dd_environment():
    env = {
        'CONFIG_FILE': os.path.join(get_here(), 'compose', 'config.xml'),
        'FUNCTIONS_FILE': os.path.join(get_here(), 'compose', 'functions.sh'),
    }
    with docker_run(
        os.path.join(get_here(), 'compose', 'docker-compose.yml'), env_vars=env, log_patterns="Ignite node started OK"
    ):
        result = run_command("docker exec dd-ignite /opt/ignite/apache-ignite/bin/control.sh --activate", capture=True)
        if result.stderr:
            raise Exception(result.stderr)
        instance = load_jmx_config()
        instance['instances'][0]['port'] = 49112
        instance['instances'][0]['host'] = get_docker_hostname()
        yield instance, E2E_METADATA
