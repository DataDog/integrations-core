# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from contextlib import contextmanager

import pytest

from datadog_checks.dev import EnvVars, TempDir
from datadog_checks.dev.docker import docker_run
from datadog_checks.dev.env import get_state, save_state
from datadog_checks.dev.utils import load_jmx_config

from .common import E2E_METADATA, FLAVOR, HELLO_URL, HERE


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', FLAVOR, 'docker-compose.yml')

    log_patterns = ['Server startup'] if FLAVOR == 'standalone' else ['Starting ProtocolHandler']

    with docker_run(
        compose_file,
        build=True,
        endpoints=HELLO_URL,
        log_patterns=log_patterns,
        wrappers=[create_log_volumes()],
    ):
        yield load_jmx_config(), E2E_METADATA


@pytest.fixture
def instance():
    return {}


@contextmanager
def create_log_volumes():
    env_vars = {}
    docker_volumes = get_state("docker_volumes", [])

    with TempDir("tomcat") as d:
        os.chmod(d, 0o777)
        docker_volumes.append(f"{d}:/var/log/tomcat")
        env_vars["TOMCAT_LOG_FOLDER"] = d

        config = [
            {
                "type": "file",
                "path": "/var/log/tomcat/*",
                "source": "tomcat",
                "service": "tomcat",
            },
        ]

        save_state("logs_config", config)
        save_state("docker_volumes", docker_volumes)

        with EnvVars(env_vars):
            yield
