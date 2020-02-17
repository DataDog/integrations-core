# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import contextmanager
from typing import Iterator

import rethinkdb
from rethinkdb import r

from ..common import (
    CONNECT_SERVER_PORT,
    DATABASE,
    HEROES_DOCUMENTS,
    HEROES_TABLE,
    HEROES_TABLE_INITIAL_CONFIG,
    HEROES_TABLE_REPLICATED_CONFIG,
    HOST,
    NUM_FAMOUS_HEROES,
    PROXY_PORT,
)


@contextmanager
def setup_cluster_ensuring_all_default_metrics_are_defined():
    # type: () -> Iterator[None]
    """
    Configure a cluster for integration testing purposes.

    This helper should make it so that all default metrics are defined within the context block,
    including ones for transient activity such as system jobs.
    """
    with _setup_database():
        _create_test_table()
        _simulate_client_writes()
        _simulate_client_reads()
        _setup_test_table_replication()
        yield


@contextmanager
def _setup_database():
    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # See: https://rethinkdb.com/api/python/db_create
        response = r.db_create(DATABASE).run(conn)
        assert response['dbs_created'] == 1

        yield

        response = r.db_drop(DATABASE).run(conn)
        assert response['dbs_dropped'] == 1


def _create_test_table():
    # type: () -> None
    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # See: https://rethinkdb.com/api/python/table_create/
        response = r.db(DATABASE).table_create(HEROES_TABLE, **HEROES_TABLE_INITIAL_CONFIG).run(conn)
        assert response['tables_created'] == 1


def _setup_test_table_replication():
    # type: () -> None
    def _wait_backfill_started(conn):
        # type: (rethinkdb.net.Connection) -> None
        for change in r.db('rethinkdb').table('jobs').filter({'type': 'backfill'}).changes().run(conn):
            assert change is not None
            # Stop on the first backfill job event.
            break

    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # Existing data in tables will be rebalanced, triggering a backfill job on the RethinkDB server side.
        # We do all of this instead of setting up replication initially so that metrics associated to this job
        # are collected during tests.
        r.db(DATABASE).table(HEROES_TABLE).reconfigure(**HEROES_TABLE_REPLICATED_CONFIG).run(conn)
        _wait_backfill_started(conn)


def _simulate_client_writes():
    # type: () -> None
    """
    Simulate a client application that inserts rows by connecting via the proxy node.

    Calling this ensures that 'written_docs_*' metrics will have a non-zero value.
    """

    with r.connect(host=HOST, port=PROXY_PORT) as conn:
        table = HEROES_TABLE
        documents = HEROES_DOCUMENTS

        # See: https://rethinkdb.com/api/python/insert
        # NOTE: 'durability="soft"' speeds up the write by not waiting for data to be committed to disk.
        response = (
            r.db(DATABASE).table(table).insert(documents).run(conn, durability="soft", array_limit=len(documents))
        )
        assert response['errors'] == 0
        assert response['inserted'] == len(documents)


def _simulate_client_reads():
    # type: () -> None
    """
    Simulate a client application that reads rows by connecting via the proxy node.

    Calling this ensures that 'read_docs_*' metrics will have a non-zero value.
    """

    with r.connect(db=DATABASE, host=HOST, port=PROXY_PORT) as conn:
        all_heroes = list(r.table('heroes').run(conn))
        assert len(all_heroes) == len(HEROES_DOCUMENTS)

        famous_heroes = list(r.table('heroes').filter(r.row['appearances_count'] >= 50).run(conn))
        assert len(famous_heroes) == NUM_FAMOUS_HEROES
