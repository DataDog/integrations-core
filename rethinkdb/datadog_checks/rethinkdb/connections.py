# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, TypedDict

import rethinkdb

# See: https://rethinkdb.com/api/python/server
ConnectionServer = TypedDict('ConnectionServer', {'id': str, 'name': str, 'proxy': bool})


class Connection(object):
    """
    Represents a connection to a RethinkDB server.

    Abstracts away any interfaces specific to the `rethinkdb` client library.
    """

    def __init__(self, conn):
        # type: (rethinkdb.net.Connection) -> None
        self._conn = conn

    def __enter__(self):
        # type: () -> Connection
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
