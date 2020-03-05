# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from typing import Callable, Iterator, List, Optional

import rethinkdb

from datadog_checks.base import ConfigurationError

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
from .types import Instance, Metric
from .version import parse_version


class Config(object):
    """
    Hold instance configuration for a RethinkDB check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)
        user = instance.get('username')
        password = instance.get('password')
        tls_ca_cert = instance.get('tls_ca_cert')

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if not isinstance(port, int) or isinstance(port, bool):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        self._host = host  # type: str
        self._port = port  # type: int
        self._user = user  # type: Optional[str]
        self._password = password  # type: Optional[str]
        self._tls_ca_cert = tls_ca_cert  # type: Optional[str]

        self._r = rethinkdb.r
        self._query_engine = QueryEngine(r=self._r)

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
        ]  # type: List[Callable[[QueryEngine, Connection], Iterator[Metric]]]

    @property
    def host(self):
        # type: () -> str
        return self._host

    @property
    def port(self):
        # type: () -> int
        return self._port

    def connect(self):
        # type: () -> Connection
        host = self._host
        port = self._port
        user = self._user
        password = self._password
        ssl = {'ca_certs': self._tls_ca_cert} if self._tls_ca_cert is not None else None

        try:
            conn = self._r.connect(host=host, port=port, user=user, password=password, ssl=ssl)
        except rethinkdb.errors.ReqlDriverError as exc:
            raise CouldNotConnect(exc)

        return RethinkDBConnection(conn)

    def collect_metrics(self, conn):
        # type: (Connection) -> Iterator[Metric]
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

    def __repr__(self):
        # type: () -> str
        return 'Config(host={host!r}, port={port!r})'.format(host=self._host, port=self._port)
