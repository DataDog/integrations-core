# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY3

from datadog_checks.dev import WaitFor, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.teamcity import TeamCityCheck

if PY3:
    from datadog_checks.teamcity.check import TeamCityCheckV2

from .common import COMPOSE_FILE, INSTANCE, LEGACY_INSTANCE, OPENMETRICS_INSTANCE, USE_OPENMETRICS


def restore_teamcity_server():
    cmd = [
        'docker',
        'exec',
        'teamcity-server',
        '/opt/teamcity/bin/maintainDB.sh',
        'restore',
        '-A',
        '/data/teamcity_server/datadir',
        '-I',
        '-F',
        '/teamcity_backup.zip',
    ]
    run_command(cmd)


def restart_teamcity_server():
    cmd = ['docker', 'exec', 'teamcity-server', '/opt/teamcity/bin/teamcity-server.sh', 'restart']

    run_command(cmd)


@pytest.fixture(scope='session')
def dd_environment(instance, openmetrics_instance):
    conditions = [
        WaitFor(restore_teamcity_server),
        WaitFor(restart_teamcity_server),
        CheckDockerLogs('teamcity-server', ['TeamCity initialized'], attempts=100, wait=5),
    ]
    with docker_run(COMPOSE_FILE, conditions=conditions, sleep=10, mount_logs=True):
        if USE_OPENMETRICS:
            yield openmetrics_instance
        else:
            yield instance


@pytest.fixture(scope='session')
def legacy_instance():
    return LEGACY_INSTANCE


@pytest.fixture(scope='session')
def instance():
    return INSTANCE


@pytest.fixture(scope='session')
def openmetrics_instance():
    return OPENMETRICS_INSTANCE


@pytest.fixture(scope="session")
def check():
    return lambda instance: TeamCityCheck('teamcity', {}, [instance])


@pytest.fixture(scope="session")
def check_v2():
    return lambda instance: TeamCityCheckV2('teamcity', {}, [instance])
