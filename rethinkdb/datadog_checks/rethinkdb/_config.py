# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from typing import Callable, Iterator, List

import rethinkdb

from datadog_checks.base import ConfigurationError

from ._metrics.config import collect_config_totals
from ._metrics.current_issues import collect_current_issues
from ._metrics.statistics import (
    collect_cluster_statistics,
    collect_replica_statistics,
    collect_server_statistics,
    collect_table_statistics,
)
from ._metrics.statuses import collect_server_status, collect_table_status
from ._metrics.system_jobs import collect_system_jobs
from ._queries import QueryEngine
from ._types import Instance, Metric
from ._version import parse_version


class Config:
    """
    Hold instance configuration for a RethinkDB check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if not isinstance(port, int) or isinstance(port, bool):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        self._host = host  # type: str
        self._port = port  # type: int
        self._query_engine = QueryEngine(r=rethinkdb.r)

        self._collect_funcs = [
            collect_config_totals,
            collect_cluster_statistics,
            collect_server_statistics,
            collect_table_statistics,
            collect_replica_statistics,
            collect_server_status,
            collect_table_status,
            collect_system_jobs,
            collect_current_issues,
        ]  # type: List[Callable[[QueryEngine, rethinkdb.net.Connection], Iterator[Metric]]]

    @property
    def host(self):
        # type: () -> str
        return self._host

    @property
    def port(self):
        # type: () -> int
        return self._port

    def connect(self):
        # type: () -> rethinkdb.net.Connection
        host = self._host
        port = self._port
        return self._query_engine.connect(host, port)

    def collect_metrics(self, conn):
        # type: (rethinkdb.net.Connection) -> Iterator[Metric]
        for collect in self._collect_funcs:
            for metric in collect(self._query_engine, conn):
                yield metric

    def get_connected_server_version(self, conn):
        # type: (rethinkdb.net.Connection) -> str
        """
        Return the version of RethinkDB run by the server at the other end of the connection, in SemVer format.

        Example:

        >>> config.get_version(conn)
        '2.4.0~0bionic'
        """
        version_string = self._query_engine.get_connected_server_version_string(conn)
        return parse_version(version_string)

    def __repr__(self):
        # type: () -> str
        return 'Config(host={host!r}, port={port!r})'.format(host=self._host, port=self._port)
