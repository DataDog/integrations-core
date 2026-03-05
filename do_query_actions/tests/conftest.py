# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import psycopg
import pytest

from datadog_checks.dev import WaitFor, docker_run

from . import common

HERE = os.path.dirname(os.path.abspath(__file__))

E2E_METADATA = {
    'start_commands': [
        'apt update',
        'apt install -y --no-install-recommends build-essential python3-dev libpq-dev',
    ],
}


def connect_to_pg():
    psycopg.connect(
        host='localhost',
        dbname=common.POSTGRES_INSTANCE['dbname'],
        user=common.POSTGRES_INSTANCE['username'],
        port=common.POSTGRES_INSTANCE['port'],
        password=common.POSTGRES_INSTANCE['password'],
    )


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'),
        conditions=[WaitFor(connect_to_pg)],
    ):
        yield deepcopy(common.POSTGRES_INSTANCE), E2E_METADATA


@pytest.fixture
def postgres_instance():
    return deepcopy(common.POSTGRES_INSTANCE)


@pytest.fixture
def multi_query_instance():
    return deepcopy(common.MULTI_QUERY_INSTANCE)
