# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_linux_proc_extras(aggregator, check):
    check.check(deepcopy(common.INSTANCE))

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, common.EXPECTED_TAG)


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check_no_irq(aggregator, check):
    check.check(deepcopy(common.INSTANCE))

    for metric in common.EXPECTED_BASE_METRICS:
        aggregator.assert_metric_has_tag(metric, common.EXPECTED_TAG)


@pytest.mark.e2e
def test_linux_proc_extras_e2e(dd_agent_check):
    aggregator = dd_agent_check(deepcopy(common.INSTANCE), rate=True)
    expected_metrics = deepcopy(common.EXPECTED_METRICS)
    # metric removed from list because env does not emit
    expected_metrics.remove('system.processes.priorities')
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
