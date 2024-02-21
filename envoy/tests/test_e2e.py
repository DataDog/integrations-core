# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy import Envoy

from .common import (
    CONNECTION_LIMIT_METRICS,
    DEFAULT_INSTANCE,
    FLAKY_METRICS,
    LOCAL_RATE_LIMIT_METRICS,
    PROMETHEUS_METRICS,
    requires_new_environment,
)

pytestmark = [requires_new_environment]


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)

    for metric in PROMETHEUS_METRICS + LOCAL_RATE_LIMIT_METRICS + CONNECTION_LIMIT_METRICS:
        formatted_metric = "envoy.{}".format(metric)
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(formatted_metric, at_least=0)
            continue
        aggregator.assert_metric(formatted_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(
        'envoy.openmetrics.health', Envoy.OK, tags=['endpoint:{}'.format(DEFAULT_INSTANCE['openmetrics_endpoint'])]
    )
