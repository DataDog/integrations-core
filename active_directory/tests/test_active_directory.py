# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests, pdh_mocks_fixture  # noqa: F401

from datadog_checks.active_directory import ActiveDirectoryCheck
from datadog_checks.active_directory.metrics import DEFAULT_COUNTERS
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.testing import requires_py2
from datadog_checks.dev.utils import get_metadata_metrics

from .common import CHECK_NAME, MINIMAL_INSTANCE

pytestmark = [requires_py2, pytest.mark.usefixtures('pdh_mocks_fixture')]


@pytest.fixture(autouse=True)
def setup_check():
    initialize_pdh_tests()


def test_basic_check(aggregator, dd_run_check):
    # type: (AggregatorStub) -> None
    instance = MINIMAL_INSTANCE
    check = ActiveDirectoryCheck(CHECK_NAME, {}, [instance])
    dd_run_check(check)

    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        aggregator.assert_metric(metric, tags=None, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
