# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

import itertools
from typing import Callable, Dict, Iterator

import rethinkdb

from .._types import Metric
from ._current_issues import collect_current_issues
from ._statistics import (
    collect_cluster_statistics,
    collect_replica_statistics,
    collect_server_statistics,
    collect_table_statistics,
)
from ._statuses import collect_server_status, collect_table_status
from ._system_jobs import collect_system_jobs

__all__ = ['collect_default_metrics']


def collect_default_metrics(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    metrics = itertools.chain(
        collect_cluster_statistics(conn),
        collect_server_statistics(conn),
        collect_table_statistics(conn),
        collect_replica_statistics(conn),
        collect_server_status(conn),
        collect_table_status(conn),
        collect_system_jobs(conn),
        collect_current_issues(conn),
    )

    for metric in metrics:
        yield metric
