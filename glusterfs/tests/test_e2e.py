# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.glusterfs import GlusterfsCheck

from .common import EXPECTED_METRICS

pytestmark = pytest.mark.e2e


def test_e2e(dd_agent_check, config):
    aggregator = dd_agent_check(config)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check("glusterfs.brick.health", GlusterfsCheck.OK)
    aggregator.assert_service_check("glusterfs.volume.health", GlusterfsCheck.OK)
    aggregator.assert_service_check("glusterfs.brick.health", GlusterfsCheck.OK)
    aggregator.assert_all_metrics_covered()
