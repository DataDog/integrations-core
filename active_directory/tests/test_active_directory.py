# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from .common import (
    CHECK_NAME,
    MINIMAL_INSTANCE,
)
from datadog_checks.active_directory import ActiveDirectoryCheck
from datadog_checks.active_directory.active_directory import DEFAULT_COUNTERS

# for reasons unknown, flake8 says that pdh_mocks_fixture is unused, even though
# it's used below.  noqa to suppress that error.
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_basic_check(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = MINIMAL_INSTANCE
    c = ActiveDirectoryCheck(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        Aggregator.assert_metric(metric, tags=None, count=1)

    assert Aggregator.metrics_asserted_pct == 100.0
