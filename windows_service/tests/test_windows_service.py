# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import pywintypes
from mock import patch

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
        status=c.UNKNOWN,
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


def test_startup_type_filter_automatic(aggregator, check, instance_startup_type_filter):
    instance_startup_type_filter['services'] = [
        {'startup_type': 'automatic'},
    ]
    c = check(instance_startup_type_filter)
    c.check(instance_startup_type_filter)

    # Make sure we got at least one
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, at_least=1)
    # Assert all found were automatic
    for sc in aggregator.service_checks(c.SERVICE_CHECK_NAME):
        assert 'windows_service_startup_type:automatic' in sc.tags


def test_startup_type_filter_automatic_and_delayed(aggregator, check, instance_startup_type_filter):
    instance_startup_type_filter['services'] = [
        {'startup_type': 'automatic'},
        {'startup_type': 'automatic_delayed_start'},
    ]
    c = check(instance_startup_type_filter)
    c.check(instance_startup_type_filter)

    # Make sure we got at least one
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, at_least=1)
    # Assert all found were automatic or delayed
    for sc in aggregator.service_checks(c.SERVICE_CHECK_NAME):
        assert (
            'windows_service_startup_type:automatic' in sc.tags
            or 'windows_service_startup_type:automatic_delayed_start' in sc.tags
        )


def test_name_dict_basic(aggregator, check, instance_basic_dict):
    c = check(instance_basic_dict)
    c.check(instance_basic_dict)

    # Check count
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, count=2)
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.UNKNOWN, count=1)
    # Check details
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.OK,
        tags=['windows_service:EventLog', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.OK,
        tags=['windows_service:Dnscache', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.UNKNOWN,
        tags=['windows_service:NonExistentService', 'optional:tag1'],
        count=1,
    )


def test_name_dict_wildcard_with_wmi_compat(aggregator, check, instance_wildcard_dict):
    c = check(instance_wildcard_dict)
    c.check(instance_wildcard_dict)

    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:EventLog'], count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:EventSystem'], count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:Dnscache'], count=1)


def test_startup_type_filter_name_dict_wildcard_without_wmi_compat(aggregator, check, instance_wildcard_dict):
    del instance_wildcard_dict['host']

    c = check(instance_wildcard_dict)
    c.check(instance_wildcard_dict)

    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:EventLog'], count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:EventSystem'], count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:Dnscache'], count=0)


def test_startup_type_filter_automatic_single_without_tag(aggregator, check, instance_startup_type_filter):
    instance_startup_type_filter['services'] = [
        {
            'startup_type': 'automatic',
            'name': 'EventLog',
        },
    ]
    instance_startup_type_filter['windows_service_startup_type_tag'] = False

    c = check(instance_startup_type_filter)
    c.check(instance_startup_type_filter)

    # Make sure we got exactly one
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_NAME, status=c.OK, tags=['windows_service:EventLog'], count=1)


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
        c.SERVICE_CHECK_NAME, status=c.UNKNOWN, tags=['windows_service:NonExistentService', 'optional:tag1'], count=1
    )


def test_startup_type_tag(aggregator, check, instance_basic):
    instance_basic['windows_service_startup_type_tag'] = True
    c = check(instance_basic)
    c.check(instance_basic)
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.OK,
        tags=[
            'service:EventLog',
            'windows_service:EventLog',
            'windows_service_startup_type:automatic',
            'optional:tag1',
        ],
        count=1,
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.OK,
        tags=[
            'service:Dnscache',
            'windows_service:Dnscache',
            'windows_service_startup_type:automatic',
            'optional:tag1',
        ],
        count=1,
    )
    aggregator.assert_service_check(
        c.SERVICE_CHECK_NAME,
        status=c.UNKNOWN,
        tags=[
            'service:NonExistentService',
            'windows_service:NonExistentService',
            'windows_service_startup_type:unknown',
            'optional:tag1',
        ],
        count=1,
    )


def test_openservice_failure(aggregator, check, instance_basic_dict, caplog):
    # dict type
    instance_basic_dict['services'].append({'startup_type': 'automatic'})
    # str type
    instance_basic_dict['services'].append('EventLog')

    instance_basic_dict['windows_service_startup_type_tag'] = True
    c = check(instance_basic_dict)

    with patch('win32service.OpenService', side_effect=pywintypes.error('mocked error')):
        c.check(instance_basic_dict)

    assert 'Failed to query EventLog service config' in caplog.text


def test_invalid_pattern_type(aggregator, check, instance_basic_dict):
    # Array is not valid type
    instance_basic_dict['services'].append(
        ['foo'],
    )

    instance_basic_dict['windows_service_startup_type_tag'] = True
    c = check(instance_basic_dict)

    with pytest.raises(Exception, match="Invalid type 'list' for service"):
        c.check(instance_basic_dict)


def test_invalid_pattern_regex(aggregator, check, instance_basic_dict):
    instance_basic_dict['services'].append('(foo')

    instance_basic_dict['windows_service_startup_type_tag'] = True
    c = check(instance_basic_dict)

    with pytest.raises(Exception, match=r"Regular expression syntax error in '\(foo':"):
        c.check(instance_basic_dict)


@pytest.mark.e2e
def test_basic_e2e(dd_agent_check, check, instance_basic):
    aggregator = dd_agent_check(instance_basic)

    aggregator.assert_service_check(
        WindowsService.SERVICE_CHECK_NAME,
        status=WindowsService.OK,
        tags=['service:EventLog', 'windows_service:EventLog', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_service_check(
        WindowsService.SERVICE_CHECK_NAME,
        status=WindowsService.OK,
        tags=['service:Dnscache', 'windows_service:Dnscache', 'optional:tag1'],
        count=1,
    )
    aggregator.assert_service_check(
        WindowsService.SERVICE_CHECK_NAME,
        status=WindowsService.UNKNOWN,
        tags=['service:NonExistentService', 'windows_service:NonExistentService', 'optional:tag1'],
        count=1,
    )
