# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

from typing import Iterator

import rethinkdb

from .._queries import QueryEngine
from .._types import Metric


def collect_current_issues(engine, conn):
    # type: (QueryEngine, rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about current system issues.

    See: https://rethinkdb.com/docs/system-issues/
    """
    return iter(())  # TODO
