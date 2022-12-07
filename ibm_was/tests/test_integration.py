# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance, check, dd_run_check):
    check = check(instance)
    dd_run_check(check)

    for metric_name in common.METRICS_ALWAYS_PRESENT:
        aggregator.assert_metric(metric_name)
        aggregator.assert_metric_has_tag(metric_name, 'key1:value1')

    aggregator.assert_service_check(
        'ibm_was.can_connect', status=check.OK, tags=common.DEFAULT_SERVICE_CHECK_TAGS, count=1
    )
