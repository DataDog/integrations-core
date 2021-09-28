# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import pytest

from .common import INSTANCE, INSTANCE_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(deepcopy(INSTANCE))

    for metric in INSTANCE_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
