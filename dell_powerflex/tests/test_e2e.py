# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import ALL_EXPECTED_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check()

    gateway_tag = f"powerflex_gateway_url:{instance['powerflex_gateway_url']}"

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1, tags=[gateway_tag])

    for metric in ALL_EXPECTED_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=[gateway_tag] + metric['tags'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
