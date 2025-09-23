# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.fs import create_file, path_exists
from datadog_checks.openldap import OpenLDAP

from .common import DEFAULT_INSTANCE, HERE, HOST


@pytest.fixture(scope='session')
def dd_environment():
    with TempDir() as d:
        host_socket_path = os.path.join(d, 'ldapi')

        if not path_exists(host_socket_path):
            os.chmod(d, 0o777)
            create_file(host_socket_path)
            os.chmod(host_socket_path, 0o640)

        with docker_run(
            compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
            env_vars={'HOST_SOCKET_DIR': d, 'OPENLDAP_CERTS_DIR': os.path.join(HERE, 'compose', 'certs')},
            log_patterns='slapd starting',
        ):
            yield DEFAULT_INSTANCE


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
    instance['url'] = 'ldaps://{}:1636'.format(HOST)
    return instance
