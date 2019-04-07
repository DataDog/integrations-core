# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import xmlrpclib
from copy import deepcopy

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
    with docker_run(compose_file=os.path.join(HERE, 'compose', 'supervisord.yaml'), endpoints=URL):
        server = xmlrpclib.Server('http://localhost:19001/RPC2')
        server.supervisor.startAllProcesses()
        yield SUPERVISORD_CONFIG
