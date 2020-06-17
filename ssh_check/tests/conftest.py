# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run, get_here, run_command
from datadog_checks.ssh_check import CheckSSH

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    env = {
        "ROOT_PASSWORD": common.INSTANCE_INTEGRATION["password"],
        "SSH_SERVER_IMAGE": common.SSH_SERVER_IMAGE,
    }

    with docker_run(
        compose_file=os.path.join(get_here(), "compose", "docker-compose.yml"),
        env_vars=env,
        log_patterns="Server listening on 0.0.0.0 port 22.",
    ):
        try:
            yield common.INSTANCE_INTEGRATION
        finally:
            # Remove any key added when check connected to the sshd server during tests.
            # This prevents 'host key for server xyz does not match' errors across test runs,
            # since keys are generated at random by the sshd server upon first connection.
            run_command(["ssh-keygen", "-R", common.INTEGRATION_ADDED_KEY_HOST])


@pytest.fixture
def check():
    return CheckSSH("ssh_check", {}, {})


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE_INTEGRATION)
