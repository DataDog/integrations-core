# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Iterator

import rethinkdb

from .._queries import query_system_jobs
from .._types import Metric


def collect_jobs(conn):
    # type: (rethinkdb.net.Connection) -> Iterator[Metric]
    """
    Collect metrics about system jobs.

    See: https://rethinkdb.com/docs/system-jobs/
    """
    for job in query_system_jobs(conn):
        duration = job['duration_sec']
        servers = job['servers']

        tags = ['server:{}'.format(server) for server in servers]

        if job['type'] == 'query':
            client_address = job['info']['client_address']
            client_port = job['info']['client_port']

            query_tags = tags + ['client_address:{}'.format(client_address), 'client_port:{}'.format(client_port)]

            yield {
                'type': 'gauge',
                'name': 'rethinkdb.jobs.query.duration',
                'value': duration,
                'tags': query_tags,
            }

        elif job['type'] == 'index_construction':
            database = job['info']['db']
            table = job['info']['table']
            index = job['info']['index']
            progress = job['info']['progress']

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
            database = job['info']['db']
            destination_server = job['info']['destination_server']
            source_server = job['info']['source_server']
            table = job['info']['table']
            progress = job['info']['progress']

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
