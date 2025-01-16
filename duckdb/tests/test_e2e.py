# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_all_metrics_covered()
