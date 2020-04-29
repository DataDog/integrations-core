# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests, pdh_mocks_fixture  # noqa: F401

from datadog_checks.exchange_server import ExchangeCheck
from datadog_checks.exchange_server.exchange_server import DEFAULT_COUNTERS

from .common import CHECK_NAME, METRIC_INSTANCES, MINIMAL_INSTANCE


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_basic_check(aggregator):
    initialize_pdh_tests()
    instance = MINIMAL_INSTANCE
    c = ExchangeCheck(CHECK_NAME, {}, [instance])
    c.check(instance)

    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        instances = METRIC_INSTANCES.get(metric)
        if instances is not None:
            for inst in instances:
                aggregator.assert_metric(metric, tags=["instance:%s" % inst], count=1)
        else:
            aggregator.assert_metric(metric, tags=None, count=1)

    assert aggregator.metrics_asserted_pct == 100.0
