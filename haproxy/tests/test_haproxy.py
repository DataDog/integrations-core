# (C) Datadog, Inc. 2012-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os
import copy

from datadog_checks.utils.platform import Platform
from datadog_checks.haproxy import HAProxy

import common


def _test_frontend_metrics(aggregator, shared_tag):
    frontend_tags = shared_tag + ['type:FRONTEND', 'service:public']
    for gauge in common.FRONTEND_CHECK_GAUGES:
        aggregator.assert_metric(gauge, tags=frontend_tags, count=1)

    if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '4']:
        for gauge in common.FRONTEND_CHECK_GAUGES_POST_1_4:
            aggregator.assert_metric(gauge, tags=frontend_tags, count=1)

    for rate in common.FRONTEND_CHECK_RATES:
        aggregator.assert_metric(rate, tags=frontend_tags, count=1)

    if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '4']:
        for rate in common.FRONTEND_CHECK_RATES_POST_1_4:
            aggregator.assert_metric(rate, tags=frontend_tags, count=1)


def _test_backend_metrics(aggregator, shared_tag, services=None):
    backend_tags = shared_tag + ['type:BACKEND']
    if not services:
        services = common.BACKEND_SERVICES
    for service in services:
        for backend in common.BACKEND_LIST:
            tags = backend_tags + ['service:' + service, 'backend:' + backend]

            for gauge in common.BACKEND_CHECK_GAUGES:
                aggregator.assert_metric(gauge, tags=tags, count=1)

            if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '5']:
                for gauge in common.BACKEND_CHECK_GAUGES_POST_1_5:
                    aggregator.assert_metric(gauge, tags=tags, count=1)

            if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '7']:
                for gauge in common.BACKEND_CHECK_GAUGES_POST_1_7:
                    aggregator.assert_metric(gauge, tags=tags, count=1)

            for rate in common.BACKEND_CHECK_RATES:
                aggregator.assert_metric(rate, tags=tags, count=1)

            if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '4']:
                for rate in common.BACKEND_CHECK_RATES_POST_1_4:
                    aggregator.assert_metric(rate, tags=tags, count=1)


def _test_service_checks(aggregator, services=None):
    if not services:
        services = common.BACKEND_SERVICES
    for service in services:
        for backend in common.BACKEND_LIST:
            tags = ['service:' + service, 'backend:' + backend]
            aggregator.assert_service_check(common.SERVICE_CHECK_NAME,
                                            status=HAProxy.UNKNOWN,
                                            count=1,
                                            tags=tags)
        tags = ['service:' + service, 'backend:BACKEND']
        aggregator.assert_service_check(common.SERVICE_CHECK_NAME,
                                        status=HAProxy.OK,
                                        count=1,
                                        tags=tags)


@pytest.mark.integration
def test_check(aggregator, haproxy_container):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    haproxy_check.check(common.CHECK_CONFIG)

    shared_tag = ["instance_url:{0}".format(common.STATS_URL)]

    _test_frontend_metrics(aggregator, shared_tag + ['active:false'])
    _test_backend_metrics(aggregator, shared_tag + ['active:false'])

    # check was run 2 times
    #       - FRONTEND is reporting OPEN that we ignore
    #       - only the BACKEND aggregate is reporting UP -> OK
    #       - The 3 individual servers are returning no check -> UNKNOWN
    _test_service_checks(aggregator)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_check_service_filter(aggregator, haproxy_container):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    config = copy.deepcopy(common.CHECK_CONFIG)
    config['services_include'] = ['datadog']
    config['services_exclude'] = ['.*']
    haproxy_check.check(config)
    shared_tag = ["instance_url:{0}".format(common.STATS_URL)]

    _test_backend_metrics(aggregator, shared_tag + ['active:false'], ['datadog'])

    _test_service_checks(aggregator, ['datadog'])

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_wrong_config(aggregator, haproxy_container):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    config = copy.deepcopy(common.CHECK_CONFIG)
    config['username'] = 'fake_username'

    with pytest.raises(Exception):
        haproxy_check.check(config)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_open_config(aggregator, haproxy_container):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    haproxy_check.check(common.CHECK_CONFIG_OPEN)

    shared_tag = ["instance_url:{0}".format(common.STATS_URL_OPEN)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag)
    _test_service_checks(aggregator)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.skipif(not Platform.is_linux(), reason='Windows sockets are not file handles')
def test_unixsocket_config(aggregator, haproxy_container):
    haproxy_check = HAProxy(common.CHECK_NAME, {}, {})
    config = copy.deepcopy(common.CONFIG_UNIXSOCKET)
    unixsocket_url = 'unix://{0}'.format(haproxy_container)
    config['url'] = unixsocket_url
    haproxy_check.check(config)

    shared_tag = ["instance_url:{0}".format(unixsocket_url)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag)
    _test_service_checks(aggregator)

    aggregator.assert_all_metrics_covered()
