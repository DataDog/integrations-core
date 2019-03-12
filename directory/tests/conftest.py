# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.directory import DirectoryCheck

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(common.HERE, "compose", "docker-compose.yml")
    with docker_run(
        compose_file=compose_file,
    ):
        yield common.get_config_stubs(".")[0]


@pytest.fixture
def check():
    return DirectoryCheck(common.CHECK_NAME)
