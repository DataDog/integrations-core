# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests, pdh_mocks_fixture  # noqa: F401

from datadog_checks.dev.testing import requires_py2
from datadog_checks.exchange_server import ExchangeCheck
from datadog_checks.exchange_server.metrics import DEFAULT_COUNTERS

from .common import CHECK_NAME, METRIC_INSTANCES, MINIMAL_INSTANCE

pytestmark = [requires_py2, pytest.mark.usefixtures('pdh_mocks_fixture')]


@pytest.fixture(autouse=True)
def setup_check():
    initialize_pdh_tests()


@pytest.mark.integration
def test_basic_check(aggregator, dd_run_check):
    instance = MINIMAL_INSTANCE
    c = ExchangeCheck(CHECK_NAME, {}, [instance])
    dd_run_check(c)

    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        instances = METRIC_INSTANCES.get(metric)
        if instances is not None:
            for inst in instances:
                aggregator.assert_metric(metric, tags=["instance:%s" % inst], count=1)
        else:
            aggregator.assert_metric(metric, tags=None, count=1)

    assert aggregator.metrics_asserted_pct == 100.0
