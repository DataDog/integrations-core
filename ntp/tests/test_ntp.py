# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ntplib
import mock
import pytest
from datadog_checks.ntp import NtpCheck


@pytest.fixture
def instance():
    return {
        'host': 'foo.com',
        'version': 42,
        'timeout': 13.37,
        'tags': ['mytag'],
    }


@pytest.fixture
def check():
    """
    This check only works in Agent v5 with the old
    AgentCheck api so we mock it
    """
    c = NtpCheck('ntp', {}, {})
    c.gauge = mock.MagicMock()
    c.service_check = mock.MagicMock()
    return c


@pytest.fixture
def ntp_client():
    request = mock.MagicMock()
    request.return_value = mock.MagicMock(offset=1042, recv_time=4242)
    return mock.MagicMock(request=request)


def test_defaults(check, ntp_client):
    """
    Test what was sent to the NTP client when the config file is empty
    """
    with mock.patch('datadog_checks.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        check.check({})
        args, kwargs = ntp_client.request.call_args
        assert '.datadog.pool.ntp.org' in kwargs.get('host', '')
        assert kwargs.get('port') == 'ntp'
        assert kwargs.get('timeout') == 1.0
        assert kwargs.get('version') == 3
        check.gauge.assert_called_once_with('ntp.offset', 1042, tags=[], timestamp=4242)


def test_instance(check, ntp_client, instance):
    """
    Test what was sent to the NTP client when config was passed
    """
    instance['port'] = 'Boo!'
    with mock.patch('datadog_checks.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        check.check(instance)
        args, kwargs = ntp_client.request.call_args
        assert 'foo.com' in kwargs.get('host', '')
        assert kwargs.get('port') == 123
        assert kwargs.get('timeout') == 13.37
        assert kwargs.get('version') == 42
        check.gauge.assert_called_once_with('ntp.offset', 1042, tags=['mytag'], timestamp=4242)


def test_wrong_config(check, instance):
    """
    Test wrong config values are spotted
    """
    instance['offset_threshold'] = 'foo'
    with pytest.raises(Exception) as e:
        check.check(instance)
        assert 'Must specify an integer value for offset_threshold' in e


def test_service_check_unknown(check, ntp_client, instance):
    """
    Test the UNKNOWN service check is sent
    """
    with mock.patch('datadog_checks.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        ntp_client.request.side_effect = ntplib.NTPException
        check.check(instance)
        check.service_check.assert_called_once_with('ntp.in_sync', NtpCheck.UNKNOWN,
                                                    message=None, tags=['mytag'], timestamp=None)


def test_service_check_ok(check, ntp_client, instance):
    """
    Test the OK service check is sent
    """
    instance['offset_threshold'] = 2048
    with mock.patch('datadog_checks.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        check.check(instance)
        check.service_check.assert_called_once_with('ntp.in_sync', NtpCheck.OK,
                                                    message=None, tags=['mytag'], timestamp=4242)


def test_service_check_ko(check, ntp_client, instance):
    """
    Test the OK service check is sent
    """
    with mock.patch('datadog_checks.ntp.ntp.ntplib.NTPClient') as c:
        c.return_value = ntp_client
        check.check(instance)
        check.service_check.assert_called_once_with('ntp.in_sync', NtpCheck.CRITICAL,
                                                    message='Offset 1042 secs higher than offset threshold (60 secs)',
                                                    tags=['mytag'], timestamp=4242)


def test__get_service_port(check, instance):
    """
    Test the fallback procedure to get the service port
    """
    assert check._get_service_port(instance) == 'ntp'
    instance['port'] = 'foo'
    assert check._get_service_port(instance) == 123
