# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.torchserve import TorchserveCheck

from .openmetrics.metrics import METRICS as OPENMETRICS_METRICS
from .openmetrics.metrics import OPTIONAL_METRICS

pytestmark = [pytest.mark.e2e, pytest.mark.usefixtures("dd_environment")]


def test_e2e_discovery(dd_agent_check_discovery):
    # Discovery is scoped to the OpenMetrics endpoint only: the runtime accepts the
    # first candidate that submits metrics, and the Inference/Management API checks
    # only submit service checks, so they can never be discovered. Those APIs remain
    # manually configurable but are not part of this discovered instance.
    aggregator = dd_agent_check_discovery(check_rate=True, discovery_min_instances=1)

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

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, TorchserveCheck)
