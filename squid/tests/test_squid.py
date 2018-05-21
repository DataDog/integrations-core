# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import common
from datadog_checks.squid import SquidCheck


@pytest.mark.integration
def test_check_fail(aggregator, spin_up_squid):
    squid_check = SquidCheck(common.CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        squid_check.check(common.BAD_CONFIG)


@pytest.mark.integration
def test_check_ok(aggregator, spin_up_squid):
    squid_check = SquidCheck(common.CHECK_NAME, {}, {})
    squid_check.check(common.CHECK_CONFIG)

    expected_tags = ["name:ok_instance", "custom_tag"]
    aggregator.assert_service_check(common.SERVICE_CHECK, tags=expected_tags, status=common.OK)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric("squid.cachemgr." + metric, tags=expected_tags)
