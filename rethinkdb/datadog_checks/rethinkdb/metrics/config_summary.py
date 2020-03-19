# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

import rethinkdb

from .. import operations
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_config_summary(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect aggregated metrics about cluster configuration.

    See: https://rethinkdb.com/docs/system-tables/#configuration-tables
    """
    logger.debug('collect_config_summary')

    summary = operations.query_config_summary(conn)
    logger.debug('config_summary %r', summary)

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.config.servers',
        'value': summary['servers'],
        'tags': [],
    }

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.config.databases',
        'value': summary['databases'],
        'tags': [],
    }

    for database, num_tables in summary['tables_per_database'].items():
        tags = ['database:{}'.format(database)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.config.tables_per_database',
            'value': num_tables,
            'tags': tags,
        }

    for table, num_indexes in summary['secondary_indexes_per_table'].items():
        tags = ['table:{}'.format(table)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.config.secondary_indexes_per_table',
            'value': num_indexes,
            'tags': tags,
        }
