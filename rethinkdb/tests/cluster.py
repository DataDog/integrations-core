# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from contextlib import contextmanager
from typing import Iterator, List

import rethinkdb
from rethinkdb import r

from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.docker import temporarily_stop_service

from .common import (
    AGENT_PASSWORD,
    AGENT_USER,
    CLIENT_USER,
    COMPOSE_FILE,
    DATABASE,
    HEROES_TABLE,
    HEROES_TABLE_CONFIG,
    HEROES_TABLE_DOCUMENTS,
    HEROES_TABLE_INDEX_FIELD,
    HOST,
    SERVER_PORTS,
)

logger = logging.getLogger(__name__)


def setup_cluster():
    # type: () -> None
    """
    Configure the test cluster.
    """
    logger.debug('setup_cluster')

    with r.connect(host=HOST, port=SERVER_PORTS['server0']) as conn:
        # A test DB is automatically created, but we don't use it and it would skew our metrics.
        response = r.db_drop('test').run(conn)
        assert response['dbs_dropped'] == 1

        # Cluster content.
        response = r.db_create(DATABASE).run(conn)
        assert response['dbs_created'] == 1
        response = r.db(DATABASE).table_create(HEROES_TABLE, **HEROES_TABLE_CONFIG).run(conn)
        assert response['tables_created'] == 1
        response = r.db(DATABASE).table(HEROES_TABLE).index_create(HEROES_TABLE_INDEX_FIELD).run(conn)
        assert response['created'] == 1

        response = r.db(DATABASE).table(HEROES_TABLE).wait(timeout=1).run(conn)
        assert response['ready'] == 1

        # Users.
        # See: https://rethinkdb.com/docs/permissions-and-accounts/

        if AGENT_USER != 'admin':
            # Setup a dedicated Agent user.
            response = r.db('rethinkdb').table('users').insert({'id': AGENT_USER, 'password': AGENT_PASSWORD}).run(conn)
            assert response['inserted'] == 1
            response = r.db('rethinkdb').grant(AGENT_USER, {'read': True}).run(conn)
            assert response['granted'] == 1

        response = r.db('rethinkdb').table('users').insert({'id': CLIENT_USER, 'password': False}).run(conn)
        assert response['inserted'] == 1
        response = r.db(DATABASE).grant(CLIENT_USER, {'read': True, 'write': True}).run(conn)
        assert response['granted'] == 1

    # Simulate client activity.
    # NOTE: ensures that 'written_docs_*' and 'read_docs_*' metrics have non-zero values.

    with r.connect(host=HOST, port=SERVER_PORTS['server0'], user=CLIENT_USER) as conn:
        response = r.db(DATABASE).table(HEROES_TABLE).insert(HEROES_TABLE_DOCUMENTS).run(conn)
        assert response['inserted'] == len(HEROES_TABLE_DOCUMENTS)

        documents = list(r.db(DATABASE).table(HEROES_TABLE).run(conn))
        assert len(documents) == len(HEROES_TABLE_DOCUMENTS)


@contextmanager
def temporarily_disconnect_server(server):
    # type: (str) -> Iterator[None]
    """
    Gracefully disconnect a server from the cluster.

    Ensures that the cluster/replicas are in a stable state (not rebalancing) inside and after exiting the context.
    """
    service = 'rethinkdb-{}'.format(server)
    logger.debug('temporarily_disconnect_server server=%r service=%r', server, service)

    def _server_exists(conn):
        # type: (rethinkdb.net.Connection) -> bool
        servers = r.db('rethinkdb').table('server_status').map(r.row['name']).run(conn)  # type: List[str]
        logger.debug('server_exists server=%r servers=%r', server, servers)
        return server in servers

    def _leader_election_done(conn):
        # type: (rethinkdb.net.Connection) -> bool
        STABLE_REPLICA_STATES = {'ready', 'waiting_for_primary', 'disconnected'}

        replica_states = list(
            r.db('rethinkdb')
            .table('table_status')
            .concat_map(r.row['shards'].default([]))  # May be `None` on 2.3.x.
            .concat_map(r.row['replicas'])
            .map(r.row['state'])
            .run(conn)
        )  # type: List[str]

        logger.debug('replica_states %r', replica_states)

        return all(state in STABLE_REPLICA_STATES for state in replica_states)

    def _server_disconnected(conn):
        # type: (rethinkdb.net.Connection) -> bool
        return not _server_exists(conn) and _leader_election_done(conn)

    def _server_reconnected(conn):
        # type: (rethinkdb.net.Connection) -> bool
        return _server_exists(conn) and _leader_election_done(conn)

    with temporarily_stop_service(service, compose_file=COMPOSE_FILE):
        with r.connect(host=HOST, port=SERVER_PORTS['server0']) as conn:
            WaitFor(lambda: _server_disconnected(conn))()

        yield

    with r.connect(host=HOST, port=SERVER_PORTS['server0']) as conn:
        WaitFor(lambda: _server_reconnected(conn))()
