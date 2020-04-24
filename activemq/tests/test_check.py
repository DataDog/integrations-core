# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.tooling.jmx import JVM_E2E_METRICS
from datadog_checks.dev.utils import get_metadata_metrics

from .common import ACTIVEMQ_E2E_METRICS


@pytest.mark.e2e
def test(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)

    for metric in ACTIVEMQ_E2E_METRICS + JVM_E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    # TODO: At the moment, JMX reported metrics are NOT in-app metrics, hence we can't assert the type yet.
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_metric_type=False, exclude=JVM_E2E_METRICS)
