# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

import os
from typing import Dict, Iterator, List

import pytest
import rethinkdb

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.rethinkdb._types import Instance

from .common import (
    CONNECT_SERVER_PORT,
    DATABASE,
    HERE,
    HEROES_INITIAL_DOCUMENTS,
    HEROES_TABLE,
    HEROES_TABLE_OPTIONS,
    HOST,
    IMAGE,
    NUM_FAMOUS_HEROES,
    PROXY_PORT,
)

E2E_METADATA = {'start_commands': ['pip install rethinkdb==2.4.4']}


@pytest.fixture(scope='session')
def instance():
    # type: () -> Instance
    return {
        'host': HOST,
        'port': CONNECT_SERVER_PORT,
    }


def create_tables():
    # type: () -> None
    with rethinkdb.r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # See: https://rethinkdb.com/api/python/db_create
        response = rethinkdb.r.db_create(DATABASE).run(conn)
        assert response['dbs_created'] == 1

        table = HEROES_TABLE
        options = HEROES_TABLE_OPTIONS

        # See: https://rethinkdb.com/api/python/table_create/
        response = rethinkdb.r.db(DATABASE).table_create(table, **options).run(conn)
        assert response['tables_created'] == 1


def simulate_client_writes():
    # type: () -> None
    """
    Simulate a client application that inserts rows by connecting via the proxy node.
    """
    with rethinkdb.r.connect(host=HOST, port=PROXY_PORT) as conn:
        table = HEROES_TABLE
        documents = HEROES_INITIAL_DOCUMENTS

        # See: https://rethinkdb.com/api/python/insert
        response = rethinkdb.r.db(DATABASE).table(table).insert(documents).run(conn)
        assert response['errors'] == 0
        assert response['inserted'] == len(documents)


def simulate_client_reads():
    # type: () -> None
    """
    Simulate a client application that reads rows by connecting via the proxy node.
    """
    with rethinkdb.r.connect(db=DATABASE, host=HOST, port=PROXY_PORT) as conn:
        all_heroes = list(rethinkdb.r.table('heroes').run(conn))
        assert len(all_heroes) == len(HEROES_INITIAL_DOCUMENTS)

        famous_heroes = list(rethinkdb.r.table('heroes').filter(rethinkdb.r.row['appearances_count'] >= 50).run(conn))
        assert len(famous_heroes) == NUM_FAMOUS_HEROES


@pytest.fixture(scope='session')
def dd_environment(instance):
    # type: (Instance) -> Iterator
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    env_vars = {
        'RETHINKDB_IMAGE': IMAGE,
        'RETHINKDB_CONNECT_SERVER_PORT': str(CONNECT_SERVER_PORT),
        'RETHINKDB_PROXY_PORT': str(PROXY_PORT),
    }  # type: Dict[str, str]

    conditions = [
        WaitFor(create_tables, attempts=1),
        WaitFor(simulate_client_writes, attempts=1),
        WaitFor(simulate_client_reads, attempts=1),
    ]

    log_patterns = [
        r'Server ready, "server0".*',
        r'Connected to server "server1".*',
        r'Connected to server "server2".*',
        r'Connected to proxy.*',
    ]  # type: List[str]

    with docker_run(compose_file, env_vars=env_vars, conditions=conditions, log_patterns=log_patterns):
        config = {'instances': [instance]}
        yield config, E2E_METADATA
