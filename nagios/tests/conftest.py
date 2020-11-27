# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run

from .common import HERE, INSTANCE_INTEGRATION


@pytest.fixture(scope="session")
def dd_environment():
    nagios_conf = os.path.join(HERE, 'compose', 'nagios4', 'nagios.cfg')
    with TempDir("nagios_var_log") as nagios_var_log:
        e2e_metadata = {
            'docker_volumes': [
                '{}:/opt/nagios/etc/nagios.cfg'.format(nagios_conf),
                '{}:/opt/nagios/var/log/'.format(nagios_var_log),
            ]
        }

        configuration = {
            "init_config": {},
            "instances": [INSTANCE_INTEGRATION],
            "logs": {
                "type": "file",
                "path": os.path.join(nagios_var_log, 'nagios.log'),
                "source": "nagios",
            }
        }

        with docker_run(
            os.path.join(HERE, 'compose', 'docker-compose.yaml'),
            env_vars={'NAGIOS_LOGS_PATH': nagios_var_log},
            build=True,
        ):
            yield configuration, e2e_metadata


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
