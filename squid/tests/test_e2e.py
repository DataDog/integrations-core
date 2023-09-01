# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.squid import SquidCheck

from .common import EXPECTED_METRICS, SERVICE_CHECK


@pytest.mark.e2e
def test_check_ok(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    expected_tags = ["name:ok_instance", "custom_tag"]
    aggregator.assert_service_check(SERVICE_CHECK, tags=expected_tags, status=SquidCheck.OK)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric("squid.cachemgr." + metric, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
