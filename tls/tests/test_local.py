# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.tls import TLSCheck
from datadog_checks.tls.const import (
    SERVICE_CHECK_CAN_CONNECT,
    SERVICE_CHECK_EXPIRATION,
    SERVICE_CHECK_VALIDATION,
    SERVICE_CHECK_VERSION,
)
from datadog_checks.tls.tls_local import TLSLocalCheck


def test_right_class(instance_local_no_server_hostname):
    c = TLSCheck('tls', {}, [instance_local_no_server_hostname])
    assert isinstance(c.checker, TLSLocalCheck)


def test_no_server_hostname(instance_local_no_server_hostname):
    c = TLSCheck('tls', {}, [instance_local_no_server_hostname])

    with pytest.raises(ConfigurationError):
        c.check(None)


def test_not_found(aggregator, instance_local_not_found):
    c = TLSCheck('tls', {}, [instance_local_not_found])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    aggregator.assert_all_metrics_covered()


def test_ok(aggregator, instance_local_ok):
    c = TLSCheck('tls', {}, [instance_local_ok])

    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_ok_der(aggregator, instance_local_ok_der):
    c = TLSCheck('tls', {}, [instance_local_ok_der])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_hostname(aggregator, instance_local_hostname):
    c = TLSCheck('tls', {}, [instance_local_hostname])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_hostname_mismatch(aggregator, instance_local_hostname_mismatch):
    c = TLSCheck('tls', {}, [instance_local_hostname_mismatch])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_bad(aggregator, instance_local_cert_bad):
    c = TLSCheck('tls', {}, [instance_local_cert_bad])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, count=0)

    aggregator.assert_all_metrics_covered()


def test_cert_expired(aggregator, instance_local_cert_expired):
    c = TLSCheck('tls', {}, [instance_local_cert_expired])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_send_cert_duration(aggregator, instance_local_send_cert_duration):
    c = TLSCheck('tls', {}, [instance_local_send_cert_duration])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_metric('tls.issued_days', count=1)
    aggregator.assert_metric('tls.issued_seconds', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_critical_days(aggregator, instance_local_cert_critical_days):
    c = TLSCheck('tls', {}, [instance_local_cert_critical_days])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_critical_seconds(aggregator, instance_local_cert_critical_seconds):
    c = TLSCheck('tls', {}, [instance_local_cert_critical_seconds])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.CRITICAL, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_warning_days(aggregator, instance_local_cert_warning_days):
    c = TLSCheck('tls', {}, [instance_local_cert_warning_days])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.WARNING, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()


def test_cert_warning_seconds(aggregator, instance_local_cert_warning_seconds):
    c = TLSCheck('tls', {}, [instance_local_cert_warning_seconds])
    c.check(None)

    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.OK, tags=c._tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.WARNING, tags=c._tags, count=1)

    aggregator.assert_metric('tls.days_left', count=1)
    aggregator.assert_metric('tls.seconds_left', count=1)
    aggregator.assert_all_metrics_covered()
