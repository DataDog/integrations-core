# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here, run_command, TempDir
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.utils import load_jmx_config

E2E_METADATA = {
    'use_jmx': True,
}


@pytest.fixture(scope="session")
def dd_environment():
    with TempDir('log') as log_dir:
        with docker_run(
            os.path.join(get_here(), 'compose', 'docker-compose.yml'),
            env_vars={'LOG_DIR': log_dir},
            conditions=[WaitFor(setup_ignite)],
            log_patterns="Ignite node started OK",
        ):
            instance = load_jmx_config()
            instance['instances'][0]['port'] = 49112
            instance['instances'][0]['host'] = get_docker_hostname()
            metadata = E2E_METADATA.copy()
            metadata['docker_volumes'] = ['{}:/var/log/ignite'.format(log_dir)]
            yield instance, metadata


def setup_ignite():
    result = run_command("docker exec dd-ignite /opt/ignite/apache-ignite/bin/control.sh --activate", capture=True)
    if result.stderr:
        raise Exception(result.stderr)
