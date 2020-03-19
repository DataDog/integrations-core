# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

import rethinkdb

from ..queries import QueryEngine
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_current_issues(engine, conn):
    # type: (QueryEngine, rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about current system issues.

    See: https://rethinkdb.com/docs/system-issues/
    """
    logger.debug('collect_current_issues')

    totals = engine.query_current_issues_totals(conn)
    logger.debug('current_issues totals=%r', totals)

    for issue_type, total in totals['issues_by_type'].items():
        yield {
            'type': 'gauge',
            'name': 'rethinkdb.current_issues.total',
            'value': total,
            'tags': ['issue_type:{}'.format(issue_type)],
        }

    for issue_type, total in totals['critical_issues_by_type'].items():
        yield {
            'type': 'gauge',
            'name': 'rethinkdb.current_issues.critical.total',
            'value': total,
            'tags': ['issue_type:{}'.format(issue_type)],
        }
