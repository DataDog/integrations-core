# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.fs import create_file

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    nagios_conf = os.path.join(common.HERE, 'compose', 'nagios4', 'nagios.cfg')
    with TempDir("nagios_var_log") as nagios_var_log:
        e2e_metadata = {
            'docker_volumes': [
                '{}:/opt/nagios/etc/nagios.cfg'.format(nagios_conf),
                '{}:/opt/nagios/var/log/'.format(nagios_var_log),
            ]
        }
        for perfdata_file in (
            os.path.join(nagios_var_log, common.HOST_PERFDATA_FILE),
            os.path.join(nagios_var_log, common.SERVICE_PERFDATA_FILE),
        ):
            if not os.path.isfile(perfdata_file):
                create_file(perfdata_file)

        with docker_run(
            os.path.join(common.HERE, 'compose', 'docker-compose.yaml'),
            env_vars={'NAGIOS_LOGS_PATH': nagios_var_log, 'NAGIOS_VERSION': common.NAGIOS_VERSION},
            build=True,
            mount_logs=True,
        ):
            yield common.INSTANCE_INTEGRATION, e2e_metadata


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE_INTEGRATION)
