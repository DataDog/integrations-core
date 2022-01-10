# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests, pdh_mocks_fixture  # noqa: F401

from datadog_checks.aspdotnet import AspdotnetCheck
from datadog_checks.dev.testing import requires_py2

from . import common

pytestmark = [requires_py2, pytest.mark.usefixtures('pdh_mocks_fixture')]


@pytest.fixture(autouse=True)
def setup_check():
    initialize_pdh_tests()


def test_basic_check(aggregator):
    instance = common.MINIMAL_INSTANCE
    c = AspdotnetCheck('aspdotnet', {}, [instance])
    c.check(instance)

    for metric in common.ASP_METRICS:
        aggregator.assert_metric(metric, tags=None, count=1)

    for metric in common.ASP_APP_METRICS:
        for i in common.ASP_APP_INSTANCES:
            aggregator.assert_metric(metric, tags=["instance:%s" % i], count=1)

    assert aggregator.metrics_asserted_pct == 100.0


def test_with_tags(aggregator):
    instance = common.INSTANCE_WITH_TAGS
    c = AspdotnetCheck('aspdotnet', {}, [instance])
    c.check(instance)

    for metric in common.ASP_METRICS:
        aggregator.assert_metric(metric, tags=['tag1', 'another:tag'], count=1)

    for metric in common.ASP_APP_METRICS:
        for i in common.ASP_APP_INSTANCES:
            aggregator.assert_metric(metric, tags=['tag1', 'another:tag', "instance:%s" % i], count=1)

    assert aggregator.metrics_asserted_pct == 100.0
