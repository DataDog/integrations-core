# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Iterator, List, Mapping

from datadog_checks.rethinkdb._connections import Connection, ConnectionServer


class MockConnection(Connection):
    def __init__(self, rows):
        # type: (List[Mapping[str, Any]]) -> None
        self.rows = rows

    def server(self):
        # type: () -> ConnectionServer
        return {'id': 'test', 'name': 'testserver', 'proxy': False}

    def run(self, query):
        # type: (Any) -> Iterator
        for row in self.rows:
            yield row
