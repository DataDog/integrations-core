# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

import itertools
from typing import Iterator

import rethinkdb

from .._types import Metric
from ._current_issues import collect_current_issues
from ._jobs import collect_jobs
from ._statistics import collect_statistics
from ._statuses import collect_statuses


def collect_default_metrics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect default metrics from various system tables.

    See: https://rethinkdb.com/docs/system-tables/
    """
    metrics = itertools.chain(
        collect_statistics(conn), collect_statuses(conn), collect_jobs(conn), collect_current_issues(conn)
    )

    for metric in metrics:
        yield metric
