# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
@pytest.mark.skip(reason="ianbytchek/riak-cs docker image not compatible with gh runner docker v26")
def test_check(aggregator, check):
    check.check(common.generate_config_with_creds())
    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, check.OK, tags=common.EXPECTED_TAGS)
    for metric in common.EXPECTED_METRICS_21:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)
