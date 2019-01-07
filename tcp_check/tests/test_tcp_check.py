# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

CHECK_NAME = 'tcp_check'


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def instance_ko():
    return {
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService',
        'tags': ["foo:bar"],
    }


@pytest.fixture
def instance():
    return {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1.5,
        'name': 'UpService',
        'tags': ["foo:bar"]
    }


@pytest.fixture
def instance_ssl():
    return {
        'host': 'datadoghq.com',
        'port': 443,
        'timeout': 1.5,
        'name': 'UpService',
        'tags': ["foo:bar"],
        'check_certificate_expiration': True
    }


def test_down(aggregator, check, instance_ko):
    """
    Service expected to be down
    """
    check.check(instance_ko)
    expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)


def test_up(aggregator, check, instance):
    """
    Service expected to be up
    """
    check.check(instance)
    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)


def test_response_time(aggregator, check, instance):
    """
    Test the response time from a server expected to be up
    """
    instance['collect_response_time'] = True
    instance['name'] = 'instance:response_time'
    check.check(instance)

    # service check
    expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:instance:response_time']
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)

    # response time metric
    expected_tags = ['url:datadoghq.com:80', 'instance:instance:response_time', 'foo:bar']
    aggregator.assert_metric('network.tcp.response_time', tags=expected_tags)
    aggregator.assert_all_metrics_covered()


def test_ssl_certificate_verification_certificate_up(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be up
    """
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.OK, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)


def test_ssl_certificate_verification_site_down(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be down
    """
    instance_ssl['host'] = '1.2.3.4'
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:1.2.3.4", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=0, tags=expected_tags)
    aggregator.assert_metric('tcp.ssl.days_left', value=0, tags=expected_tags)
    aggregator.assert_metric('tcp.ssl.seconds_left', value=0, tags=expected_tags)


def test_ssl_certificate_verification_site_expired(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be up, which certificate
    is expected to be down
    """
    instance_ssl['host'] = 'expired.badssl.com'
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:expired.badssl.com", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    aggregator.assert_metric('tcp.ssl.days_left', value=0, tags=expected_tags)
    aggregator.assert_metric('tcp.ssl.seconds_left', value=0, tags=expected_tags)


def test_ssl_certificate_verification_site_critical_in_days(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be up, which certificate
    is expected to be critical in days
    """
    instance_ssl['host'] = 'sha256.badssl.com'
    instance_ssl['days_critical'] = 1000
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:sha256.badssl.com", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)


def test_ssl_certificate_verification_site_warning_in_days(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be up, which certificate
    is expected to be critical in days
    """
    instance_ssl['host'] = 'sha256.badssl.com'
    instance_ssl['days_warning'] = 1000
    instance_ssl['days_critical'] = 1
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:sha256.badssl.com", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.WARNING, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)


def test_ssl_certificate_verification_site_critical_in_seconds(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be up, which certificate
    is expected to be critical in days
    """
    instance_ssl['host'] = 'sha256.badssl.com'
    instance_ssl['seconds_critical'] = 86400000  # 1000 days
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:sha256.badssl.com", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.CRITICAL, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)


def test_ssl_certificate_verification_site_warning_in_seconds(aggregator, check, instance_ssl):
    """
    Test the SSL certificate check from a server expected to be up, which certificate
    is expected to be critical in days
    """
    instance_ssl['host'] = 'sha256.badssl.com'
    instance_ssl['seconds_warning'] = 86400000  # 1000 days
    instance_ssl['seconds_critical'] = 1
    check.check(instance_ssl)

    expected_tags = ["instance:UpService", "target_host:sha256.badssl.com", "port:443", "foo:bar"]
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
    aggregator.assert_service_check('tcp.ssl_cert', status=check.WARNING, tags=expected_tags)
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
