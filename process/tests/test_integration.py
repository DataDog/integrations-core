# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from copy import deepcopy

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_integration(aggregator, check, dd_run_check):
    dd_run_check(check)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check):
    aggregator = dd_agent_check(deepcopy(common.INSTANCE))
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)
