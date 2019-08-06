# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    aggregator.assert_metric('system.swap.swapped_in', tags=instance.get("tags"))
    aggregator.assert_metric('system.swap.swapped_out', tags=instance.get("tags"))
