# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

from ..connections import Connection
from ..queries import QueryEngine
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_current_issues(engine, conn):
    # type: (QueryEngine, Connection) -> Iterator[Metric]
    """
    Collect metrics about current system issues.

    See: https://rethinkdb.com/docs/system-issues/
    """
    logger.debug('collect_current_issues')

    totals = engine.query_current_issues_totals(conn)
    logger.debug('current_issues totals=%r', totals)

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.current_issues.total',
        'value': totals['issues'],
        'tags': [],
    }

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.current_issues.critical.total',
        'value': totals['critical_issues'],
        'tags': [],
    }

    for issue_type, total in totals['issues_by_type'].items():
        yield {
            'type': 'gauge',
            'name': 'rethinkdb.current_issues.{issue_type}.total'.format(issue_type=issue_type),
            'value': total,
            'tags': [],
        }

    for issue_type, total in totals['critical_issues_by_type'].items():
        yield {
            'type': 'gauge',
            'name': 'rethinkdb.current_issues.{issue_type}.critical.total'.format(issue_type=issue_type),
            'value': total,
            'tags': [],
        }
