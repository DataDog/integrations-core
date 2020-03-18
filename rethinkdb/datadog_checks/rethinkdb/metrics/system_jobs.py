# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Iterator, List, Tuple

from ..connections import Connection
from ..queries import QueryEngine
from ..types import Job
from ._base import DocumentMetricCollector

logger = logging.getLogger(__name__)


class SystemJobsCollector(DocumentMetricCollector[Job]):
    """
    Collect metrics about system jobs.

    See: https://rethinkdb.com/docs/system-jobs/
    """

    name = 'system_jobs'
    group = 'jobs'

    metrics = [{'type': 'gauge', 'path': 'duration_sec'}]

    def iter_documents(self, engine, conn):
        # type: (QueryEngine, Connection) -> Iterator[Tuple[Job, List[str]]]
        for job in engine.query_system_jobs(conn):
            tags = ['job_type:{}'.format(job['type'])]
            tags.extend('server:{}'.format(server) for server in job['servers'])

            # Follow job types listed on: https://rethinkdb.com/docs/system-jobs/#document-schema

            if job['type'] == 'query':
                # NOTE: Request-response queries are typically too short-lived to be captured across Agent checks.
                # Change feed queries however are long-running, they we'd be able to capture them.
                # See: https://rethinkdb.com/docs/system-jobs/#query
                # TODO(before-merging): submit within a `duration_sec` threshold instead of skipping entirely.
                continue
            elif job['type'] == 'disk_compaction':
                # Ongoing task on each server -- no information provided (i.e. `info` is empty).
                # See: https://rethinkdb.com/docs/system-jobs/#disk_compaction
                continue
            if job['type'] == 'index_construction':
                tags.extend(
                    [
                        'database:{}'.format(job['info']['db']),
                        'table:{}'.format(job['info']['table']),
                        'index:{}'.format(job['info']['index']),
                    ]
                )
            elif job['type'] == 'backfill':
                tags.extend(
                    [
                        'database:{}'.format(job['info']['db']),
                        'destination_server:{}'.format(job['info']['destination_server']),
                        'source_server:{}'.format(job['info']['source_server']),
                        'table:{}'.format(job['info']['table']),
                    ]
                )
            else:
                info = job.get('info', {})
                raise RuntimeError('Unknown job type: {!r} (info: {!r})'.format(job['type'], info))

            yield job, tags


collect_system_jobs = SystemJobsCollector()
