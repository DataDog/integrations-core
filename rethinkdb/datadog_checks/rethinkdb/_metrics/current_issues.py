# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Iterator

from .._connections import Connection
from .._queries import QueryEngine
from .._types import Metric


def collect_current_issues(engine, conn):
    # type: (QueryEngine, Connection) -> Iterator[Metric]
    """
    Collect metrics about current system issues.

    See: https://rethinkdb.com/docs/system-issues/
    """
    return iter(())  # TODO
