# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.tcp_check import TCPCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(os.path.join(common.HERE, 'compose', 'docker-compose.yml')):
        yield common.INSTANCE


@pytest.fixture
def check():
    return TCPCheck(common.CHECK_NAME, {}, [common.INSTANCE])


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)
