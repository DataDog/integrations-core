# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest
from datadog_checks.openldap import OpenLDAP

from datadog_checks.dev import TempDir, docker_run
from .common import DEFAULT_INSTANCE, HERE, HOST


@pytest.fixture(scope='session')
def dd_environment():

    with TempDir() as d:
        systemd_run = os.path.join(d, 'systemd_run')
        run_dbus = os.path.join(d, 'run_dbus')

        E2E_METADATA = {
            'docker_volumes': [
                '{}:/run'.format(systemd_run),
                '{}:/var/run/dbus'.format(run_dbus),
            ],
        }

        with docker_run(
            compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
            env_vars={'HOST_SOCKET_DIR': d},
        ):
            yield DEFAULT_INSTANCE, E2E_METADATA


@pytest.fixture
def check():
    return OpenLDAP('openldap', {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(DEFAULT_INSTANCE)
    return instance


@pytest.fixture
def instance_ssl():
    instance = deepcopy(DEFAULT_INSTANCE)
    instance['url'] = 'ldaps://{}:6360'.format(HOST)
    return instance
