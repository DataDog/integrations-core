# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import EXPECTED_INTEGRATION_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, datadog_agent):
    aggregator = dd_agent_check(rate=True)
    for m in EXPECTED_INTEGRATION_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(
        'singlestore.can_connect', AgentCheck.OK, tags=['singlestore_endpoint:localhost:3306']
    )
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '7',
        'version.minor': '5',
        'version.patch': '9',
        'version.raw': '7.5.9',
    }
    datadog_agent.assert_metadata('singlestore', version_metadata)
