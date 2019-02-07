# (C) Datadog, Inc. 2012-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os
import copy

from datadog_checks.haproxy import HAProxy

from .common import (BACKEND_SERVICES, BACKEND_LIST, BACKEND_TO_ADDR, BACKEND_CHECK_GAUGES, FRONTEND_CHECK_GAUGES,
                     FRONTEND_CHECK_GAUGES_POST_1_4, BACKEND_CHECK_GAUGES_POST_1_5, BACKEND_CHECK_GAUGES_POST_1_7,
                     FRONTEND_CHECK_RATES, FRONTEND_CHECK_RATES_POST_1_4, BACKEND_CHECK_RATES_POST_1_4,
                     BACKEND_CHECK_RATES, requires_socket_support, SERVICE_CHECK_NAME, STATS_URL, CHECK_CONFIG_OPEN,
                     STATS_URL_OPEN, CONFIG_TCPSOCKET, STATS_SOCKET, CONFIG_UNIXSOCKET, platform_supports_sockets)


def _test_frontend_metrics(aggregator, shared_tag):
    frontend_tags = shared_tag + ['type:FRONTEND', 'service:public']
    for gauge in FRONTEND_CHECK_GAUGES:
        aggregator.assert_metric(gauge, tags=frontend_tags, count=1)

    if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '4']:
        for gauge in FRONTEND_CHECK_GAUGES_POST_1_4:
            aggregator.assert_metric(gauge, tags=frontend_tags, count=1)

    for rate in FRONTEND_CHECK_RATES:
        aggregator.assert_metric(rate, tags=frontend_tags, count=1)

    if os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] >= ['1', '4']:
        for rate in FRONTEND_CHECK_RATES_POST_1_4:
            aggregator.assert_metric(rate, tags=frontend_tags, count=1)


def _test_backend_metrics(aggregator, shared_tag, services=None, add_addr_tag=False):
    backend_tags = shared_tag + ['type:BACKEND']
    haproxy_version = os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2]
    if not services:
        services = BACKEND_SERVICES
    for service in services:
        for backend in BACKEND_LIST:
            tags = backend_tags + ['service:' + service, 'backend:' + backend]

            if add_addr_tag and haproxy_version >= ['1', '7']:
                tags.append('server_address:{}'.format(
                    BACKEND_TO_ADDR[backend]))

            for gauge in BACKEND_CHECK_GAUGES:
                aggregator.assert_metric(gauge, tags=tags, count=1)

            if haproxy_version >= ['1', '5']:
                for gauge in BACKEND_CHECK_GAUGES_POST_1_5:
                    aggregator.assert_metric(gauge, tags=tags, count=1)

            if haproxy_version >= ['1', '7']:
                for gauge in BACKEND_CHECK_GAUGES_POST_1_7:
                    aggregator.assert_metric(gauge, tags=tags, count=1)

            for rate in BACKEND_CHECK_RATES:
                aggregator.assert_metric(rate, tags=tags, count=1)

            if haproxy_version >= ['1', '4']:
                for rate in BACKEND_CHECK_RATES_POST_1_4:
                    aggregator.assert_metric(rate, tags=tags, count=1)


def _test_service_checks(aggregator, services=None, count=1):
    if not services:
        services = BACKEND_SERVICES
    for service in services:
        for backend in BACKEND_LIST:
            tags = ['service:' + service, 'backend:' + backend]
            aggregator.assert_service_check(SERVICE_CHECK_NAME,
                                            status=HAProxy.UNKNOWN,
                                            count=1,
                                            tags=tags)
        tags = ['service:' + service, 'backend:BACKEND']
        aggregator.assert_service_check(SERVICE_CHECK_NAME,
                                        status=HAProxy.OK,
                                        count=1,
                                        tags=tags)


@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check(aggregator, check, instance):
    check.check(instance)

    shared_tag = ["instance_url:{0}".format(STATS_URL)]

    _test_frontend_metrics(aggregator, shared_tag + ['active:false'])
    _test_backend_metrics(aggregator, shared_tag + ['active:false'])

    _test_service_checks(aggregator, count=0)

    aggregator.assert_all_metrics_covered()

@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_service_check(aggregator, check, instance):
    # Add the enable service check
    instance.update({
        "enable_service_check": True
    })

    check.check(instance)

    shared_tag = ["instance_url:{0}".format(STATS_URL)]

    _test_frontend_metrics(aggregator, shared_tag + ['active:false'])
    _test_backend_metrics(aggregator, shared_tag + ['active:false'])

    # check was run 2 times
    #       - FRONTEND is reporting OPEN that we ignore
    #       - only the BACKEND aggregate is reporting UP -> OK
    #       - The 3 individual servers are returning no check -> UNKNOWN
    _test_service_checks(aggregator)

    aggregator.assert_all_metrics_covered()

@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_service_filter(aggregator, check, instance):
    instance['services_include'] = ['datadog']
    instance['services_exclude'] = ['.*']
    check.check(instance)
    shared_tag = ["instance_url:{0}".format(STATS_URL)]

    _test_backend_metrics(aggregator, shared_tag + ['active:false'], ['datadog'])

    aggregator.assert_all_metrics_covered()


@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_wrong_config(aggregator, check, instance):
    instance['username'] = 'fake_username'

    with pytest.raises(Exception):
        check.check(instance)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_open_config(aggregator, check):
    check.check(CHECK_CONFIG_OPEN)

    shared_tag = ["instance_url:{0}".format(STATS_URL_OPEN)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.skipif(os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2] < ['1', '7'] or
                    not platform_supports_sockets,
                    reason='Sockets with operator level are only available with haproxy 1.7')
def test_tcp_socket(aggregator, check):
    config = copy.deepcopy(CONFIG_TCPSOCKET)
    check.check(config)

    shared_tag = ["instance_url:{0}".format(STATS_SOCKET)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag, add_addr_tag=True)

    aggregator.assert_all_metrics_covered()


@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_unixsocket_config(aggregator, check, dd_environment):
    config = copy.deepcopy(CONFIG_UNIXSOCKET)
    unixsocket_url = dd_environment["unixsocket_url"]
    config['url'] = unixsocket_url
    check.check(config)

    shared_tag = ["instance_url:{0}".format(unixsocket_url)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag, add_addr_tag=True)

    aggregator.assert_all_metrics_covered()
