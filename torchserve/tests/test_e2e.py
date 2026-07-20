# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.torchserve import TorchserveCheck

from .management.common import METRICS as MANAGEMENT_METRICS
from .management.common import NON_PREDICTABLE_TAGS
from .openmetrics.metrics import METRICS as OPENMETRICS_METRICS
from .openmetrics.metrics import OPTIONAL_METRICS

pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("dd_environment")]


def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True, discovery_min_instances=3)

    # Discovery generates one candidate per port, so the union of all three
    # instance types' metrics/service checks is submitted in a single run.
    for expected_metric in OPENMETRICS_METRICS.keys():
        at_least = 0 if expected_metric in OPTIONAL_METRICS else 1
        aggregator.assert_metric(f"torchserve.openmetrics.{expected_metric}", at_least=at_least)
        # discovery derives the endpoint from the container's own IP, not the
        # docker hostname used by the static instance, so the exact `endpoint`
        # tag value isn't predictable here.

    aggregator.assert_service_check(
        "torchserve.openmetrics.health",
        status=AgentCheck.OK,
    )

    # discovery can't predict the `inference_api_url` tag value ahead of time,
    # so only the service check status is asserted here.
    aggregator.assert_service_check(
        "torchserve.inference_api.health",
        AgentCheck.OK,
    )

    for metric in MANAGEMENT_METRICS:
        non_predictable_tags = [
            t.split(":")[0] for t in metric.get("tags", []) if t.split(":")[0] in NON_PREDICTABLE_TAGS
        ]
        expected_tags = [t for t in metric.get("tags", []) if t.split(":")[0] not in NON_PREDICTABLE_TAGS]

        aggregator.assert_metric(
            metric["name"],
            at_least=metric.get("at_least", 1),
        )

        for tag in expected_tags:
            aggregator.assert_metric_has_tag(metric["name"], tag)

        for tag in non_predictable_tags:
            aggregator.assert_metric_has_tag_prefix(metric["name"], tag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, TorchserveCheck)
