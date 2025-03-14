# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_metric('silverstripe_cms.pages_live.count', value=3)
    aggregator.assert_metric('silverstripe_cms.pages.count', value=3)
