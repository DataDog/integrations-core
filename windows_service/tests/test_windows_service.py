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


class ServiceAssertion:
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
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog', 'optional:tag1']),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache', 'optional:tag1']),
        ServiceAssertion('NonExistentService', -1, extra_tags=['service:NonExistentService', 'optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_wildcard(aggregator, check, instance_wildcard):
    c = check(instance_wildcard)
    c.check(instance_wildcard)
    services = [
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog']),
        ServiceAssertion('EventSystem', win32service.SERVICE_RUNNING, extra_tags=['service:EventSystem']),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_all(aggregator, check, instance_all):
    c = check(instance_all)
    c.check(instance_all)
    services = [
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog']),
        ServiceAssertion('EventSystem', win32service.SERVICE_RUNNING, extra_tags=['service:EventSystem']),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache']),
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
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        ServiceAssertion('NonExistentService', -1, extra_tags=['optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_name_dict_wildcard_with_wmi_compat(aggregator, check, instance_wildcard_dict):
    c = check(instance_wildcard_dict)
    c.check(instance_wildcard_dict)

    services = [
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING),
        ServiceAssertion('EventSystem', win32service.SERVICE_RUNNING),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_startup_type_filter_name_dict_wildcard_without_wmi_compat(aggregator, check, instance_wildcard_dict):
    del instance_wildcard_dict['host']

    c = check(instance_wildcard_dict)
    c.check(instance_wildcard_dict)

    services = [
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING),
        ServiceAssertion('EventSystem', win32service.SERVICE_RUNNING),
        ServiceAssertion('Dnscache', -1, count=0),
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
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_basic_disable_service_tag(aggregator, check, instance_basic_disable_service_tag):
    c = check(instance_basic_disable_service_tag)
    c.check(instance_basic_disable_service_tag)
    services = [
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        ServiceAssertion('NonExistentService', -1, extra_tags=['optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_startup_type_tag(aggregator, check, instance_basic):
    instance_basic['windows_service_startup_type_tag'] = True
    c = check(instance_basic)
    c.check(instance_basic)
    services = [
        ServiceAssertion(
            'EventLog',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:EventLog', 'windows_service_startup_type:automatic', 'optional:tag1'],
            count=1,
        ),
        ServiceAssertion(
            'Dnscache',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:Dnscache', 'windows_service_startup_type:automatic', 'optional:tag1'],
            count=1,
        ),
        ServiceAssertion(
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
        ServiceAssertion(
            'EventLog',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:EventLog', 'display_name:Windows Event Log', 'optional:tag1'],
            count=1,
        ),
        ServiceAssertion(
            'Dnscache',
            win32service.SERVICE_RUNNING,
            extra_tags=['service:Dnscache', 'display_name:DNS Client', 'optional:tag1'],
            count=1,
        ),
        ServiceAssertion(
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
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['optional:tag1']),
        ServiceAssertion('dnscache', -1, extra_tags=['optional:tag1']),
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
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING),
        ServiceAssertion('EventSystem', win32service.SERVICE_RUNNING),
        # The prefix match should go unmatched, even though it is listed first in the config
        ServiceAssertion('event', -1, count=1),
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


# Per-user service instances carry SERVICE_USER_OWN_PROCESS (0x50) plus the
# SERVICE_USERSERVICE_INSTANCE flag (0x80). Templates (not enumerated) lack the 0x80 bit.
USER_SERVICE_INSTANCE_TYPE = 0x10 | 0x40 | 0x80
WIN32_OWN_PROCESS_TYPE = 0x10


def _per_user_mock_services():
    return [
        {
            'ServiceName': 'OneSyncSvc_443f50',
            'DisplayName': 'Sync Host_443f50',
            'CurrentState': win32service.SERVICE_RUNNING,
            'ProcessId': 1234,
            'ServiceType': USER_SERVICE_INSTANCE_TYPE,
        },
        {
            'ServiceName': 'OneSyncSvc_18f113',
            'DisplayName': 'Sync Host_18f113',
            'CurrentState': win32service.SERVICE_RUNNING,
            'ProcessId': 5678,
            'ServiceType': USER_SERVICE_INSTANCE_TYPE,
        },
        {
            'ServiceName': 'Dnscache',
            'DisplayName': 'DNS Client',
            'CurrentState': win32service.SERVICE_RUNNING,
            'ProcessId': 9999,
            'ServiceType': WIN32_OWN_PROCESS_TYPE,
        },
    ]


def test_group_per_user_services(aggregator, check, instance_group_per_user_services):
    c = check(instance_group_per_user_services)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance_group_per_user_services)

    services = [
        # Both per-user instances collapse to the template name, so the grouped tag is submitted twice
        ServiceAssertion('OneSyncSvc', win32service.SERVICE_RUNNING, extra_tags=['display_name:Sync Host'], count=2),
        # The LUID-suffixed names must no longer be emitted
        ServiceAssertion('OneSyncSvc_443f50', win32service.SERVICE_RUNNING, count=0),
        ServiceAssertion('OneSyncSvc_18f113', win32service.SERVICE_RUNNING, count=0),
        # Non per-user services are untouched
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['display_name:DNS Client']),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_group_per_user_services_disabled(aggregator, check, instance_group_per_user_services):
    instance_group_per_user_services['group_per_user_services'] = False
    c = check(instance_group_per_user_services)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance_group_per_user_services)

    services = [
        # Without grouping each instance keeps its full LUID-suffixed name
        ServiceAssertion(
            'OneSyncSvc_443f50', win32service.SERVICE_RUNNING, extra_tags=['display_name:Sync Host_443f50']
        ),
        ServiceAssertion(
            'OneSyncSvc_18f113', win32service.SERVICE_RUNNING, extra_tags=['display_name:Sync Host_18f113']
        ),
        # The grouped template name is not emitted
        ServiceAssertion('OneSyncSvc', win32service.SERVICE_RUNNING, count=0),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_group_per_user_services_ignores_non_user_service(aggregator, check, instance_group_per_user_services):
    # A regular service whose name happens to end in _<hex> must not be stripped: it lacks the
    # SERVICE_USERSERVICE_INSTANCE flag.
    mock_services = [
        {
            'ServiceName': 'MyService_abc123',
            'DisplayName': 'My Service_abc123',
            'CurrentState': win32service.SERVICE_RUNNING,
            'ProcessId': 4242,
            'ServiceType': WIN32_OWN_PROCESS_TYPE,
        },
    ]
    c = check(instance_group_per_user_services)

    with patch('win32service.EnumServicesStatusEx', return_value=mock_services):
        c.check(instance_group_per_user_services)

    services = [
        ServiceAssertion(
            'MyService_abc123', win32service.SERVICE_RUNNING, extra_tags=['display_name:My Service_abc123']
        ),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_group_per_user_services_with_name_filter(aggregator, check, instance_group_per_user_services):
    # Grouping must also apply when services are selected by a name filter (not just ALL). The
    # prefix regex matches the full LUID-suffixed instance names, but the emitted tag is grouped.
    instance_group_per_user_services['services'] = ['OneSyncSvc']

    c = check(instance_group_per_user_services)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance_group_per_user_services)

    services = [
        ServiceAssertion('OneSyncSvc', win32service.SERVICE_RUNNING, extra_tags=['display_name:Sync Host'], count=2),
        # The grouped template name must not be reported UNKNOWN by the services_unseen path
        ServiceAssertion('OneSyncSvc', -1, count=0),
        # The non-matching service is not reported
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, count=0),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_per_user_false_excludes_per_user_services(aggregator, check):
    # `per_user: false` collects only non-per-user services, so per-user instances are dropped.
    instance = {'services': [{'per_user': False}], 'disable_legacy_service_tag': True}
    c = check(instance)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance)

    services = [
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING),
        ServiceAssertion('OneSyncSvc_443f50', win32service.SERVICE_RUNNING, count=0),
        ServiceAssertion('OneSyncSvc_18f113', win32service.SERVICE_RUNNING, count=0),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_per_user_true_collects_only_per_user_services(aggregator, check):
    instance = {'services': [{'per_user': True}], 'disable_legacy_service_tag': True}
    c = check(instance)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance)

    services = [
        ServiceAssertion('OneSyncSvc_443f50', win32service.SERVICE_RUNNING),
        ServiceAssertion('OneSyncSvc_18f113', win32service.SERVICE_RUNNING),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, count=0),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_per_user_composes_with_name_filter(aggregator, check):
    # A name filter that matches the per-user instances but is gated to non-per-user collects nothing.
    instance = {'services': [{'name': 'OneSyncSvc', 'per_user': False}], 'disable_legacy_service_tag': True}
    c = check(instance)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance)

    services = [
        ServiceAssertion('OneSyncSvc_443f50', win32service.SERVICE_RUNNING, count=0),
        ServiceAssertion('OneSyncSvc_18f113', win32service.SERVICE_RUNNING, count=0),
        # The named filter still goes unmatched and reports UNKNOWN once.
        ServiceAssertion('OneSyncSvc', -1, count=1),
    ]
    assert_service_check_and_metrics(aggregator, services)


def test_per_user_false_with_grouping_warns(aggregator, check):
    instance = {
        'services': [{'per_user': False}],
        'group_per_user_services': True,
        'disable_legacy_service_tag': True,
    }
    c = check(instance)

    with patch('win32service.EnumServicesStatusEx', return_value=_per_user_mock_services()):
        c.check(instance)

    assert any('will not be grouped' in w for w in c.warnings)


@pytest.mark.e2e
def test_basic_e2e(dd_agent_check, check, instance_basic):
    aggregator = dd_agent_check(instance_basic)

    services = [
        ServiceAssertion('EventLog', win32service.SERVICE_RUNNING, extra_tags=['service:EventLog', 'optional:tag1']),
        ServiceAssertion('Dnscache', win32service.SERVICE_RUNNING, extra_tags=['service:Dnscache', 'optional:tag1']),
        ServiceAssertion('NonExistentService', -1, extra_tags=['service:NonExistentService', 'optional:tag1']),
    ]
    assert_service_check_and_metrics(aggregator, services)
