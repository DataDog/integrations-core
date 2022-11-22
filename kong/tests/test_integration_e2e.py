import platform, os

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.kong import Kong

from . import common

BAD_CONFIG = {'kong_status_url': 'http://localhost:1111/status/'}

GAUGES = [
    'kong.total_requests',
    'kong.connections_active',
    'kong.connections_waiting',
    'kong.connections_reading',
    'kong.connections_accepted',
    'kong.connections_writing',
    'kong.connections_handled',
]

# Our test environment only exposes these 3 metrics via prometheus
EXPECTED_METRICS = [
    'kong.memory.lua.shared_dict.bytes',
    'kong.memory.lua.shared_dict.total_bytes',
    'kong.nginx.http.current_connections',
]

# Different metrics for the new version of Kong
EXPECTED_METRICS_V3 = [
    'kong.memory.lua.shared_dict.bytes',
    'kong.memory.lua.shared_dict.total_bytes',
    'kong.nginx.http.connections.total',
]

DATABASES = ['reachable']


@pytest.fixture
def check():
    return lambda instance: Kong(common.CHECK_NAME, {}, [instance])


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, check, dd_run_check):
    for stub in common.CONFIG_STUBS:
        dd_run_check(check(stub))

    _assert_check(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    config = {'init_config': {}, 'instances': common.CONFIG_STUBS}
    aggregator = dd_agent_check(config)

    _assert_check(aggregator)


def _assert_check(aggregator):
    for stub in common.CONFIG_STUBS:
        expected_tags = stub['tags']

        for mname in GAUGES:
            aggregator.assert_metric(mname, tags=expected_tags, count=1)

        aggregator.assert_service_check(
            'kong.can_connect', status=Kong.OK, tags=['kong_host:localhost', 'kong_port:8001'] + expected_tags, count=1
        )

    aggregator.all_metrics_asserted()


@pytest.mark.usefixtures('dd_environment')
def test_connection_failure(aggregator, check, dd_run_check):
    with pytest.raises(Exception):
        dd_run_check(check(BAD_CONFIG))
    aggregator.assert_service_check(
        'kong.can_connect', status=Kong.CRITICAL, tags=['kong_host:localhost', 'kong_port:1111'], count=1
    )

    aggregator.all_metrics_asserted()


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.e2e
def test_e2e_openmetrics_v2(dd_agent_check, instance_openmetrics_v2):
    kong_version = os.environ.get('KONG_VERSION').split('.')[0]
    aggregator = dd_agent_check(instance_openmetrics_v2, rate=True)
    tags = "endpoint:" + instance_openmetrics_v2.get('openmetrics_endpoint')
    tags = instance_openmetrics_v2.get('tags').append(tags)
    aggregator.assert_service_check('kong.openmetrics.health', AgentCheck.OK, count=2, tags=tags)

    # Only a subset(3) of metrics are exposed currently in our Kong test environment
    if kong_version >= '3':
        metrics = EXPECTED_METRICS_V3
    else:
        metrics = EXPECTED_METRICS

    for metric in metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=tags)
