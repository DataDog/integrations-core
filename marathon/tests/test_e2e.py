# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.e2e
def test_marathon_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)

    aggregator.assert_all_metrics_covered()
