# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from copy import deepcopy

import pytest
from packaging import version

from datadog_checks.dev.utils import get_metadata_metrics

from .common import CONFIG, OPENMETRICS_CONFIG, requires_management, requires_prometheus
from .metrics import (
    DEFAULT_OPENMETRICS,
    FLAKY_E2E_METRICS,
    RABBITMQ_4_0_ADDED,
    RABBITMQ_4_0_REMOVED,
    RABBITMQ_VERSION,
    assert_metric_covered,
)

log = logging.getLogger(__file__)

pytestmark = pytest.mark.e2e


@requires_management
def test_rabbitmq_e2e_management(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)
    assert_metric_covered(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@requires_prometheus
def test_rabbitmq_e2e_openmetrics(dd_agent_check):
    aggregator = dd_agent_check(OPENMETRICS_CONFIG, rate=True)
    metadata_metrics = get_metadata_metrics()
    expected_metrics = deepcopy(DEFAULT_OPENMETRICS)
    unexpected_metrics = deepcopy(FLAKY_E2E_METRICS)
    if RABBITMQ_VERSION == version.parse('4.0'):
        expected_metrics |= RABBITMQ_4_0_ADDED
        expected_metrics -= RABBITMQ_4_0_REMOVED
    else:
        unexpected_metrics |= RABBITMQ_4_0_ADDED
    for metric in expected_metrics:
        if metric in unexpected_metrics:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(metadata_metrics)
    aggregator.assert_all_metrics_covered()
