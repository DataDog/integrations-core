# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics

from .common import COORDINATOR_METRICS, LEGACY_ROUTER_METRICS, ROUTER_METRICS, SIDECAR_METRICS


@pytest.mark.e2e
def test_check_llm_d_e2e(dd_agent_check, instances):
    aggregator = dd_agent_check({'instances': instances}, rate=True)

    # This only shows the check agrees with the fixtures Caddy serves, not with a live llm-d.
    # See the fixture provenance headers.
    for metric in ROUTER_METRICS + LEGACY_ROUTER_METRICS + SIDECAR_METRICS + COORDINATOR_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    # rate=True runs each of the 4 instances twice.
    aggregator.assert_service_check('llm_d.openmetrics.health', ServiceCheck.OK, count=8)
    assert_service_checks(aggregator)
