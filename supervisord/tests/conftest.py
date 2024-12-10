# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy
from xmlrpc.client import ServerProxy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.supervisord.supervisord import SupervisordCheck

from .common import BAD_SUPERVISORD_CONFIG, HERE, SUPERVISORD_CONFIG, URL


@pytest.fixture
def check():
    return SupervisordCheck("supervisord", {}, {})


@pytest.fixture
def instance():
    return deepcopy(SUPERVISORD_CONFIG)


@pytest.fixture
def bad_instance():
    return deepcopy(BAD_SUPERVISORD_CONFIG)


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(compose_file=os.path.join(HERE, 'compose', 'supervisord.yaml'), endpoints=URL, mount_logs=True):
        server = ServerProxy('{}/RPC2'.format(URL))
        server.supervisor.startAllProcesses()
        yield SUPERVISORD_CONFIG
