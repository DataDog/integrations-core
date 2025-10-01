# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
from collections.abc import Callable
from typing import Optional

import psycopg
import pytest
from semver import VersionInfo

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.config import build_config
from datadog_checks.postgres.metrics_cache import PostgresMetricsCache

from .common import (
    DB_NAME,
    HOST,
    PASSWORD,
    PORT,
    PORT_REPLICA,
    PORT_REPLICA2,
    PORT_REPLICA_LOGICAL,
    POSTGRES_IMAGE,
    POSTGRES_LOCALE,
    POSTGRES_VERSION,
    USER,
)

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = {
    'host': HOST,
    'port': PORT,
    'username': USER,
    'password': PASSWORD,
    'dbname': DB_NAME,
    'tags': ['foo:bar'],
    'disable_generic_tags': True,
    'collect_settings': {'enabled': True, 'run_sync': True},
}


E2E_METADATA = {
    'start_commands': [
        'apt update',
        'apt install -y --no-install-recommends build-essential python3-dev libpq-dev',
    ],
}


def connect_to_pg():
    psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD)
    if float(POSTGRES_VERSION) >= 10.0:
        psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, port=PORT_REPLICA, password=PASSWORD)
        psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, port=PORT_REPLICA2, password=PASSWORD)
        psycopg.connect(host=HOST, dbname=DB_NAME, user=USER, port=PORT_REPLICA_LOGICAL, password=PASSWORD)


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    """
    Start a standalone postgres server requiring authentication.
    """
    compose_file = 'docker-compose.yaml'
    if float(POSTGRES_VERSION) >= 10.0:
        compose_file = 'docker-compose-replication.yaml'
    with docker_run(
        os.path.join(HERE, 'compose', compose_file),
        conditions=[WaitFor(connect_to_pg)],
        env_vars={"POSTGRES_IMAGE": POSTGRES_IMAGE, "POSTGRES_LOCALE": POSTGRES_LOCALE},
        capture=True,
    ):
        yield e2e_instance, E2E_METADATA



@pytest.fixture(scope="function")
def integration_check() -> Callable[[dict, Optional[dict]], PostgreSql]:
    c = None

    def _check(instance: dict, init_config: dict = None):
        nonlocal c
        c = PostgreSql('postgres', init_config or {}, [instance])
        return c

    yield _check

    if c:        
        c.cancel()


@pytest.fixture
def pg_instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def pg_replica_instance():
    instance = copy.deepcopy(INSTANCE)
    instance['port'] = PORT_REPLICA
    return instance


@pytest.fixture
def pg_replica_instance2():
    instance = copy.deepcopy(INSTANCE)
    instance['port'] = PORT_REPLICA2
    return instance


@pytest.fixture
def pg_replica_logical():
    instance = copy.deepcopy(INSTANCE)
    instance['port'] = PORT_REPLICA_LOGICAL
    return instance


@pytest.fixture
def metrics_cache(pg_instance):
    check = PostgreSql('postgres', {}, [pg_instance])
    check.warning = print
    config, _ = build_config(check)
    return PostgresMetricsCache(config)


@pytest.fixture
def metrics_cache_replica(pg_replica_instance):
    check = PostgreSql('postgres', {}, [pg_replica_instance])
    check.warning = print
    config, _ = build_config(check)
    return PostgresMetricsCache(config)


@pytest.fixture(scope='session')
def e2e_instance():
    instance = copy.deepcopy(INSTANCE)
    instance['dbm'] = True
    return instance
