# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from typing import Iterator

import rethinkdb
from rethinkdb import r

from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.docker import temporarily_stop_service
from datadog_checks.dev.structures import EnvVars

from .common import (
    COMPOSE_ENV_VARS,
    COMPOSE_FILE,
    CONNECT_SERVER_PORT,
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_CONFIG,
    HEROES_TABLE_DOCUMENTS,
    HEROES_TABLE_INDEX_FIELD,
    HOST,
    PROXY_PORT,
)


def setup_cluster():
    # type: () -> None
    """
    Configure the test cluster.
    """
    _drop_test_database()  # Automatically created by RethinkDB, but we don't use it and it would skew our metrics.
    _create_database()
    _create_test_table()
    _simulate_client_writes()
    _simulate_client_reads()


def _drop_test_database():
    # type: () -> None
    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # See: https://rethinkdb.com/api/python/db_drop
        response = r.db_drop('test').run(conn)
        assert response['dbs_dropped'] == 1


def _create_database():
    # type: () -> None
    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # See: https://rethinkdb.com/api/python/db_create
        response = r.db_create(DATABASE).run(conn)
        assert response['dbs_created'] == 1


def _create_test_table():
    # type: () -> None
    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        # See: https://rethinkdb.com/api/python/table_create/
        response = r.db(DATABASE).table_create(HEROES_TABLE, **HEROES_TABLE_CONFIG).run(conn)
        assert response['tables_created'] == 1

        # See: https://rethinkdb.com/api/python/index_create/
        response = r.db(DATABASE).table(HEROES_TABLE).index_create(HEROES_TABLE_INDEX_FIELD).run(conn)
        assert response['created'] == 1


def _simulate_client_writes():
    # type: () -> None
    """
    Simulate a client application that inserts rows by connecting via the proxy node.

    Calling this ensures that 'written_docs_*' metrics will have a non-zero value.
    """

    with r.connect(host=HOST, port=PROXY_PORT) as conn:
        # See: https://rethinkdb.com/api/python/insert
        response = r.db(DATABASE).table(HEROES_TABLE).insert(HEROES_TABLE_DOCUMENTS).run(conn)
        assert response['errors'] == 0
        assert response['inserted'] == len(HEROES_TABLE_DOCUMENTS)


def _simulate_client_reads():
    # type: () -> None
    """
    Simulate a client application that reads rows by connecting via the proxy node.

    Calling this ensures that 'read_docs_*' metrics will have a non-zero value.
    """

    with r.connect(db=DATABASE, host=HOST, port=PROXY_PORT) as conn:
        all_heroes = list(r.table(HEROES_TABLE).run(conn))
        assert len(all_heroes) == len(HEROES_TABLE_DOCUMENTS)


@contextmanager
def temporarily_disconnect_server(server):
    """
    Gracefully disconnect a server from the cluster.
    Ensures that the stable is left in a stable state inside and after exiting the context.
    """
    service = 'rethinkdb-{}'.format(server)

    def _server_exists(conn):
        # type: (rethinkdb.net.Connection) -> bool
        return r.db('rethinkdb').table('server_status').map(r.row['name']).contains(server).run(conn)

    def _leader_election_done(conn):
        # type: (rethinkdb.net.Connection) -> bool
        STABLE_REPLICA_STATES = {'ready', 'waiting_for_primary', 'disconnected'}

        replica_states = (
            r.db('rethinkdb')
            .table('table_status')
            .concat_map(r.row['shards'])
            .concat_map(r.row['replicas'])
            .map(r.row['state'])
            .run(conn)
        )  # type: Iterator[str]

        return all(state in STABLE_REPLICA_STATES for state in replica_states)

    def _server_disconnected(conn):
        # type: (rethinkdb.net.Connection) -> bool
        return not _server_exists(conn) and _leader_election_done(conn)

    def _server_reconnected(conn):
        # type: (rethinkdb.net.Connection) -> bool
        return _server_exists(conn) and _leader_election_done(conn)

    with temporarily_stop_service(service, compose_file=COMPOSE_FILE):
        with EnvVars(COMPOSE_ENV_VARS):
            with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
                WaitFor(lambda: _server_disconnected(conn))()

            yield

    with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
        WaitFor(lambda: _server_reconnected(conn))()
