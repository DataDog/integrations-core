# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


def test_bad_config(check, instance_bad_config):
    with pytest.raises(ValueError):
        check.check(instance_bad_config)


def test_basic(aggregator, check, instance_basic):
    check.check(instance_basic)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:EventLog', 'optional:tag1'], count=1)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:Dnscache', 'optional:tag1'], count=1)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.CRITICAL,
                                    tags=['service:NonExistentService', 'optional:tag1'], count=1)


def test_wildcard(aggregator, check, instance_wildcard):
    check.check(instance_wildcard)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:EventLog'], count=1)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:EventSystem'], count=1)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:Dnscache'], count=1)


def test_all(aggregator, check, instance_all):
    check.check(instance_all)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:EventLog'], count=1)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:Dnscache'], count=1)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=check.OK,
                                    tags=['service:EventSystem'], count=1)
