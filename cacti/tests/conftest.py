# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pymysql
import pytest

from datadog_checks.cacti import CactiCheck
from datadog_checks.dev import TempDir, WaitFor, docker_run, run_command

from . import common
from .common import CONTAINER_NAME, E2E_METADATA, HERE, INSTANCE_INTEGRATION, MYSQL_PASSWORD, MYSQL_USERNAME, RRD_PATH

SQL_SETUP = '''
DROP USER IF EXISTS '{user}'@'localhost';
DROP USER IF EXISTS '{user}'@'%';

CREATE USER '{user}'@'localhost' IDENTIFIED BY '{password}';
GRANT ALL PRIVILEGES ON *.* TO '{user}'@'localhost' WITH GRANT OPTION;
CREATE USER '{user}'@'%' IDENTIFIED BY '{password}';
GRANT ALL PRIVILEGES ON *.* TO '{user}'@'%' WITH GRANT OPTION;

FLUSH PRIVILEGES;
'''.format(
    user=MYSQL_USERNAME, password=MYSQL_PASSWORD
)


def setup_db():
    run_docker_command(['mysql', '-u', 'root', '-e', SQL_SETUP])
    run_docker_command(['/sbin/restore'])


def check_data_available():
    conn = pymysql.connect(
        host=common.HOST,
        user=common.MYSQL_USERNAME,
        passwd=common.MYSQL_PASSWORD,
        db=common.DATABASE,
        port=common.MYSQL_PORT,
    )
    c = conn.cursor()

    c.execute('select count(*) from data_local')
    data_local_count = c.fetchone()[0]

    if data_local_count == 0:
        raise Exception("Exception data_local to be populated but found 0 entries.")


def poll_cacti():
    run_docker_command(['php', '/opt/cacti/lib/poller.php', '--force'])


def run_docker_command(command):
    run_command(['docker', 'exec', CONTAINER_NAME] + command, capture=True, check=True)


@pytest.fixture(scope="session")
def dd_environment():
    with TempDir("nagios_var_log") as rrd_path:
        e2e_metadata = deepcopy(E2E_METADATA)
        e2e_metadata['docker_volumes'] = ['{}:{}'.format(rrd_path, RRD_PATH)]

        with docker_run(
            conditions=[WaitFor(setup_db), WaitFor(check_data_available), WaitFor(poll_cacti)],
            compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
            env_vars={'RRD_PATH': rrd_path},
            build=True,
            mount_logs=True,
        ):
            yield INSTANCE_INTEGRATION, e2e_metadata


@pytest.fixture
def check():
    return CactiCheck('cacti', {}, [{}])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
