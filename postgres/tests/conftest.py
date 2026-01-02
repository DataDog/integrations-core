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
def dd_environment(e2e_instance, skip_env):
    """
    Start a standalone postgres server requiring authentication.
    """
    if skip_env:
        yield e2e_instance, E2E_METADATA
        return

    compose_file = 'docker-compose.yaml'
    if float(POSTGRES_VERSION) >= 10.0:
        compose_file = 'docker-compose-replication.yaml'
    with docker_run(
        os.path.join(HERE, 'compose', compose_file),
        conditions=[WaitFor(connect_to_pg)],
        env_vars={
            "POSTGRES_IMAGE": POSTGRES_IMAGE,
            "POSTGRES_LOCALE": POSTGRES_LOCALE,
            "PGDATA": "/var/lib/postgresql/$PG_MAJOR/docker",
        },
        capture=True,
    ):
        yield e2e_instance, E2E_METADATA


# Skip environment setup
# This is helpful for running tests locally without having to spin up the environment repeatedly
# To use this, launch the necessary docker compose files manually and then run the tests with --skip-env
def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--skip-env",
        action="store_true",
        default=False,
        help="skip environment setup",
    )


@pytest.fixture(scope='session')
def skip_env(request):
    return request.config.getoption("--skip-env")


@pytest.fixture
def check():
    c = PostgreSql('postgres', {}, [{'dbname': 'dbname', 'host': 'localhost', 'port': '5432', 'username': USER}])
    c._version = VersionInfo(9, 2, 0)
    return c


@pytest.fixture(scope="function")
def integration_check() -> Callable[[dict, Optional[dict]], PostgreSql]:
    checks = []

    def _check(instance: dict, init_config: dict = None):
        nonlocal checks
        c = PostgreSql('postgres', init_config or {}, [instance])
        checks.append(c)
        return c

    yield _check

    for c in checks:
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
def metrics_cache(pg_instance, integration_check):
    check = integration_check(pg_instance)
    check.warning = print
    config, _ = build_config(check)
    return PostgresMetricsCache(config)


@pytest.fixture
def metrics_cache_replica(pg_replica_instance, integration_check):
    check = integration_check(pg_replica_instance)
    check.warning = print
    config, _ = build_config(check)
    return PostgresMetricsCache(config)


@pytest.fixture(scope='session')
def e2e_instance():
    instance = copy.deepcopy(INSTANCE)
    instance['dbm'] = True
    return instance


@pytest.fixture(scope='function', autouse=False)
def reset_pg_stat_statements(pg_instance):
    """
    Resets pg_stat_statements before each test to ensure clean state.
    This prevents test isolation issues when incremental_query_metrics is enabled.

    Usage: Add this fixture as a parameter to any test that needs a clean pg_stat_statements state.
    """
    from .utils import _get_superconn

    try:
        with _get_superconn(pg_instance) as superconn:
            with superconn.cursor() as cur:
                cur.execute("SELECT pg_stat_statements_reset();")
    except Exception:
        # If pg_stat_statements is not available or we can't reset, that's okay
        # Some tests might run on versions without pg_stat_statements
        pass

    yield
