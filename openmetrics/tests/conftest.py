# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest
from prometheus_client.openmetrics.exposition import generate_latest as generate_latest_strict

from datadog_checks.base import ensure_unicode
from datadog_checks.dev import docker_run

from .common import HERE, INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    log_patterns = ['Server is ready to receive web requests']

    with docker_run(compose_file, log_patterns=log_patterns, sleep=10):
        yield INSTANCE


@pytest.fixture
def poll_mock(mock_http_response):
    registry = CollectorRegistry()
    g1 = Gauge('metric1', 'processor usage', ['matched_label', 'node', 'flavor'], registry=registry)
    g1.labels(matched_label="foobar", node="host1", flavor="test").set(99.9)
    g2 = Gauge('metric2', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g2.labels(matched_label="foobar", node="host2", timestamp="123").set(12.2)
    c1 = Counter('counter1', 'hits', ['node'], registry=registry)
    c1.labels(node="host2").inc(42)
    c2 = Counter('counter2_total', 'hits total', ['node'], registry=registry)
    c2.labels(node="host2").inc(42)
    g3 = Gauge('metric3', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g3.labels(matched_label="foobar", node="host2", timestamp="456").set(float('inf'))

    mock_http_response(ensure_unicode(generate_latest(registry)), normalize_content=False)


@pytest.fixture
def strict_poll_mock(mock_http_response):
    registry = CollectorRegistry()
    g1 = Gauge('metric1', 'processor usage', ['matched_label', 'node', 'flavor'], registry=registry)
    g1.labels(matched_label="foobar", node="host1", flavor="test").set(99.9)
    g2 = Gauge('metric2', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g2.labels(matched_label="foobar", node="host2", timestamp="123").set(12.2)
    c1 = Counter('counter1', 'hits', ['node'], registry=registry)
    c1.labels(node="host2").inc(42)
    g3 = Gauge('metric3', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g3.labels(matched_label="foobar", node="host2", timestamp="456").set(float('inf'))

    mock_http_response(ensure_unicode(generate_latest_strict(registry)), normalize_content=False)
