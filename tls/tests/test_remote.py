# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from six import PY2

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.testing import requires_py3
from datadog_checks.tls.const import (
    SERVICE_CHECK_CAN_CONNECT,
    SERVICE_CHECK_EXPIRATION,
    SERVICE_CHECK_VALIDATION,
    SERVICE_CHECK_VERSION,
)
from datadog_checks.tls.tls import TLSCheck
from datadog_checks.tls.tls_remote import TLSRemoteCheck

try:
    from unittest.mock import MagicMock, patch
except ImportError:  # Python 2
    from mock import MagicMock, patch


def test_right_class_is_instantiated(instance_remote_no_server):
    c = TLSCheck('tls', {}, [instance_remote_no_server])
    assert isinstance(c.checker, TLSRemoteCheck)


def test_no_server(instance_remote_no_server):
    c = TLSCheck('tls', {}, [instance_remote_no_server])

    with pytest.raises(ConfigurationError):
        c.check(None)


def test_ok(aggregator, instance_remote_ok):
    c = TLSCheck('tls', {}, [instance_remote_ok])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_ok_ip(aggregator, instance_remote_ok_ip):
    c = TLSCheck('tls', {}, [instance_remote_ok_ip])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_ok_udp(aggregator, instance_remote_ok_udp):
    c = TLSCheck('tls', {}, [instance_remote_ok_udp])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_no_resolve(aggregator, instance_remote_no_resolve):
    c = TLSCheck('tls', {}, [instance_remote_no_resolve])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    message = 'Unable to resolve host, check your DNS'
    assert message in aggregator.service_checks(SERVICE_CHECK_CAN_CONNECT)[0].message

    aggregator.assert_all_metrics_covered()


def test_no_connect(aggregator, instance_remote_no_connect):
    c = TLSCheck('tls', {}, [instance_remote_no_connect])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    message = 'Unable to resolve host, check your DNS'
    assert message not in aggregator.service_checks(SERVICE_CHECK_CAN_CONNECT)[0].message

    aggregator.assert_all_metrics_covered()


def test_no_connect_port_in_host(aggregator, instance_remote_no_connect_port_in_host):
    c = TLSCheck('tls', {}, [instance_remote_no_connect_port_in_host])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    message = 'Unable to resolve host, check your DNS'
    assert message not in aggregator.service_checks(SERVICE_CHECK_CAN_CONNECT)[0].message

    aggregator.assert_all_metrics_covered()


def test_no_connect_ipv6(aggregator, instance_remote_no_connect):
    c = TLSCheck('tls', {}, [instance_remote_no_connect])
    with mock.patch('socket.getaddrinfo', return_value=()):
        c.check(None)

    aggregator.assert_service_check(
        SERVICE_CHECK_CAN_CONNECT,
        status=c.CRITICAL,
        tags=c._tags,
        message='No valid addresses found, try checking your IPv6 connectivity',
        count=1,
    )
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    aggregator.assert_all_metrics_covered()


def test_version_default_1_2(aggregator, instance_remote_version_default_1_2):
    c = TLSCheck('tls', {}, [instance_remote_version_default_1_2])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_version_default_1_3(aggregator, instance_remote_version_default_1_3):
    c = TLSCheck('tls', {}, [instance_remote_version_default_1_3])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_version_init_config_default(aggregator, instance_remote_version_default_1_2):
    c = TLSCheck('tls', {'allowed_versions': ['1.2']}, [instance_remote_version_default_1_2])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_hostname_mismatch(aggregator, instance_remote_hostname_mismatch):
    c = TLSCheck('tls', {}, [instance_remote_hostname_mismatch])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_self_signed_ok(aggregator, instance_remote_self_signed_ok):
    c = TLSCheck('tls', {}, [instance_remote_self_signed_ok])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_expired(aggregator, instance_remote_cert_expired):
    c = TLSCheck('tls', {}, [instance_remote_cert_expired])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    if PY2:
        aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
        aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)
    else:
        aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
        aggregator.assert_service_check(
            SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, message='Certificate has expired', count=1
        )

    aggregator.assert_all_metrics_covered()


@pytest.mark.skip(reason="expired certified, reactivate test when certified valid again")
def test_fetch_intermediate_certs(aggregator, instance_remote_fetch_intermediate_certs):
    c = TLSCheck('tls', {}, [instance_remote_fetch_intermediate_certs])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_send_cert_duration(aggregator, instance_remote_send_cert_duration):
    c = TLSCheck('tls', {}, [instance_remote_send_cert_duration])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_metric('tls.issued_days', count=1)
    aggregator.assert_metric('tls.issued_seconds', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_critical_days(aggregator, instance_remote_cert_critical_days):
    c = TLSCheck('tls', {}, [instance_remote_cert_critical_days])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_critical_seconds(aggregator, instance_remote_cert_critical_seconds):
    c = TLSCheck('tls', {}, [instance_remote_cert_critical_seconds])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_warning_days(aggregator, instance_remote_cert_warning_days):
    c = TLSCheck('tls', {}, [instance_remote_cert_warning_days])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.WARNING, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_warning_seconds(aggregator, instance_remote_cert_warning_seconds):
    c = TLSCheck('tls', {}, [instance_remote_cert_warning_seconds])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.WARNING, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_postgres_ok(aggregator, instance_remote_postgresql_valid):
    c = TLSCheck('tls', {}, [instance_remote_postgresql_valid])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_mysql_ok(aggregator, instance_remote_mysql_valid):
    c = TLSCheck('tls', {}, [instance_remote_mysql_valid])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


@requires_py3
def test_valid_version_with_critical_certificate_validation_and_critial_certificate_expiration(
    aggregator, instance_remote_ok
):
    from ssl import SSLCertVerificationError

    c = TLSCheck('tls', {}, [instance_remote_ok])
    check = TLSRemoteCheck(agent_check=c)
    with patch.object(check.agent_check, 'get_tls_context') as mock_get_tls_context:
        mock_tls_context = MagicMock()
        mock_get_tls_context.return_value = mock_tls_context

        with patch.object(mock_tls_context, 'wrap_socket') as mock_wrap_socket:
            mock_wrap_socket.return_value.__enter__.return_value.version.return_value = 'TLSv1.2'
            ssl_exception = SSLCertVerificationError()
            ssl_exception.verify_code = 10
            ssl_exception.verify_message = 'Test exception with error code 10'
            mock_wrap_socket.return_value.__enter__.return_value.getpeercert.side_effect = ssl_exception
            c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(
        SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1, message='Test exception with error code 10'
    )
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(
        SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, message='Certificate has expired', count=1
    )

    aggregator.assert_all_metrics_covered()


@requires_py3
def test_valid_version_and_critical_certificate_validation_due_to_socket_exception(aggregator, instance_remote_ok):
    c = TLSCheck('tls', {}, [instance_remote_ok])
    check = TLSRemoteCheck(agent_check=c)
    with patch.object(check.agent_check, 'get_tls_context') as mock_get_tls_context:
        mock_tls_context = MagicMock()
        mock_get_tls_context.return_value = mock_tls_context

        with patch.object(mock_tls_context, 'wrap_socket') as mock_wrap_socket:
            mock_wrap_socket.return_value.__enter__.return_value.version.return_value = 'TLSv1.2'
            mock_wrap_socket.return_value.__enter__.return_value.getpeercert.side_effect = Exception(
                'Exception with secure_sock.getpeercert(binary_form=True)'
            )
            c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(
        SERVICE_CHECK_VALIDATION,
        status=c.CRITICAL,
        tags=c._tags,
        count=1,
        message='Exception with secure_sock.getpeercert(binary_form=True)',
    )
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    aggregator.assert_all_metrics_covered()


@requires_py3
def test_valid_version_and_critical_certificate_validation_due_to_parsing_error(aggregator, instance_remote_ok):
    c = TLSCheck('tls', {}, [instance_remote_ok])
    check = TLSRemoteCheck(agent_check=c)
    with patch.object(check.agent_check, 'get_tls_context') as mock_get_tls_context:
        mock_tls_context = MagicMock()
        mock_get_tls_context.return_value = mock_tls_context

        with patch.object(mock_tls_context, 'wrap_socket') as mock_wrap_socket:
            mock_wrap_socket.return_value.__enter__.return_value.version.return_value = 'TLSv1.2'
            mock_wrap_socket.return_value.getpeercert.side_effect = Exception('Test exception')
            c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(
        SERVICE_CHECK_VALIDATION,
        status=c.CRITICAL,
        tags=c._tags,
        count=1,
        message="Unable to parse the certificate: argument 'data': 'MagicMock' object cannot be converted to 'PyBytes'",
    )
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    aggregator.assert_all_metrics_covered()
