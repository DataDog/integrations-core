# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import LazyFunction, docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.ibm_was import IbmWasCheck

from . import common


class StartPerfServlet(LazyFunction):
    def __call__(self, *args, **kwargs):
        run_command(
            'docker exec ibm_was /opt/IBM/WebSphere/AppServer/profiles/AppSrv01/bin/wsadmin.sh '
            '-lang jython -user wsadmin -password IbmWasPassword1 -f /home/scripts/init.jython'
        )


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')

    with docker_run(
        compose_file,
        conditions=[
            CheckDockerLogs(compose_file, 'The SSL configuration alias is NodeDefaultSSLSettings', attempts=80, wait=3),
            StartPerfServlet(),
            CheckEndpoints(common.INSTANCE['servlet_url']),
        ],
        attempts=2,
    ):
        yield common.INSTANCE


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.fixture()
def check():
    return lambda instance: IbmWasCheck('ibm_was', {}, [instance or common.INSTANCE])
