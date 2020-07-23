# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.jmx import JVM_E2E_METRICS
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS


@pytest.mark.e2e
def test(dd_agent_check):

    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in METRICS + JVM_E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS)
