# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.glusterfs import GlusterfsCheck

from .common import E2E_METRICS

pytestmark = pytest.mark.e2e


def test_e2e(dd_agent_check, config):
    aggregator = dd_agent_check(config)

    for metric in E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check("glusterfs.cluster.health", GlusterfsCheck.OK)
    aggregator.assert_all_metrics_covered()
