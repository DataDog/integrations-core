# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import contextmanager

import rethinkdb
from rethinkdb import r

from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.docker import temporarily_pause_service
from datadog_checks.dev.structures import EnvVars

from .common import (
    COMPOSE_ENV_VARS,
    COMPOSE_FILE,
    CONNECT_SERVER_PORT,
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_CONFIG,
    HEROES_TABLE_DOCUMENTS,
    HOST,
    PROXY_PORT,
    SERVERS,
)


def setup_cluster():
    # type: () -> None
    """
    Configure the test cluster.
    """
    _create_database()
    _create_test_table()
    _simulate_client_writes()
    _simulate_client_reads()


def _create_database():
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
    service = 'rethinkdb-{}'.format(server)

    def _servers_have_rebalanced(conn):
        # type: (rethinkdb.net.Connection) -> bool
        # RethinkDB will rebalance data across tables and remove the server from 'server_status' afterwards.
        servers = list(r.db('rethinkdb').table('server_status').run(conn))
        return len(servers) == len(SERVERS) - 1

    with EnvVars(COMPOSE_ENV_VARS):
        with temporarily_pause_service(service, compose_file=COMPOSE_FILE):
            with r.connect(host=HOST, port=CONNECT_SERVER_PORT) as conn:
                wait_until_rebalanced = WaitFor(lambda: _servers_have_rebalanced(conn))
                wait_until_rebalanced()

            yield
