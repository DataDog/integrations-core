# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.ceph import Ceph

from .common import (
    BASIC_CONFIG,
    CEPH_VERSION,
    EXPECTED_METRICS,
    EXPECTED_SERVICE_CHECKS,
    EXPECTED_SERVICE_TAGS,
)

CEPH_MAJOR_VERSION = int(CEPH_VERSION.lstrip('v').split('.')[0] or 0)
RATE_METRICS = {'ceph.read_bytes', 'ceph.write_bytes'}


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check(BASIC_CONFIG, rate=True)

    for metric in EXPECTED_METRICS:
        # Rates need two samples with the same tags, but `ceph_mon_state` can change between runs before Octopus.
        if CEPH_MAJOR_VERSION < 15 and metric in RATE_METRICS:
            continue
        aggregator.assert_metric(metric, at_least=1)

    aggregator.assert_metric('ceph.num_mons.active', value=3, at_least=1)

    # The tag comes from `mon_status`, which Octopus (15) removed.
    if CEPH_MAJOR_VERSION < 15:
        aggregator.assert_metric_has_tag_prefix('ceph.num_mons', 'ceph_mon_state:', at_least=1)
    else:
        aggregator.assert_metric_has_tag_prefix('ceph.num_mons', 'ceph_mon_state:', count=0)

    for sc in EXPECTED_SERVICE_CHECKS:
        aggregator.assert_service_check(sc, status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)
