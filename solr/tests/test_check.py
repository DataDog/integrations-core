# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import SOLR_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)  # type: AggregatorStub

    for metric in SOLR_METRICS + JVM_E2E_METRICS_NEW:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)
