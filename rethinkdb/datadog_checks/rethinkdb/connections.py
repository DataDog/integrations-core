# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
RethinkDB connection interface and implementations.
"""
from __future__ import absolute_import

from typing import Any, TypedDict

import rethinkdb

# See: https://rethinkdb.com/api/python/server
ConnectionServer = TypedDict('ConnectionServer', {'id': str, 'name': str, 'proxy': bool})

ConnectionTags = TypedDict('ConnectionTags', {'server': str, 'host': str, 'port': int, 'proxy': bool})


class Connection(object):
    """
    Base class and interface for connection objects.
    """

    def __enter__(self):
        # type: () -> Connection
        return self

    def __exit__(self, *args):
        # type: (*Any) -> None
        pass

    @property
    def host(self):
        # type: () -> str
        raise NotImplementedError  # pragma: no cover

    @property
    def port(self):
        # type: () -> int
        raise NotImplementedError  # pragma: no cover

    def server(self):
        # type: () -> ConnectionServer
        raise NotImplementedError  # pragma: no cover

    def run(self, query):
        # type: (rethinkdb.RqlQuery) -> Any
        raise NotImplementedError  # pragma: no cover


class RethinkDBConnection(Connection):
    """
    A connection backed by an actual RethinkDB connection.
    """

    def __init__(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        self._conn = conn

    def __enter__(self):
        # type: () -> RethinkDBConnection
        self._conn.__enter__()
        return self

    def __exit__(self, *args):
        # type: (*Any) -> Any
        return self._conn.__exit__(*args)

    @property
    def host(self):
        # type: () -> str
        return self._conn.host

    @property
    def port(self):
        # type: () -> int
        return self._conn.port

    def server(self):
        # type: () -> ConnectionServer
        return self._conn.server()

    def run(self, query):
        # type: (rethinkdb.RqlQuery) -> Any
        return query.run(self._conn)
