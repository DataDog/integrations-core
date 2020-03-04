# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

from ..connections import Connection
from ..queries import QueryEngine
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_config_totals(engine, conn):
    # type: (QueryEngine, Connection) -> Iterator[Metric]
    """
    Collect aggregated metrics about cluster configuration.

    See: https://rethinkdb.com/docs/system-tables/#configuration-tables
    """
    logger.debug('collect_config_totals')

    totals = engine.query_config_totals(conn)
    logger.debug('config_totals totals=%r', totals)

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.server.total',
        'value': totals['servers'],
        'tags': [],
    }

    yield {
        'type': 'gauge',
        'name': 'rethinkdb.database.total',
        'value': totals['databases'],
        'tags': [],
    }

    for database, total in totals['tables_per_database'].items():
        tags = ['database:{}'.format(database)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.database.table.total',
            'value': total,
            'tags': tags,
        }

    for table, total in totals['secondary_indexes_per_table'].items():
        tags = ['table:{}'.format(table)]

        yield {
            'type': 'gauge',
            'name': 'rethinkdb.table.secondary_index.total',
            'value': total,
            'tags': tags,
        }
