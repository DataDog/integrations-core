# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics

from .common import E2E_METRICS


def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_service_check('argo_rollouts.openmetrics.health', ServiceCheck.OK, count=2)
    for metric in E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    assert_service_checks(aggregator)
