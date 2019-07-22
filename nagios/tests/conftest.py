# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from copy import deepcopy

from datadog_checks.dev import docker_run
from datadog_checks.nagios import NagiosCheck
import os

from .common import (
    HERE,
    INSTANCE_INTEGRATION
)

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session")
def dd_environment():
    nagios_var = os.path.join(HERE, 'compose', 'nagios4', 'var')
    nagios_conf = os.path.join(HERE, 'compose', 'nagios4', 'nagios.cfg')
    e2e_metadata = {'docker_volumes': [
        '{}:/opt/nagios/etc/nagios.cfg'.format(nagios_conf),
        '{}:/opt/nagios/var/'.format(nagios_var)
    ]}

    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        env_vars={
            'NAGIOS_CONFIG_FILE': nagios_conf,
            'NAGIOS_LOGS_PATH': nagios_var
        }
    ):
        yield INSTANCE_INTEGRATION, e2e_metadata


@pytest.fixture
def check():
    return NagiosCheck('nagios', {}, {}, instances=[INSTANCE_INTEGRATION])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)
