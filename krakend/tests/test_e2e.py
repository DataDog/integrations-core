# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import get_docker_hostname
from tests.helpers import get_metrics_from_metadata
from tests.types import InstanceBuilder


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance: InstanceBuilder):
    config = {"init_config": {}, "instances": [instance(True, True, get_docker_hostname(), 9090)]}

    aggregator = dd_agent_check(config, check_rate=True)

    metadata_metrics = get_metrics_from_metadata()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check):
    aggregator = dd_agent_check(
        {"init_config": {}, "instances": []},
        check_rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )

    metadata_metrics = get_metrics_from_metadata()

    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )

    # Krakend exposes both port 8080 (HTTP gateway) and 9090 (metrics). The trial
    # proxy probes both; the 8080 candidate's OpenMetrics scrape fails (non-Prometheus
    # response), which calls submit_health_check(CRITICAL) inside the scraper before
    # raising. The _TrialModeProxy must buffer that submission and discard it on
    # candidate failure — only the winner's OK should reach the aggregator.
    aggregator.assert_service_check(
        "krakend.api.openmetrics.health",
        status=AgentCheck.CRITICAL,
        count=0,
    )
    aggregator.assert_service_check(
        "krakend.api.openmetrics.health",
        status=AgentCheck.OK,
        at_least=1,
    )
