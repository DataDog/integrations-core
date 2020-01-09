# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from six import PY2

from datadog_checks.base import ConfigurationError
from datadog_checks.tls import TLSCheck


def test_no_server(instance_remote_no_server):
    c = TLSCheck('tls', {}, [instance_remote_no_server])

    with pytest.raises(ConfigurationError):
        c.check(None)


def test_ok(aggregator, instance_remote_ok):
    c = TLSCheck('tls', {}, [instance_remote_ok])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_ok_ip(aggregator, instance_remote_ok_ip):
    c = TLSCheck('tls', {}, [instance_remote_ok_ip])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_ok_udp(aggregator, instance_remote_ok_udp):
    c = TLSCheck('tls', {}, [instance_remote_ok_udp])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_no_resolve(aggregator, instance_remote_no_resolve):
    c = TLSCheck('tls', {}, [instance_remote_no_resolve])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, count=0)

    message = 'Unable to resolve host, check your DNS'
    assert message in aggregator.service_checks(c.SERVICE_CHECK_CAN_CONNECT)[0].message

    aggregator.assert_all_metrics_covered()


def test_no_connect(aggregator, instance_remote_no_connect):
    c = TLSCheck('tls', {}, [instance_remote_no_connect])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, count=0)

    message = 'Unable to resolve host, check your DNS'
    assert message not in aggregator.service_checks(c.SERVICE_CHECK_CAN_CONNECT)[0].message

    aggregator.assert_all_metrics_covered()


def test_no_connect_port_in_host(aggregator, instance_remote_no_connect_port_in_host):
    c = TLSCheck('tls', {}, [instance_remote_no_connect_port_in_host])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, count=0)

    message = 'Unable to resolve host, check your DNS'
    assert message not in aggregator.service_checks(c.SERVICE_CHECK_CAN_CONNECT)[0].message

    aggregator.assert_all_metrics_covered()


def test_no_connect_ipv6(aggregator, instance_remote_no_connect):
    c = TLSCheck('tls', {}, [instance_remote_no_connect])
    with mock.patch('socket.getaddrinfo', return_value=()):
        c.check(None)

    aggregator.assert_service_check(
        c.SERVICE_CHECK_CAN_CONNECT,
        status=c.CRITICAL,
        tags=c._tags,
        message='No valid addresses found, try checking your IPv6 connectivity',
        count=1,
    )
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, count=0)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, count=0)

    aggregator.assert_all_metrics_covered()


def test_version_default_1_1(aggregator, instance_remote_version_default_1_1):
    c = TLSCheck('tls', {}, [instance_remote_version_default_1_1])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_version_default_1_2(aggregator, instance_remote_version_default_1_2):
    c = TLSCheck('tls', {}, [instance_remote_version_default_1_2])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_version_default_1_3(aggregator, instance_remote_version_default_1_3):
    c = TLSCheck('tls', {}, [instance_remote_version_default_1_3])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_version_init_config_default(aggregator, instance_remote_version_default_1_1):
    c = TLSCheck('tls', {'allowed_versions': ['1.1']}, [instance_remote_version_default_1_1])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_hostname_mismatch(aggregator, instance_remote_hostname_mismatch):
    c = TLSCheck('tls', {}, [instance_remote_hostname_mismatch])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_self_signed_ok(aggregator, instance_remote_self_signed_ok):
    c = TLSCheck('tls', {}, [instance_remote_self_signed_ok])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_expired(aggregator, instance_remote_cert_expired):
    c = TLSCheck('tls', {}, [instance_remote_cert_expired])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    if PY2:
        aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, count=0)
        aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, count=0)
    else:
        aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, count=0)
        aggregator.assert_service_check(
            c.SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, message='Certificate has expired', count=1
        )

    aggregator.assert_all_metrics_covered()


def test_cert_critical_days(aggregator, instance_remote_cert_critical_days):
    c = TLSCheck('tls', {}, [instance_remote_cert_critical_days])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_critical_seconds(aggregator, instance_remote_cert_critical_seconds):
    c = TLSCheck('tls', {}, [instance_remote_cert_critical_seconds])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_warning_days(aggregator, instance_remote_cert_warning_days):
    c = TLSCheck('tls', {}, [instance_remote_cert_warning_days])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.WARNING, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_warning_seconds(aggregator, instance_remote_cert_warning_seconds):
    c = TLSCheck('tls', {}, [instance_remote_cert_warning_seconds])
    c.check(None)

    aggregator.assert_service_check(c.SERVICE_CHECK_CAN_CONNECT, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VERSION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(c.SERVICE_CHECK_EXPIRATION, status=c.WARNING, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()
