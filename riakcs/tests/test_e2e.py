# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check, check):
    aggregator = dd_agent_check(common.generate_config_with_creds(), rate=True)
    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, check.OK, tags=common.EXPECTED_TAGS)
    for metric in common.EXPECTED_METRICS_21:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)
