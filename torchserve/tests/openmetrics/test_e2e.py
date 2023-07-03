# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .metrics import METRICS, OPTIONAL_METRICS

pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("dd_environment")]


def test_check(dd_agent_check, openmetrics_instance):
    aggregator = dd_agent_check(openmetrics_instance, rate=True)

    for expected_metric in METRICS.keys():
        at_least = 0 if expected_metric in OPTIONAL_METRICS else 1
        aggregator.assert_metric(f"torchserve.openmetrics.{expected_metric}", at_least=at_least)
        aggregator.assert_metric_has_tag(
            metric_name=f'torchserve.openmetrics.{expected_metric}',
            tag=f'endpoint:{openmetrics_instance["openmetrics_endpoint"]}',
            at_least=at_least,
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        "torchserve.openmetrics.health",
        status=AgentCheck.OK,
    )
