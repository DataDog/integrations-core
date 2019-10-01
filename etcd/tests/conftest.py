# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.etcd.metrics import METRIC_MAP

from .common import COMPOSE_FILE, LEGACY_INSTANCE, URL, V3_PREVIEW


def add_key():
    if not V3_PREVIEW:
        requests.post('{}/v2/keys/message'.format(URL), data={'value': 'Hello world'})


@pytest.fixture(scope='session')
def dd_environment(instance):
    if V3_PREVIEW:
        endpoints = '{}/metrics'.format(URL)
    else:
        endpoints = ('{}/v2/stats/self'.format(URL), '{}/v2/stats/store'.format(URL))

    # Sleep a bit so all metrics are available
    with docker_run(COMPOSE_FILE, conditions=[CheckEndpoints(endpoints), add_key], sleep=3):
        yield instance


@pytest.fixture(scope='session')
def legacy_instance():
    return copy.deepcopy(LEGACY_INSTANCE)


@pytest.fixture(scope='session')
def instance():
    if V3_PREVIEW:
        return {'use_preview': True, 'prometheus_url': '{}/metrics'.format(URL)}
    else:
        return copy.deepcopy(LEGACY_INSTANCE)


@pytest.fixture(scope='session')
def openmetrics_metrics():
    metrics = list(METRIC_MAP.values())

    histograms = ['network.peer.round_trip_time.seconds']

    for histogram in histograms:
        metrics.remove(histogram)
        metrics.append('{}.count'.format(histogram))
        metrics.append('{}.sum'.format(histogram))

    return metrics
