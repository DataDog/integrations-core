import pytest

from datadog_checks.kong import Kong

from . import common


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

        for mname in common.EXPECTED_GAUGES:
            aggregator.assert_metric(mname, tags=expected_tags, count=1)

        aggregator.assert_metric('kong.table.count', len(common.DATABASES), tags=expected_tags, count=1)

        for name in common.DATABASES:
            tags = expected_tags + ['table:{}'.format(name)]
            aggregator.assert_metric('kong.table.items', tags=tags, count=1)

        aggregator.assert_service_check(
            'kong.can_connect', status=Kong.OK, tags=['kong_host:localhost', 'kong_port:8001'] + expected_tags, count=1
        )

    aggregator.all_metrics_asserted()
