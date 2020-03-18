# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.rethinkdb.connections import Connection


class MockConnection(Connection):
    """
    A connection class that returns a fixed set of rows regardless of the query.
    """

    def __init__(self, rows):
        # type: (Any) -> None
        self.rows = rows

    def run(self, query):
        # type: (Any) -> Any
        return self.rows
