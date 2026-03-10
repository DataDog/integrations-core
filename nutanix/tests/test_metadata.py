# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nutanix import NutanixCheck

from .metrics import (
    CLUSTER_BASIC_METRICS,
    CLUSTER_CAPACITY_METRICS,
    CLUSTER_STATS_METRICS_OPTIONAL,
    CLUSTER_STATS_METRICS_REQUIRED,
    HEALTH_METRICS,
    HOST_BASIC_METRICS,
    HOST_CAPACITY_METRICS,
    HOST_STATS_METRICS_OPTIONAL,
    HOST_STATS_METRICS_REQUIRED,
    VM_BASIC_METRICS,
    VM_CAPACITY_METRICS,
    VM_STATS_METRICS_OPTIONAL,
    VM_STATS_METRICS_REQUIRED,
)

REQUIRED_METRICS = (
    HEALTH_METRICS
    + CLUSTER_BASIC_METRICS
    + CLUSTER_CAPACITY_METRICS
    + CLUSTER_STATS_METRICS_REQUIRED
    + HOST_BASIC_METRICS
    + HOST_CAPACITY_METRICS
    + HOST_STATS_METRICS_REQUIRED
    + VM_BASIC_METRICS
    + VM_CAPACITY_METRICS
    + VM_STATS_METRICS_REQUIRED
)

OPTIONAL_METRICS = CLUSTER_STATS_METRICS_OPTIONAL + HOST_STATS_METRICS_OPTIONAL + VM_STATS_METRICS_OPTIONAL


@pytest.mark.unit
def test_all_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in REQUIRED_METRICS:
        aggregator.assert_metric(metric)

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
