# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    check.check(deepcopy(common.INSTANCE))

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, common.EXPECTED_TAG)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check):
    aggregator = dd_agent_check(deepcopy(common.INSTANCE), rate=True)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
