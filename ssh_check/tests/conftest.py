# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run, get_here

from . import common

PWD_ENV = {
    "ROOT_PASSWORD": common.INSTANCE_INTEGRATION.get("password", "1234"),
    "SSH_SERVER_IMAGE": common.SSH_SERVER_IMAGE,
    "ROOT_KEYPAIR_LOGIN_ENABLED": "false",
}


KEYPAIR_ENV = {
    "ROOT_PASSWORD": common.INSTANCE_INTEGRATION.get("password", "1234"),
    "SSH_SERVER_IMAGE": common.SSH_SERVER_IMAGE,
    "ROOT_KEYPAIR_LOGIN_ENABLED": "true",
}


LOG_PATTERN = "Server listening on 0.0.0.0 port 22."
PRIVATE_KEY_FILE = os.path.join(get_here(), 'private_key')


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(get_here(), "compose", "docker-compose.yml"),
        env_vars=PWD_ENV,
        log_patterns=LOG_PATTERN,
    ):
        yield common.INSTANCE_INTEGRATION


@pytest.fixture(scope="session")
def dd_environment_keypair():
    with docker_run(
        compose_file=os.path.join(get_here(), "compose", "docker-compose-keypair.yml"),
        env_vars=KEYPAIR_ENV,
        log_patterns=LOG_PATTERN,
    ):
        instance = deepcopy(common.INSTANCE_INTEGRATION)
        instance['private_key_file'] = PRIVATE_KEY_FILE
        instance['password'] = 'testpassprase'
        yield instance


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE_INTEGRATION)
