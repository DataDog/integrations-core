# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator

import rethinkdb

from .. import operations
from ..types import Metric

logger = logging.getLogger(__name__)


def collect_system_jobs(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about system jobs.

    See: https://rethinkdb.com/docs/system-jobs/
    """
    logger.debug('collect_system_jobs')

    for job in operations.query_system_jobs(conn):
        logger.debug('job %r', job)

        duration = job['duration_sec']
        servers = job['servers']

        tags = ['server:{}'.format(server) for server in servers]

        if job['type'] == 'index_construction':
            job_tags = tags + [
                'job_type:{}'.format(job['type']),
                'database:{}'.format(job['info']['db']),
                'table:{}'.format(job['info']['table']),
                'index:{}'.format(job['info']['index']),
            ]
            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.duration',
                'value': duration,
                'tags': job_tags,
            }

        elif job['type'] == 'backfill':
            job_tags = tags + [
                'job_type:{}'.format(job['type']),
                'database:{}'.format(job['info']['db']),
                'destination_server:{}'.format(job['info']['destination_server']),
                'source_server:{}'.format(job['info']['source_server']),
                'table:{}'.format(job['info']['table']),
            ]
            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.duration',
                'value': duration,
                'tags': job_tags,
            }
