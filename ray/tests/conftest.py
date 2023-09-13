# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import time
from contextlib import contextmanager
from urllib.parse import urljoin

import pytest
import requests

from datadog_checks.dev import EnvVars, TempDir, docker_run
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.ray import RayCheck

from .common import (
    E2E_METADATA,
    HEAD_DASHBOARD_PORT,
    HEAD_INSTANCE,
    HEAD_METRICS_PORT,
    HEAD_OPENMETRICS_ENDPOINT,
    HERE,
    MOCKED_HEAD_INSTANCE,
    MOCKED_WORKER_INSTANCE,
    RAY_VERSION,
    SERVE_PORT,
    SERVE_URL,
    WORKER1_INSTANCE,
    WORKER1_METRICS_PORT,
    WORKER1_OPENMETRICS_ENDPOINT,
    WORKER2_INSTANCE,
    WORKER2_METRICS_PORT,
    WORKER2_OPENMETRICS_ENDPOINT,
    WORKER3_INSTANCE,
    WORKER3_METRICS_PORT,
    WORKER3_OPENMETRICS_ENDPOINT,
)


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        compose_file=os.path.join(
            HERE,
            "docker",
            "docker-compose.yaml",
        ),
        env_vars={
            "RAY_VERSION": RAY_VERSION,
            "HEAD_METRICS_PORT": HEAD_METRICS_PORT,
            "HEAD_DASHBOARD_PORT": HEAD_DASHBOARD_PORT,
            "WORKER1_METRICS_PORT": WORKER1_METRICS_PORT,
            "WORKER2_METRICS_PORT": WORKER2_METRICS_PORT,
            "WORKER3_METRICS_PORT": WORKER3_METRICS_PORT,
            "SERVE_PORT": SERVE_PORT,
        },
        conditions=[
            CheckEndpoints(HEAD_OPENMETRICS_ENDPOINT),
            CheckEndpoints(WORKER1_OPENMETRICS_ENDPOINT),
            CheckEndpoints(WORKER2_OPENMETRICS_ENDPOINT),
            CheckEndpoints(WORKER3_OPENMETRICS_ENDPOINT),
            CheckEndpoints(urljoin(SERVE_URL, "hello")),
            WaitFor(run_add),
            WaitFor(prepare_service),
        ],
        wrappers=[create_log_volumes()],
    ):
        yield {
            "init_config": {},
            "instances": [
                HEAD_INSTANCE,
                WORKER1_INSTANCE,
                WORKER2_INSTANCE,
                WORKER3_INSTANCE,
            ],
        }, E2E_METADATA


@pytest.fixture
def check():
    return lambda instance: RayCheck('ray', {}, [instance])


@pytest.fixture
def head_instance():
    return copy.deepcopy(HEAD_INSTANCE)


@pytest.fixture
def worker_instance():
    return copy.deepcopy(WORKER1_INSTANCE)


@pytest.fixture
def mocked_head_instance():
    return copy.deepcopy(MOCKED_HEAD_INSTANCE)


@pytest.fixture
def mocked_worker_instance():
    return copy.deepcopy(MOCKED_WORKER_INSTANCE)


def run_add():
    try:
        response = requests.post(
            urljoin(SERVE_URL, "add"),
            data='{"a": 1, "b": 2}',
            headers={'Content-Type': 'application/json'},
        )
        response.raise_for_status()
    except Exception:
        return False
    else:
        return response.status_code == 200


def prepare_service():
    # Exercise the service a bit to generate metrics
    for _ in range(10):
        run_add()
        time.sleep(1)

    return True


@contextmanager
def create_log_volumes():
    env_vars = {}
    docker_volumes = get_state("docker_volumes", [])

    with TempDir("ray", mode=0o777) as d:
        docker_volumes.append(f"{d}:/tmp/ray")
        env_vars["RAY_LOG_FOLDER"] = d

        config = [
            {
                "type": "file",
                "path": "/tmp/ray/ray.log",
                "source": "ray",
                "service": "ddev-ray",
                "log_processing_rules": [
                    {
                        "type": "multi_line",
                        "name": "new_log_start",
                        "pattern": "^(\\[)?\\d{4}-\\d{2}-\\d{2}",
                    }
                ],
            }
        ]

        save_state("logs_config", config)
        save_state("docker_volumes", docker_volumes)

        with EnvVars(env_vars):
            yield
