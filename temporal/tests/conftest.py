# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here, run_command
from datadog_checks.dev.conditions import CheckEndpoints

INSTANCE = {"service": "server"}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), "compose", "docker-compose.yaml")

    with docker_run(
        compose_file=compose_file,
        conditions=(
            CheckEndpoints(f"http://{get_docker_hostname()}:8000/metrics"),
            CheckEndpoints(f"http://{get_docker_hostname()}:8001/metrics"),
        ),
    ):
        # Run the workflow a couple of times.
        for param in ("World", "Datadog", "Agent Integrations"):
            run_command(
                "docker exec temporal-admin-tools tctl workflow start "
                "   --taskqueue python-task-queue "
                "   --workflow_type SayHello "
                f"  --input '\"{param}\"'"
            )

        time.sleep(2)

        yield copy.deepcopy(INSTANCE)


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)
