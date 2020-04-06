# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.fluentd import Fluentd

from .common import CHECK_NAME, EXPECTED_GAUGES, HOST, INSTANCE_WITH_PLUGIN


def assert_basic_case(aggregator):
    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']

    aggregator.assert_service_check('fluentd.is_ok', status=Fluentd.OK, tags=sc_tags, count=2)

    for m in EXPECTED_GAUGES:
        aggregator.assert_metric('{0}.{1}'.format(CHECK_NAME, m), tags=['plugin_id:plg1'])

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_basic_case_integration(aggregator):
    instance = copy.deepcopy(INSTANCE_WITH_PLUGIN)
    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check(None)
    check.check(None)

    assert_basic_case(aggregator)


@pytest.mark.e2e
def test_basic_case_e2e(dd_agent_check):
    instance = copy.deepcopy(INSTANCE_WITH_PLUGIN)
    aggregator = dd_agent_check(instance, rate=True)

    assert_basic_case(aggregator)
