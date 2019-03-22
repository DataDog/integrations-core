# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import pytest

from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.ssh_check import CheckSSH


@pytest.fixture(scope="session")
def dd_environment(instance):
    env = {
        "ROOT_PASSWORD": instance.get("password", "1234"),
    }

    with docker_run(
        compose_file=os.path.join(get_here(), "compose", "docker-compose.yml"),
        env_vars=env,
        conditions=[CheckDockerLogs("dd-test-sshd", "Server listening on 0.0.0.0 port 22.")]
    ):
        yield instance


@pytest.fixture
def check():
    return CheckSSH("ssh_check", {}, {})


@pytest.fixture(scope="session")
def instance():
    return {
        "host": "127.0.0.1",
        "port": 8022,
        "password": "secured_password",
        "username": "root",
        "add_missing_keys": True,
    }
