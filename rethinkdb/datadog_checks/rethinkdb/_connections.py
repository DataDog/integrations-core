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


class Connection:
    """
    Base class and interface for connection objects.
    """

    def __enter__(self):
        # type: () -> Connection
        return self

    def __exit__(self, *args):
        # type: (*Any) -> None
        pass

    def server(self):
        # type: () -> ConnectionServer
        raise NotImplementedError

    def run(self, query):
        # type: (rethinkdb.RqlQuery) -> Any
        raise NotImplementedError


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

    def server(self):
        # type: () -> ConnectionServer
        return self._conn.server()

    def run(self, query):
        # type: (rethinkdb.RqlQuery) -> Any
        return query.run(self._conn)
