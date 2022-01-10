# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.ceph import Ceph

from .common import BASIC_CONFIG, CHECK_NAME, EXPECTED_METRICS, EXPECTED_SERVICE_CHECKS, EXPECTED_SERVICE_TAGS


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, at_least=1)

    for sc in EXPECTED_SERVICE_CHECKS:
        aggregator.assert_service_check(sc, status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)
