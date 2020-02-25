# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.windows_service import WindowsService


def test_bad_config(check, instance_bad_config):
    c = check(instance_bad_config)
    with pytest.raises(ValueError):
        c.check(instance_bad_config)


def test_basic(aggregator, check, instance_basic):
    c = check(instance_basic)
    c.check(instance_basic)
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.OK,
        tags=['service:EventLog', 'windows_service:EventLog', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.OK,
        tags=['service:Dnscache', 'windows_service:Dnscache', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.CRITICAL,
        tags=['service:NonExistentService', 'windows_service:NonExistentService', 'optional:tag1'],
        count=1,
    )


def test_wildcard(aggregator, check, instance_wildcard):
    c = check(instance_wildcard)
    c.check(instance_wildcard)
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['service:EventLog', 'windows_service:EventLog'], count=1
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['service:EventSystem', 'windows_service:EventSystem'], count=1
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['service:Dnscache', 'windows_service:Dnscache'], count=1
    )


def test_all(aggregator, check, instance_all):
    c = check(instance_all)
    c.check(instance_all)
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['service:EventLog', 'windows_service:EventLog'], count=1
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['service:Dnscache', 'windows_service:Dnscache'], count=1
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['service:EventSystem', 'windows_service:EventSystem'], count=1
    )
    msg = 'The `service` tag is deprecated and has been renamed to `windows_service`'
    assert msg in c.warnings[0]


def test_basic_disable_service_tag(aggregator, check, instance_basic_disable_service_tag):
    c = check(instance_basic_disable_service_tag)
    c.check(instance_basic_disable_service_tag)
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:EventLog', 'optional:tag1'], count=1
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:Dnscache', 'optional:tag1'], count=1
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME, status=c.CRITICAL, tags=['windows_service:NonExistentService', 'optional:tag1'], count=1
    )


@pytest.mark.e2e
def test_basic_e2e(dd_agent_check, check, instance_basic):
    aggregator = dd_agent_check(instance_basic)

    aggregator.assert_service_check(
        WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK, tags=['service:EventLog', 'optional:tag1'], count=1
    )
    aggregator.assert_service_check(
        WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK, tags=['service:Dnscache', 'optional:tag1'], count=1
    )
    aggregator.assert_service_check(
        WindowsService.SERVICE_CHECK_NAME,
        status=WindowsService.CRITICAL,
        tags=['service:NonExistentService', 'windows_service:NonExistentService', 'optional:tag1'],
        count=1,
    )
