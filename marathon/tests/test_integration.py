# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.usefixtures("dd_environment")
def test_marathon(aggregator, check, instance):
    check.check(instance)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)

    aggregator.assert_all_metrics_covered()
