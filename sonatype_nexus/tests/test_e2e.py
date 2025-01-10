# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.sonatype_nexus import SonatypeNexusCheck

from .constants import E2E_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = SonatypeNexusCheck("sonatype_nexus", {}, [instance])
    aggregator.gauge(
        "sonatype_nexus.analytics.available_cpus_health",
        1,
        [{"sonatype_host": "localhost", "host": "http://localhost:8081"}],
    )
    for metric in E2E_METRICS:
        aggregator.gauge(metric)
    aggregator.assert_no_duplicate_all()
    aggregator.assert_all_metrics_covered()
