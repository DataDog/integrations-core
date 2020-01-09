# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.squid import SquidCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(compose_file=os.path.join(common.HERE, 'compose', 'squid.yaml'), endpoints=[common.URL]):
        yield common.CHECK_CONFIG


@pytest.fixture
def check():
    return SquidCheck(common.CHECK_NAME, {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(common.CHECK_CONFIG)
    return instance
