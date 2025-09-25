# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
from collections.abc import Callable
from typing import Optional
from enum import Enum

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


@pytest.fixture
def check():
    c = PostgreSql('postgres', {}, [{'dbname': 'dbname', 'host': 'localhost', 'port': '5432', 'username': USER}])
    c._version = VersionInfo(9, 2, 0)
    return c


@pytest.fixture
def integration_check() -> Callable[[dict, Optional[dict]], PostgreSql]:
    def _check(instance: dict, init_config: dict = None):
        c = PostgreSql('postgres', init_config or {}, [instance])
        return c

    return _check


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
    config = build_config(check={'warning': print}, init_config={}, instance=pg_instance)
    return PostgresMetricsCache(config)


@pytest.fixture
def metrics_cache_replica(pg_replica_instance):
    config, _ = build_config(instance=pg_replica_instance, init_config={}, check={'warning': print})
    return PostgresMetricsCache(config)


@pytest.fixture(scope='session')
def e2e_instance():
    instance = copy.deepcopy(INSTANCE)
    instance['dbm'] = True
    return instance


class SnapshotMode(Enum):
    RECORD = "record"
    REPLAY = "replay"


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--snapshot-mode",
        action="store",
        default="replay",
        help="set snapshot mode",
        choices=(SnapshotMode.RECORD.value, SnapshotMode.REPLAY.value),
    )


@pytest.fixture
def snapshot_mode(request):
    return SnapshotMode(request.config.getoption("--snapshot-mode"))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    for item in items:
        # We only want to load the dd_environment fixture for snapshot tests if we are recording
        # If we are replaying we don't need the database and we can run much faster without it
        if "snapshot" in item.keywords and config.getoption("--snapshot-mode") == SnapshotMode.RECORD.value:
            item.fixturenames.append('dd_environment')
