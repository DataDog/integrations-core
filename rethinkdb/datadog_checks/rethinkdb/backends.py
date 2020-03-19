# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable, Iterator, Sequence

import rethinkdb

from .config import Config
from .connections import Connection, RethinkDBConnection
from .exceptions import CouldNotConnect
from .metrics.config import collect_config_totals
from .metrics.current_issues import collect_current_issues
from .metrics.statistics import (
    collect_cluster_statistics,
    collect_replica_statistics,
    collect_server_statistics,
    collect_table_statistics,
)
from .metrics.statuses import collect_server_status, collect_table_status
from .metrics.system_jobs import collect_system_jobs
from .queries import QueryEngine
from .types import Metric
from .version import parse_version


class Backend(object):
    """
    An interface for high-level operations performed during a RethinkDB check.

    Abstracts away any interfaces specific to the `rethinkdb` client library, while providing a default
    implementation that uses that library.
    """

    def __init__(self):
        # type: () -> None
        # NOTE: the name 'r' may look off-putting at first, but it was chosen for consistency with the officially
        # advertised ReQL usage. For example, see: https://rethinkdb.com/docs/guide/python/
        self._r = rethinkdb.r
        self._query_engine = QueryEngine(r=self._r)
        self._collect_funcs = (
            collect_config_totals,
            collect_cluster_statistics,
            collect_server_statistics,
            collect_table_statistics,
            collect_replica_statistics,
            collect_server_status,
            collect_table_status,
            collect_system_jobs,
            collect_current_issues,
        )  # type: Sequence[Callable[[QueryEngine, Connection], Iterator[Metric]]]

    def connect(self, config):
        # type: (Config) -> Connection
        """
        Establish a connection with the configured RethinkDB server.
        """
        try:
            conn = self._r.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                ssl={'ca_certs': config.tls_ca_cert} if config.tls_ca_cert is not None else None,
            )
        except rethinkdb.errors.ReqlDriverError as exc:
            raise CouldNotConnect(exc)

        return RethinkDBConnection(conn)

    def collect_metrics(self, conn):
        # type: (Connection) -> Iterator[Metric]
        """
        Collect metrics from the RethinkDB cluster we are connected to.
        """
        for collect in self._collect_funcs:
            for metric in collect(self._query_engine, conn):
                yield metric

    def collect_connected_server_version(self, conn):
        # type: (Connection) -> str
        """
        Return the version of RethinkDB run by the server at the other end of the connection, in SemVer format.
        """
        version_string = self._query_engine.query_connected_server_version_string(conn)
        return parse_version(version_string)
