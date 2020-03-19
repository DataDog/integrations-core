# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator, cast

from ..connections import Connection
from ..queries import QueryEngine
from ..types import BackfillInfo, IndexConstructionInfo, Metric

logger = logging.getLogger(__name__)


def collect_system_jobs(engine, conn):
    # type: (QueryEngine, Connection) -> Iterator[Metric]
    """
    Collect metrics about system jobs.

    See: https://rethinkdb.com/docs/system-jobs/
    """
    logger.debug('collect_system_jobs')

    for job in engine.query_system_jobs(conn):
        logger.debug('job %r', job)

        duration = job['duration_sec']
        servers = job['servers']

        tags = ['server:{}'.format(server) for server in servers]

        if job['type'] == 'index_construction':
            # NOTE: Using `cast()` is required until tagged unions are released in mypy stable. Until then, avoid using
            # 'info' as a variable name in all cases (workaround for https://github.com/python/mypy/issues/6232).
            # See: https://mypy.readthedocs.io/en/latest/literal_types.html#tagged-unions
            index_construction_info = cast(IndexConstructionInfo, job['info'])
            database = index_construction_info['db']
            table = index_construction_info['table']
            index = index_construction_info['index']
            progress = index_construction_info['progress']

            index_construction_tags = tags + [
                'database:{}'.format(database),
                'table:{}'.format(table),
                'index:{}'.format(index),
            ]

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.index_construction.duration',
                'value': duration,
                'tags': index_construction_tags,
            }

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.index_construction.progress',
                'value': progress,
                'tags': index_construction_tags,
            }

        elif job['type'] == 'backfill':
            backfill_info = cast(BackfillInfo, job['info'])
            database = backfill_info['db']
            destination_server = backfill_info['destination_server']
            source_server = backfill_info['source_server']
            table = backfill_info['table']
            progress = backfill_info['progress']

            backfill_tags = tags + [
                'database:{}'.format(database),
                'destination_server:{}'.format(destination_server),
                'source_server:{}'.format(source_server),
                'table:{}'.format(table),
            ]

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.backfill.duration',
                'value': duration,
                'tags': backfill_tags,
            }

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.backfill.progress',
                'value': progress,
                'tags': backfill_tags,
            }
