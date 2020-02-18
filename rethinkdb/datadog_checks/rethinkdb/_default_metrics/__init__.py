# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

import itertools
from typing import Callable, Dict, Iterator

import rethinkdb

from .._types import DefaultMetricGroup, Metric
from ._current_issues import collect_current_issues
from ._statistics import (
    collect_cluster_statistics,
    collect_replica_statistics,
    collect_server_statistics,
    collect_table_statistics,
)
from ._statuses import collect_server_status, collect_table_status
from ._system_jobs import collect_system_jobs

DEFAULT_METRIC_GROUPS = {
    'cluster_statistics': collect_cluster_statistics,
    'server_statistics': collect_server_statistics,
    'table_statistics': collect_table_statistics,
    'replica_statistics': collect_replica_statistics,
    'server_status': collect_server_status,
    'table_status': collect_table_status,
    'system_jobs': collect_system_jobs,
    'current_issues': collect_current_issues,
}  # type: Dict[DefaultMetricGroup, Callable[[rethinkdb.net.Connection], Iterator[Metric]]]

__all__ = ['DEFAULT_METRIC_GROUPS']
