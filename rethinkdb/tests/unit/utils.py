# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable

from datadog_checks.rethinkdb.connections import Connection, ConnectionServer


class MockConnection(Connection):
    def __init__(self, rows):
        # type: (Callable[[], Any]) -> None
        self.rows = rows

    @property
    def host(self):
        # type: () -> str
        return 'mock.local'

    @property
    def port(self):
        # type: () -> int
        return 28015

    def server(self):
        # type: () -> ConnectionServer
        return {'id': 'test', 'name': 'testserver', 'proxy': False}

    def run(self, query):
        # type: (Any) -> Any
        return self.rows()
