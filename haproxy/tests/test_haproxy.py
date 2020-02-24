# (C) Datadog, Inc. 2012-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import os

import pytest

from datadog_checks.haproxy import HAProxy

from .common import (
    BACKEND_AGGREGATE_ONLY_CHECK,
    BACKEND_CHECK,
    BACKEND_HOSTS_METRIC,
    BACKEND_LIST,
    BACKEND_SERVICES,
    BACKEND_STATUS_METRIC,
    BACKEND_TO_ADDR,
    CHECK_CONFIG_OPEN,
    CONFIG_TCPSOCKET,
    CONFIG_UNIXSOCKET,
    FRONTEND_CHECK,
    SERVICE_CHECK_NAME,
    STATS_SOCKET,
    STATS_URL,
    STATS_URL_OPEN,
    haproxy_less_than_1_7,
    platform_supports_sockets,
    requires_shareable_unix_socket,
    requires_socket_support,
)


def _test_frontend_metrics(aggregator, shared_tag, count=1):
    haproxy_version = os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2]
    frontend_tags = shared_tag + ['type:FRONTEND', 'service:public', 'haproxy_service:public']
    for metric_name, min_version in FRONTEND_CHECK:
        if haproxy_version >= min_version:
            aggregator.assert_metric(metric_name, tags=frontend_tags, count=count)


def _test_backend_metrics(aggregator, shared_tag, services=None, add_addr_tag=False, check_aggregates=False, count=1):
    backend_tags = shared_tag + ['type:BACKEND']
    haproxy_version = os.environ.get('HAPROXY_VERSION', '1.5.11').split('.')[:2]
    if not services:
        services = BACKEND_SERVICES
    for service in services:
        tags = backend_tags + ['service:' + service, 'haproxy_service:' + service, 'backend:BACKEND']

        if check_aggregates:
            for metric_name, min_version in BACKEND_AGGREGATE_ONLY_CHECK:
                if haproxy_version >= min_version:
                    aggregator.assert_metric(metric_name, tags=tags, count=count)

        for backend in BACKEND_LIST:
            tags = backend_tags + ['service:' + service, 'haproxy_service:' + service, 'backend:' + backend]

            if add_addr_tag and haproxy_version >= ['1', '7']:
                tags.append('server_address:{}'.format(BACKEND_TO_ADDR[backend]))

            for metric_name, min_version in BACKEND_CHECK:
                if haproxy_version >= min_version:
                    aggregator.assert_metric(metric_name, tags=tags, count=count)


def _test_backend_hosts(aggregator, count=1):
    for service in BACKEND_SERVICES:
        available_tag = ['available:true', 'service:' + service, 'haproxy_service:' + service]
        unavailable_tag = ['available:false', 'service:' + service, 'haproxy_service:' + service]
        aggregator.assert_metric(BACKEND_HOSTS_METRIC, tags=available_tag, count=count)
        aggregator.assert_metric(BACKEND_HOSTS_METRIC, tags=unavailable_tag, count=count)

        status_no_check_tags = ['service:' + service, 'haproxy_service:' + service, 'status:no_check']
        aggregator.assert_metric(BACKEND_STATUS_METRIC, tags=status_no_check_tags, count=count)


def _test_service_checks(aggregator, services=None, count=1):
    if not services:
        services = BACKEND_SERVICES
    for service in services:
        for backend in BACKEND_LIST:
            tags = ['service:' + service, 'haproxy_service:' + service, 'backend:' + backend]
            aggregator.assert_service_check(SERVICE_CHECK_NAME, status=HAProxy.UNKNOWN, count=count, tags=tags)
        tags = ['service:' + service, 'haproxy_service:' + service, 'backend:BACKEND']
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=HAProxy.OK, count=count, tags=tags)


@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check(aggregator, check, instance):
    check = check(instance)
    check.check(instance)

    shared_tag = ["instance_url:{0}".format(STATS_URL)]

    _test_frontend_metrics(aggregator, shared_tag + ['active:false'])
    _test_backend_metrics(aggregator, shared_tag + ['active:false'], check_aggregates=True)

    _test_service_checks(aggregator, count=0)

    aggregator.assert_all_metrics_covered()


@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_service_check(aggregator, check, instance):
    # Add the enable service check
    instance.update({"enable_service_check": True})
    check = check(instance)
    check.check(instance)

    shared_tag = ["instance_url:{0}".format(STATS_URL)]

    _test_frontend_metrics(aggregator, shared_tag + ['active:false'])
    _test_backend_metrics(aggregator, shared_tag + ['active:false'], check_aggregates=True)

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
    check = check(instance)
    check.check(instance)
    shared_tag = ["instance_url:{0}".format(STATS_URL)]

    _test_backend_metrics(aggregator, shared_tag + ['active:false'], ['datadog'], check_aggregates=True)

    aggregator.assert_all_metrics_covered()


@requires_socket_support
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_wrong_config(aggregator, check, instance):
    instance['username'] = 'fake_username'

    with pytest.raises(Exception):
        check = check(instance)
        check.check(instance)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_open_config(aggregator, check):
    check = check(CHECK_CONFIG_OPEN)
    check.check(CHECK_CONFIG_OPEN)

    shared_tag = ["instance_url:{0}".format(STATS_URL_OPEN)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag)
    _test_backend_hosts(aggregator)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.skipif(
    haproxy_less_than_1_7 or not platform_supports_sockets,
    reason='Sockets with operator level are only available with haproxy 1.7',
)
def test_tcp_socket(aggregator, check):
    config = copy.deepcopy(CONFIG_TCPSOCKET)
    check = check(config)
    check.check(config)

    shared_tag = ["instance_url:{0}".format(STATS_SOCKET)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag, add_addr_tag=True)

    aggregator.assert_all_metrics_covered()


@requires_shareable_unix_socket
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_unixsocket_config(aggregator, check, dd_environment):
    config = copy.deepcopy(CONFIG_UNIXSOCKET)
    unixsocket_url = dd_environment["unixsocket_url"]
    config['url'] = unixsocket_url
    check = check(config)
    check.check(config)

    shared_tag = ["instance_url:{0}".format(unixsocket_url)]

    _test_frontend_metrics(aggregator, shared_tag)
    _test_backend_metrics(aggregator, shared_tag, add_addr_tag=True)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_version_metadata_http(check, datadog_agent, version_metadata):
    config = copy.deepcopy(CHECK_CONFIG_OPEN)
    check = check(config)
    check.check_id = 'test:123'
    check.check(config)

    datadog_agent.assert_metadata('test:123', version_metadata)
    # some version contains release information which is not in the test env var
    metadata_count = (
        len(version_metadata) + 1
        if ('test:123', 'version.release') in datadog_agent._metadata
        else len(version_metadata)
    )
    datadog_agent.assert_metadata_count(metadata_count)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_uptime_skip_http(check, aggregator):
    config = copy.deepcopy(CHECK_CONFIG_OPEN)
    config['startup_grace_seconds'] = 20
    check = check(config)
    check.check(config)

    aggregator.assert_all_metrics_covered()


@requires_shareable_unix_socket
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_version_metadata_unix_socket(check, version_metadata, dd_environment, datadog_agent):
    config = copy.deepcopy(CONFIG_UNIXSOCKET)
    unixsocket_url = dd_environment["unixsocket_url"]
    config['url'] = unixsocket_url
    check = check(config)
    check.check_id = 'test:123'
    check.check(config)

    datadog_agent.assert_metadata('test:123', version_metadata)
    # some version contains release information which is not in the test env var
    metadata_count = (
        len(version_metadata) + 1
        if ('test:123', 'version.release') in datadog_agent._metadata
        else len(version_metadata)
    )
    datadog_agent.assert_metadata_count(metadata_count)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.skipif(
    haproxy_less_than_1_7 or not platform_supports_sockets,
    reason='Sockets with operator level are only available with haproxy 1.7',
)
def test_version_metadata_tcp_socket(check, version_metadata, datadog_agent):
    config = copy.deepcopy(CONFIG_TCPSOCKET)
    check = check(config)
    check.check_id = 'test:123'
    check.check(config)

    datadog_agent.assert_metadata('test:123', version_metadata)
    # some version contains release information which is not in the test env var
    metadata_count = (
        len(version_metadata) + 1
        if ('test:123', 'version.release') in datadog_agent._metadata
        else len(version_metadata)
    )
    datadog_agent.assert_metadata_count(metadata_count)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.skipif(
    haproxy_less_than_1_7 or not platform_supports_sockets,
    reason='Uptime is only reported on the stats socket in v1.7+',
)
def test_uptime_skip_tcp(aggregator, check, dd_environment):
    config = copy.deepcopy(CONFIG_TCPSOCKET)
    config['startup_grace_seconds'] = 20
    check = check(config)
    check.check(config)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(CHECK_CONFIG_OPEN, rate=True)

    shared_tag = ["instance_url:{0}".format(STATS_URL_OPEN)]

    _test_frontend_metrics(aggregator, shared_tag, count=None)
    _test_backend_metrics(aggregator, shared_tag, count=None)
    _test_backend_hosts(aggregator, count=2)

    aggregator.assert_all_metrics_covered()
