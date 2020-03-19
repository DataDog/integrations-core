# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

import rethinkdb

from .. import operations
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_current_issues(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about current system issues.

    See: https://rethinkdb.com/docs/system-issues/
    """
    logger.debug('collect_current_issues')

    summary = operations.query_current_issues_summary(conn)
    logger.debug('current_issues %r', summary)

    for issue_type, total in summary['issues'].items():
        yield {
            'type': 'gauge',
            'name': 'rethinkdb.current_issues.issues',
            'value': total,
            'tags': ['issue_type:{}'.format(issue_type)],
        }

    for issue_type, total in summary['critical_issues'].items():
        yield {
            'type': 'gauge',
            'name': 'rethinkdb.current_issues.critical_issues',
            'value': total,
            'tags': ['issue_type:{}'.format(issue_type)],
        }
