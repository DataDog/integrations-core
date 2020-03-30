import os

import mock
import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

from datadog_checks.base import ensure_unicode
from datadog_checks.dev import docker_run, get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

HOST = get_docker_hostname()

INSTANCE_E2E = {
    'prometheus_url': 'http://{}:9090/metrics'.format(HOST),
    'namespace': 'prometheus',
    'metrics': [{'prometheus_target_interval_length_seconds': 'target_interval_seconds'}, 'go_memstats_mallocs_total'],
}

INSTANCE_UNIT = {
    'prometheus_url': 'http://localhost:10249/metrics',
    'namespace': 'prometheus',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1'],
    'send_histograms_buckets': True,
    'send_monotonic_counter': True,
}


@pytest.fixture(scope="session")
def instance():
    return INSTANCE_UNIT.copy()


@pytest.fixture(scope="session")
def e2e_instance():
    return INSTANCE_E2E.copy()


@pytest.fixture(scope="session")
def dd_environment(e2e_instance):
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yaml')
    log_patterns = 'Server is ready to receive web requests'

    with docker_run(compose_file, log_patterns=log_patterns, sleep=10):
        yield e2e_instance


@pytest.fixture
def poll_mock():
    registry = CollectorRegistry()
    # pylint: disable=E1123,E1101
    g1 = Gauge('metric1', 'processor usage', ['matched_label', 'node', 'flavor'], registry=registry)
    g1.labels(matched_label="foobar", node="host1", flavor="test").set(99.9)
    g2 = Gauge('metric2', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g2.labels(matched_label="foobar", node="host2", timestamp="123").set(12.2)
    c1 = Counter('counter1', 'hits', ['node'], registry=registry)
    c1.labels(node="host2").inc(42)
    g3 = Gauge('metric3', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
    g3.labels(matched_label="foobar", node="host2", timestamp="456").set(float('inf'))

    data = ensure_unicode(generate_latest(registry))
    data = data.replace("_total", "")

    poll_mock_patch = mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: data.split("\n"), headers={'Content-Type': "text/plain"},
        ),
    )
    with poll_mock_patch:
        yield
