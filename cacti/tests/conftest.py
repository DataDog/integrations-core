# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.cacti import CactiCheck
from datadog_checks.dev import TempDir, WaitFor, docker_run, run_command

from .common import CONTAINER_NAME, E2E_METADATA, HERE, INSTANCE_INTEGRATION, MYSQL_PASSWORD, MYSQL_USERNAME, RRD_PATH

SQL_SETUP = '''
FLUSH PRIVILEGES;
'''.format(
    user=MYSQL_USERNAME, password=MYSQL_PASSWORD
)


def set_up_cacti():
    commands = [
        ['/sbin/restore'],
        ['mysql', '-u', 'root', '-e', SQL_SETUP],
        ['php', '/opt/cacti/lib/poller.php', '--force'],
    ]
    for c in commands:
        command = ['docker', 'exec', CONTAINER_NAME] + c
        run_command(command, capture=True, check=True)


@pytest.fixture(scope="session")
def dd_environment():
    with TempDir("nagios_var_log") as rrd_path:
        e2e_metadata = deepcopy(E2E_METADATA)
        e2e_metadata['docker_volumes'] = ['{}:{}'.format(rrd_path, RRD_PATH)]

        with docker_run(
            conditions=[WaitFor(set_up_cacti)],
            compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
            env_vars={'RRD_PATH': rrd_path},
            build=True,
        ):
            yield INSTANCE_INTEGRATION, e2e_metadata


@pytest.fixture
def check():
    return CactiCheck('cacti', {}, {})


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
