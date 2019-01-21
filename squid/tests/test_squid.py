# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_fail(aggregator, check, instance):
    instance["host"] = "bad_host"
    with pytest.raises(Exception):
        check.check(instance)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_ok(aggregator, check, instance):
    check.check(instance)

    expected_tags = ["name:ok_instance", "custom_tag"]
    aggregator.assert_service_check(common.SERVICE_CHECK, tags=expected_tags, status=check.OK)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric("squid.cachemgr." + metric, tags=expected_tags)
