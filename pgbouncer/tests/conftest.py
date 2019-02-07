# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
from copy import deepcopy

import pytest
import psycopg2

from datadog_checks.dev import docker_run, WaitFor

from . import common

HERE = os.path.dirname(os.path.abspath(__file__))


def container_up(service_name, port):
    """
    Try to connect to postgres/pgbouncer
    """
    psycopg2.connect(
        host=common.HOST, port=port, user=common.USER, password=common.PASS,
        database=common.DB, connect_timeout=2,
    )


@pytest.fixture(scope="session", autouse=True)
def dd_environment():
    """
    Start postgres and install pgbouncer. If there's any problem executing
    docker-compose, let the exception bubble up.
    """

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yml'),
        env_vars={'TEST_RESOURCES_PATH': os.path.join(HERE, 'resources')},
        conditions=[
            WaitFor(container_up, args=("Postgres", 5432)),
            WaitFor(container_up, args=("PgBouncer", common.PORT)),
        ]
    ):

        yield common.DEFAULT_INSTANCE


@pytest.fixture
def instance():
    return deepcopy(common.DEFAULT_INSTANCE)


@pytest.fixture
def instance_with_url():
    return deepcopy(common.INSTANCE_URL)
