# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    ACTIVEMQ_E2E_JVM_METRICS,
    ACTIVEMQ_E2E_METRICS,
    ARTEMIS_E2E_METRICS,
    OPTIONAL_ARTEMIS_E2E_METRICS,
    artemis,
    not_artemis,
)


@not_artemis
@pytest.mark.e2e
def test_activemq_metrics(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)

    for metric in ACTIVEMQ_E2E_METRICS + ACTIVEMQ_E2E_JVM_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=ACTIVEMQ_E2E_JVM_METRICS)


@artemis
@pytest.mark.e2e
def test_artemis_metrics(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in ARTEMIS_E2E_METRICS + JVM_E2E_METRICS_NEW:
        at_least = 0 if metric in OPTIONAL_ARTEMIS_E2E_METRICS else 1
        aggregator.assert_metric(metric, at_least=at_least)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)
