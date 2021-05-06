# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.glusterfs import GlusterfsCheck

from .common import CONFIG, EXPECTED_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check("glusterfs.brick.health", GlusterfsCheck.OK)
    aggregator.assert_service_check("glusterfs.volume.health", GlusterfsCheck.OK)
    aggregator.assert_service_check("glusterfs.brick.health", GlusterfsCheck.OK)
    aggregator.assert_all_metrics_covered()
