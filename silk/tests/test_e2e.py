# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.silk import SilkCheck

from .common import METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check('silk.can_connect', Envoy.OK)
    aggregator.assert_service_check('silk.state', Envoy.OK)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())