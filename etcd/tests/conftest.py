# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.etcd.metrics import METRIC_MAP

from .common import COMPOSE_FILE, URL

# Needed to mount volume for logging
E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}


@pytest.fixture(scope='session')
def dd_environment(instance):
    endpoints = '{}/metrics'.format(URL)

    # Sleep a bit so all metrics are available
    with docker_run(COMPOSE_FILE, conditions=[CheckEndpoints(endpoints)], sleep=3):
        yield instance, E2E_METADATA


@pytest.fixture(scope='session')
def instance():
    return {'prometheus_url': '{}/metrics'.format(URL)}


@pytest.fixture(scope='session')
def openmetrics_metrics():
    metrics = list(METRIC_MAP.values())
    metrics.append('server.version')

    histograms = [
        'network.peer.round_trip_time.seconds',
        'debugging.mvcc.db.compaction.total.duration.milliseconds',
        'debugging.mvcc.db.compaction.pause.duration.milliseconds',
        'debugging.mvcc.index.compaction.pause.duration.milliseconds',
        'debugging.snap.save.marshalling.duration.seconds',
        'debugging.snap.save.total.duration.seconds',
        'disk.wal.fsync.duration.seconds',
        'disk.backend.commit.duration.seconds',
        'disk.backend.snapshot.duration.seconds',
        'go.gc.duration.seconds',
        'snap.db.fsync.duration.seconds',
        'snap.db.save.total.duration.seconds',
        'snap.fsync.duration.seconds',
    ]

    for histogram in histograms:
        metrics.remove(histogram)
        metrics.append('{}.count'.format(histogram))
        metrics.append('{}.sum'.format(histogram))

    metrics.append('go.gc.duration.seconds.quantile')

    return metrics
