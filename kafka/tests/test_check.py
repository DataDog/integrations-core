# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    KAFKA_COMMON_E2E_METRICS,
    KAFKA_KRAFT_E2E_METRICS,
    KAFKA_ZK_E2E_METRICS,
    OPTIONAL_KRAFT_E2E_METRICS,
    kraft,
    not_kraft,
)


@not_kraft
@pytest.mark.e2e
def test_zk_metrics(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in KAFKA_COMMON_E2E_METRICS + KAFKA_ZK_E2E_METRICS + JVM_E2E_METRICS_NEW:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)


@kraft
@pytest.mark.e2e
def test_kraft_metrics(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in KAFKA_COMMON_E2E_METRICS + KAFKA_KRAFT_E2E_METRICS + JVM_E2E_METRICS_NEW:
        at_least = 0 if metric in OPTIONAL_KRAFT_E2E_METRICS else 1
        aggregator.assert_metric(metric, at_least=at_least)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)
