# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ctypes

import pytest
import pywintypes
import win32service
import winerror
from mock import patch

from datadog_checks.windows_service import WindowsService


class Service:
    def __init__(self, name, state, extra_tags=None, count=1):
        self.name = name
        self.check_status = WindowsService.STATE_TO_STATUS.get(state, WindowsService.UNKNOWN)
        self.tags = [
            f'windows_service:{name}',
            f'windows_service_state:{WindowsService.STATE_TO_STRING.get(state, WindowsService.UNKNOWN_LITERAL)}',
        ] + (extra_tags or [])
        self.count = count


def assert_service_check_and_metrics(aggregator, services):
    for service in services:
        aggregator.assert_service_check(
            WindowsService.SERVICE_CHECK_NAME,
            status=service.check_status,
            tags=service.tags,
            count=service.count,
        )
        aggregator.assert_metric(
            'windows_service.uptime',
            tags=service.tags,
            count=service.count,
        )
        aggregator.assert_metric(
            'windows_service.state',
            tags=service.tags,
            value=1,
            count=service.count,
        )
        aggregator.assert_metric(
            'windows_service.restarts',
            tags=service.tags,
            value=0,
            count=service.count,
        )


def test_bad_config(check, instance_bad_config):
    c = check(instance_bad_config)
    with pytest.raises(ValueError):
        c.check(instance_bad_config)


def test_basic(aggregator, check, instance_basic):
    c = check(instance_basic)
    c.check(instance_basic)
    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog', 'optional:tag1']),
        Service('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache', 'optional:tag1']),
        Service('NonExistentService', -1, extra_tags=['service:NonExistentService', 'optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_wildcard(aggregator, check, instance_wildcard):
    c = check(instance_wildcard)
    c.check(instance_wildcard)
    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog']),
        Service('EventSystem', win32service.SERVICE_RUNNING, extra_tags=['service:EventSystem']),
        Service('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_all(aggregator, check, instance_all):
    c = check(instance_all)
    c.check(instance_all)
    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog']),
        Service('EventSystem', win32service.SERVICE_RUNNING, extra_tags=['service:EventSystem']),
        Service('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache']),
    ]
    assert_service_check_and_metrics(aggregator, services)
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
    # Assert uptime metrics were sent
    aggregator.assert_metric('windows_service.uptime', at_least=1)


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
    # Assert uptime metrics were sent
    aggregator.assert_metric('windows_service.uptime', at_least=1)


def test_name_dict_basic(aggregator, check, instance_basic_dict):
    c = check(instance_basic_dict)
    c.check(instance_basic_dict)

    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        Service('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        Service('NonExistentService', -1, extra_tags=['optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_name_dict_wildcard_with_wmi_compat(aggregator, check, instance_wildcard_dict):
    c = check(instance_wildcard_dict)
    c.check(instance_wildcard_dict)

    services = [
        Service('EventLog', win32service.SERVICE_RUNNING),
        Service('EventSystem', win32service.SERVICE_RUNNING),
        Service('Dnscache', win32service.SERVICE_RUNNING),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_startup_type_filter_name_dict_wildcard_without_wmi_compat(aggregator, check, instance_wildcard_dict):
    del instance_wildcard_dict['host']

    c = check(instance_wildcard_dict)
    c.check(instance_wildcard_dict)

    services = [
        Service('EventLog', win32service.SERVICE_RUNNING),
        Service('EventSystem', win32service.SERVICE_RUNNING),
        Service('Dnscache', -1, count=0),
    ]
    assert_service_check_and_metrics(aggregator, services)


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

    services = [
        Service('EventLog', win32service.SERVICE_RUNNING),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_basic_disable_service_tag(aggregator, check, instance_basic_disable_service_tag):
    c = check(instance_basic_disable_service_tag)
    c.check(instance_basic_disable_service_tag)
    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        Service('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        Service('NonExistentService', -1, extra_tags=['optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_startup_type_tag(aggregator, check, instance_basic):
    instance_basic['windows_service_startup_type_tag'] = True
    c = check(instance_basic)
    c.check(instance_basic)
    services = [
        Service(
            'EventLog',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:EventLog', 'windows_service_startup_type:automatic', 'optional:tag1'],
            count=1,
        ),
        Service(
            'Dnscache',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:Dnscache', 'windows_service_startup_type:automatic', 'optional:tag1'],
            count=1,
        ),
        Service(
            'NonExistentService',
            -1,
            extra_tags=['service:NonExistentService', 'windows_service_startup_type:unknown', 'optional:tag1'],
            count=1,
        ),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_display_name_tag(aggregator, check, instance_basic):
    instance_basic['collect_display_name_as_tag'] = True
    c = check(instance_basic)
    c.check(instance_basic)
    services = [
        Service(
            'EventLog',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:EventLog', 'display_name:Windows Event Log', 'optional:tag1'],
            count=1,
        ),
        Service(
            'Dnscache',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:Dnscache', 'display_name:DNS Client', 'optional:tag1'],
            count=1,
        ),
        Service(
            'NonExistentService',
            -1,
            extra_tags=['service:NonExistentService', 'display_name:Not_Found', 'optional:tag1'],
            count=1,
        ),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_openservice_failure(aggregator, check, instance_basic_dict, caplog):
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


def test_trigger_start(aggregator, check, instance_trigger_start):
    c = check(instance_trigger_start)
    c.check(instance_trigger_start)
    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        Service('dnscache', -1, extra_tags=['optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_trigger_count_failure(aggregator, check, instance_trigger_start, caplog):
    c = check(instance_trigger_start)

    with patch(
        'datadog_checks.windows_service.windows_service.QueryServiceConfig2W',
        side_effect=[ctypes.WinError(winerror.ERROR_INSUFFICIENT_BUFFER), ctypes.WinError(1)] * 2,
    ):
        c.check(instance_trigger_start)

    assert 'OSError: [WinError 1] Incorrect function' in caplog.text


def test_name_regex_order(aggregator, check, instance_name_regex_prefix):
    """
    This helps us check that we handle an issue that results from configs like the following
    services:
        - foobar
        - foobarbaz
    Since the name regex is executed as a PREFIX match, `foobar` will match for both `foobar` and `foobarbaz`.
    This sends a status metric for both/all services that match.
    Since the service patterns are "first come first serve", now `foobarbaz` pattern does not match
    any of the remaining services, and will report UNKNOWN.
    Sorting in reverse order puts the more specific (longer) prefix first.
    See https://github.com/DataDog/integrations-core/pull/4503
    """
    c = check(instance_name_regex_prefix)
    c.check(instance_name_regex_prefix)

    services = [
        # More specific names should match
        Service('EventLog', win32service.SERVICE_RUNNING),
        Service('EventSystem', win32service.SERVICE_RUNNING),
        # The prefix match should go unmatched, even though it is listed first in the config
        Service('event', -1, count=1),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_service_restart_detection(aggregator, check, instance_basic):
    """
    Test that service restarts are detected when the service PID changes between checks.
    """
    c = check(instance_basic)

    mock_services = [
        {
            'ServiceName': 'EventLog',
            'DisplayName': 'Windows Event Log',
            'CurrentState': win32service.SERVICE_RUNNING,
            'ProcessId': 1234,
        },
        {
            'ServiceName': 'Dnscache',
            'DisplayName': 'DNS Client',
            'CurrentState': win32service.SERVICE_RUNNING,
            'ProcessId': 5678,
        },
    ]

    with patch('win32service.EnumServicesStatusEx', return_value=mock_services):
        c.check(instance_basic)

    # On first check, restarts should be 0
    aggregator.assert_metric(
        'windows_service.restarts',
        value=0,
        tags=['windows_service:EventLog', 'windows_service_state:running', 'service:EventLog', 'optional:tag1'],
    )
    aggregator.assert_metric(
        'windows_service.restarts',
        value=0,
        tags=['windows_service:Dnscache', 'windows_service_state:running', 'service:Dnscache', 'optional:tag1'],
    )

    aggregator.reset()

    # Only change the PID of EventLog
    mock_services[0]['ProcessId'] = 9999

    with patch('win32service.EnumServicesStatusEx', return_value=mock_services):
        c.check(instance_basic)

    # On second check, EventLog should have restarts=1
    aggregator.assert_metric(
        'windows_service.restarts',
        value=1,
        tags=['windows_service:EventLog', 'windows_service_state:running', 'service:EventLog', 'optional:tag1'],
    )
    # Dnscache should still have restarts=0
    aggregator.assert_metric(
        'windows_service.restarts',
        value=0,
        tags=['windows_service:Dnscache', 'windows_service_state:running', 'service:Dnscache', 'optional:tag1'],
    )


@pytest.mark.e2e
def test_basic_e2e(dd_agent_check, check, instance_basic):
    aggregator = dd_agent_check(instance_basic)

    services = [
        Service('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog', 'optional:tag1']),
        Service('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache', 'optional:tag1']),
        Service('NonExistentService', -1, extra_tags=['service:NonExistentService', 'optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)
