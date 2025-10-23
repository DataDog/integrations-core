# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_metric('nutanix.health.up', value=1)

    aggregator.assert_metric('nutanix.cluster.count', value=1)
    aggregator.assert_metric('nutanix.cluster.available', value=1)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
