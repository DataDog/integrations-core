# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy
from json import loads
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.mapreduce import MapReduceCheck

from .common import (
    CLUSTER_INFO_URL,
    HERE,
    HOST,
    INSTANCE_INTEGRATION,
    MOCKED_E2E_HOSTS,
    MR_JOB_COUNTERS_URL,
    MR_JOBS_URL,
    MR_TASKS_URL,
    YARN_APPS_URL_BASE,
    setup_mapreduce,
)


@pytest.fixture(scope="session")
def dd_environment():
    env = {'HOSTNAME': HOST}
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        conditions=[WaitFor(setup_mapreduce, attempts=5, wait=5)],
        env_vars=env,
    ):
        # 'custom_hosts' in metadata provides native /etc/hosts mappings in the agent's docker container
        yield INSTANCE_INTEGRATION, {'custom_hosts': get_custom_hosts()}


@pytest.fixture
def check():
    return lambda instance: MapReduceCheck('mapreduce', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request(fake_http_response):
    fixtures = {
        f'{YARN_APPS_URL_BASE}?states=RUNNING&applicationTypes=MAPREDUCE': 'apps_metrics',
        MR_JOBS_URL: 'job_metrics',
        MR_JOB_COUNTERS_URL: 'job_counter_metrics',
        MR_TASKS_URL: 'task_metrics',
        CLUSTER_INFO_URL: 'cluster_info',
    }
    for url, fixture_name in fixtures.items():
        payload = loads((Path(HERE) / 'fixtures' / fixture_name).read_text())
        fake_http_response(url, json_data=payload)


def get_custom_hosts():
    return [(host, '127.0.0.1') for host in MOCKED_E2E_HOSTS]
