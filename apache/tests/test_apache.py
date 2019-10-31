# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

from datadog_checks.apache import Apache

from .common import APACHE_GAUGES, APACHE_RATES, AUTO_CONFIG, BAD_CONFIG, HOST, PORT, STATUS_CONFIG


@pytest.mark.usefixtures("dd_environment")
def test_connection_failure(aggregator, check):
    check = check(BAD_CONFIG)
    with pytest.raises(Exception):
        check.check(BAD_CONFIG)

    sc_tags = ['host:localhost', 'port:1234']
    aggregator.assert_service_check('apache.can_connect', Apache.CRITICAL, tags=sc_tags)
    assert len(aggregator._metrics) == 0


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    check = check(STATUS_CONFIG)
    check.check(STATUS_CONFIG)

    tags = STATUS_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags, count=1)

    sc_tags = ['host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_check_auto(aggregator, check):
    check = check(AUTO_CONFIG)
    check.check(AUTO_CONFIG)

    tags = AUTO_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags, count=1)

    sc_tags = ['host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(STATUS_CONFIG, rate=True)

    tags = STATUS_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags)

    sc_tags = ['host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()


def test_metadata(check, version_metadata):
    check = check(STATUS_CONFIG)
    check.check_id = 'test:123'

    with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
        check.check(STATUS_CONFIG)

        for name, value in version_metadata.items():
            m.assert_any_call('test:123', name, value)

        assert m.call_count == len(version_metadata)
