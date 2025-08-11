# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
from copy import deepcopy

import psycopg
import pytest
from packaging import version

from datadog_checks.dev import WaitFor, docker_run

from . import common

HERE = os.path.dirname(os.path.abspath(__file__))

E2E_METADATA = {
    'start_commands': [
        'apt update',
        'apt install -y --no-install-recommends build-essential python3-dev libpq-dev',
    ],
}


def container_up(service_name, port):
    """
    Try to connect to postgres/pgbouncer
    """
    psycopg.connect(
        host=common.HOST, port=port, user=common.USER, password=common.PASS, dbname=common.DB, connect_timeout=2
    )


def select_docker_compose_file(env_version):
    """
    Select the appropriate docker compose file based on the tested version of pgbouncer
    """
    if env_version < version.parse('1.10'):
        return 'docker-compose-v1.yml'
    if env_version < version.parse('1.23'):
        return 'docker-compose-v2.yml'
    # Version 1.23 and above
    return 'docker-compose-v3.yml'


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start postgres and install pgbouncer.
    If there's any problem executing `docker compose`, let the exception bubble up.
    """
    compose_file = select_docker_compose_file(common.get_version_from_env())

    with docker_run(
        compose_file=os.path.join(HERE, 'compose', compose_file),
        env_vars={'TEST_RESOURCES_PATH': os.path.join(HERE, 'resources')},
        conditions=[
            WaitFor(container_up, args=("Postgres", 5432)),
            WaitFor(container_up, args=("PgBouncer", common.PORT)),
        ],
    ):
        yield common.DEFAULT_INSTANCE, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(common.DEFAULT_INSTANCE)


@pytest.fixture
def instance_with_url():
    return deepcopy(common.INSTANCE_URL)
