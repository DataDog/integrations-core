# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from contextlib import contextmanager
from typing import Iterator, List

from rethinkdb import r

from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.docker import temporarily_stop_service
from datadog_checks.dev.structures import EnvVars
from datadog_checks.rethinkdb.connections import Connection, RethinkDBConnection

from .common import (
    AGENT_PASSWORD,
    AGENT_USER,
    CLIENT_USER,
    COMPOSE_ENV_VARS,
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

    with RethinkDBConnection(r.connect(host=HOST, port=SERVER_PORTS['server0'])) as conn:
        conn.run(r.db_drop('test'))  # Automatically created, but we don't use it and it would skew our metrics.

        # Cluster content.
        conn.run(r.db_create(DATABASE))
        conn.run(r.db(DATABASE).table_create(HEROES_TABLE, **HEROES_TABLE_CONFIG))
        conn.run(r.db(DATABASE).table(HEROES_TABLE).index_create(HEROES_TABLE_INDEX_FIELD))

        # Users.
        # See: https://rethinkdb.com/docs/permissions-and-accounts/
        conn.run(r.db('rethinkdb').table('users').insert({'id': AGENT_USER, 'password': AGENT_PASSWORD}))
        conn.run(r.db('rethinkdb').grant(AGENT_USER, {'read': True}))

        conn.run(r.db('rethinkdb').table('users').insert({'id': CLIENT_USER, 'password': False}))
        conn.run(r.db(DATABASE).grant(CLIENT_USER, {'read': True, 'write': True}))

    # Simulate client activity.
    # NOTE: ensures that 'written_docs_*' and 'read_docs_*' metrics have non-zero values.

    with RethinkDBConnection(r.connect(host=HOST, port=SERVER_PORTS['proxy'], user=CLIENT_USER)) as conn:
        response = conn.run(r.db(DATABASE).table(HEROES_TABLE).insert(HEROES_TABLE_DOCUMENTS))
        assert response['inserted'] == len(HEROES_TABLE_DOCUMENTS)

        documents = list(conn.run(r.db(DATABASE).table(HEROES_TABLE)))
        assert len(documents) == len(HEROES_TABLE_DOCUMENTS)


@contextmanager
def temporarily_disconnect_server(server):
    # type: (str) -> Iterator[None]
    """
    Gracefully disconnect a server from the cluster.
    Ensures that the stable is left in a stable state inside and after exiting the context.
    """
    service = 'rethinkdb-{}'.format(server)
    logger.debug('temporarily_disconnect_server server=%r service=%r', server, service)

    def _server_exists(conn):
        # type: (Connection) -> bool
        servers = conn.run(r.db('rethinkdb').table('server_status').map(r.row['name']))  # type: List[str]
        logger.debug('server_exists server=%r servers=%r', server, servers)
        return server in servers

    def _leader_election_done(conn):
        # type: (Connection) -> bool
        STABLE_REPLICA_STATES = {'ready', 'waiting_for_primary', 'disconnected'}

        replica_states = list(
            conn.run(
                r.db('rethinkdb')
                .table('table_status')
                .concat_map(r.row['shards'])
                .concat_map(r.row['replicas'])
                .map(r.row['state'])
            )
        )  # type: List[str]

        logger.debug('replica_states %r', replica_states)

        return all(state in STABLE_REPLICA_STATES for state in replica_states)

    def _server_disconnected(conn):
        # type: (Connection) -> bool
        return not _server_exists(conn) and _leader_election_done(conn)

    def _server_reconnected(conn):
        # type: (Connection) -> bool
        return _server_exists(conn) and _leader_election_done(conn)

    with temporarily_stop_service(service, compose_file=COMPOSE_FILE):
        with EnvVars(COMPOSE_ENV_VARS):
            with RethinkDBConnection(r.connect(host=HOST, port=SERVER_PORTS['server0'])) as conn:
                WaitFor(lambda: _server_disconnected(conn))()

            yield

    with RethinkDBConnection(r.connect(host=HOST, port=SERVER_PORTS['server0'])) as conn:
        WaitFor(lambda: _server_reconnected(conn))()
