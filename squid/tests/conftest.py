# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import pytest

from copy import deepcopy

from datadog_checks.dev import docker_run
from datadog_checks.squid import SquidCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'squid.yaml'),
        endpoints=[common.URL],
    ):
        yield common.CHECK_CONFIG


@pytest.fixture
def check():
    return SquidCheck(common.CHECK_NAME, {}, {})


@pytest.fixture
def instance():
    instance = deepcopy(common.CHECK_CONFIG)
    return instance
