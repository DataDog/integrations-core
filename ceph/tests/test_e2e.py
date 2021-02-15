# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.ceph import Ceph

from .common import BASIC_CONFIG, EXPECTED_METRICS, EXPECTED_SERVICE_CHECKS, EXPECTED_SERVICE_TAGS


@pytest.mark.e2e
def test_ceph_e2e(dd_agent_check):
    aggregator = dd_agent_check(BASIC_CONFIG, rate=True)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, at_least=1)

    for sc in EXPECTED_SERVICE_CHECKS:
        aggregator.assert_service_check(sc, status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)
