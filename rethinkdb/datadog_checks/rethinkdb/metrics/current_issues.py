# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

from ..connections import Connection
from ..queries import QueryEngine
from ..types import Metric
from ._base import DocumentMetricCollector

logger = logging.getLogger(__name__)


class CurrentIssuesCollector(DocumentMetricCollector):
    """
    Collect metrics about current system issues.

    See: https://rethinkdb.com/docs/system-issues/
    """

    name = 'current_issues'
    group = 'current_issues'

    def _collect(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Metric]
        totals = engine.query_current_issues_totals(conn)

        for issue_type, total in totals['issues_by_type'].items():
            tags = ['issue_type:{}'.format(issue_type)]
            yield self._make_metric(type='gauge', name='total', value=total, tags=tags)

        for issue_type, total in totals['critical_issues_by_type'].items():
            tags = ['issue_type:{}'.format(issue_type)]
            yield self._make_metric(type='gauge', name='critical.total', value=total, tags=tags)


collect_current_issues = CurrentIssuesCollector()
