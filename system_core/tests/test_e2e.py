# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric_has_tag(metric, instance["tags"][0])

