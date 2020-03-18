# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable

from datadog_checks.rethinkdb.connections import Connection


class MockConnection(Connection):
    def __init__(self, rows):
        # type: (Callable[[], Any]) -> None
        self.rows = rows

    def run(self, query):
        # type: (Any) -> Any
        return self.rows()
