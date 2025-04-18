# (C) Datadog, Inc. 2025-present
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
from datadog_checks.tls.tls_windows import TLSWindowsCheck


def test_right_class(instance_windows_cert_store):
    c = TLSCheck('tls', {}, [instance_windows_cert_store])
    assert isinstance(c.checker, TLSWindowsCheck)


def test_windows_cert_stores(aggregator, instance_windows_cert_store):
    c = TLSCheck('tls', {}, [instance_windows_cert_store])
    c.check(None)

    tags = c._tags + ['certificate_store:CA'] + ['subject_CN:Root Agency']
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=tags)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=tags)

    aggregator.assert_metric('tls.days_left', tags=tags)
    aggregator.assert_metric('tls.seconds_left', tags=tags)
    aggregator.assert_all_metrics_covered()


def test_windows_cert_stores_subject_filter(aggregator, instance_windows_cert_store):

    instance_windows_cert_store['cert_subject'] = ['Root Agency']
    c = TLSCheck('tls', {}, [instance_windows_cert_store])
    c.check(None)

    tags = c._tags + ['certificate_store:CA'] + ['subject_CN:Root Agency']
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, count=0)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=c.OK, tags=tags, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=c.CRITICAL, tags=tags, count=1)

    aggregator.assert_metric('tls.days_left', tags=tags, count=1)
    aggregator.assert_metric('tls.seconds_left', tags=tags, count=1)
    aggregator.assert_all_metrics_covered()
