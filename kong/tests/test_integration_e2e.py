import pytest

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

DATABASES = ['reachable']


@pytest.fixture
def check():
    return Kong(common.CHECK_NAME, {}, [{}])


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, check):
    for stub in common.CONFIG_STUBS:
        check.check(stub)

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

        aggregator.assert_metric('kong.table.count', len(DATABASES), tags=expected_tags, count=1)

        for name in DATABASES:
            tags = expected_tags + ['table:{}'.format(name)]
            aggregator.assert_metric('kong.table.items', tags=tags, count=1)

        aggregator.assert_service_check(
            'kong.can_connect', status=Kong.OK, tags=['kong_host:localhost', 'kong_port:8001'] + expected_tags, count=1
        )

    aggregator.all_metrics_asserted()


@pytest.mark.usefixtures('dd_environment')
def test_connection_failure(aggregator, check):
    with pytest.raises(Exception):
        check.check(BAD_CONFIG)
    aggregator.assert_service_check(
        'kong.can_connect', status=Kong.CRITICAL, tags=['kong_host:localhost', 'kong_port:1111'], count=1
    )

    aggregator.all_metrics_asserted()
