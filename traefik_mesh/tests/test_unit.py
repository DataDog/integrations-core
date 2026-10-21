# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError as _HTTPConnectionError
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectTimeoutError as _HTTPConnectTimeoutError
from datadog_checks.base.utils.http_exceptions import HTTPClientReadTimeoutError as _HTTPReadTimeoutError
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.base.utils.http_exceptions import HTTPClientTimeoutError as _HTTPTimeoutError
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics
from datadog_checks.traefik_mesh import TraefikMeshCheck

from .common import (
    OM_METRICS,
    OM_MOCKED_INSTANCE,
    OM_MOCKED_INSTANCE_CONTROLLER,
    OM_V3_METRICS,
    OM_V3_OPTIONAL_METRICS,
    OPTIONAL_METRICS,
    get_fixture_path,
    read_json_fixture,
)

METRICS_URL = 'http://localhost:8080/metrics'


def register_metrics(fake_http_response, fixture):
    with open(get_fixture_path(fixture), 'rb') as f:
        fake_http_response(METRICS_URL, f.read(), headers={'Content-Type': 'text/plain'})


def test_check_mock_traefik_mesh_openmetrics(dd_run_check, aggregator, fake_http_response):
    register_metrics(fake_http_response, 'traefik_proxy.txt')
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in OM_METRICS:
        if metric not in OPTIONAL_METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, 'test:traefik_mesh')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('traefik_mesh.openmetrics.health', ServiceCheck.OK)
    assert_service_checks(aggregator)


def test_check_mock_traefik_mesh_openmetrics_v3(dd_run_check, aggregator, fake_http_response):
    register_metrics(fake_http_response, 'traefik_proxy_v3.txt')
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in OM_V3_METRICS:
        if metric not in OM_V3_OPTIONAL_METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, 'test:traefik_mesh')

    aggregator.assert_metric('traefik_mesh.open_connections')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('traefik_mesh.openmetrics.health', ServiceCheck.OK)
    assert_service_checks(aggregator)


def test_check_mock_invalid_traefik_mesh_openmetrics(dd_run_check, aggregator, fake_http_response):
    fake_http_response(METRICS_URL, status_code=503)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception, match='There was an error scraping endpoint http://localhost:8080/metrics'):
        dd_run_check(check)

    aggregator.assert_service_check('traefik_mesh.openmetrics.health', ServiceCheck.CRITICAL)
    assert_service_checks(aggregator)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = TraefikMeshCheck('traefik_mesh', {}, [{}])
        dd_run_check(check)


def test_submit_node_ready_status(aggregator, dd_run_check, fake_http_response):
    register_metrics(fake_http_response, 'traefik_proxy.txt')
    fake_http_response('http://localhost:8081/api/status/readiness')
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE_CONTROLLER])

    with mock.patch(
        'datadog_checks.traefik_mesh.TraefikMeshCheck.get_mesh_ready_status',
        return_value=read_json_fixture('controller_node_status.json'),
    ):
        dd_run_check(check)

    tags = [
        'controller_endpoint:http://localhost:8081',
        'test:traefik_mesh',
        'node_name:traefik-mesh-proxy-jgh7x',
        'node_ip:10.68.1.20',
    ]
    aggregator.assert_metric('traefik_mesh.node.ready', value=0, tags=tags)
    aggregator.assert_metric('traefik_mesh.node.ready', count=3)


def test_valid_controller_service_check(aggregator, fake_http_response):
    fake_http_response('http://localhost:8081/api/status/readiness', status_code=200)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE_CONTROLLER])

    check.submit_controller_readiness_service_check()
    aggregator.assert_service_check('traefik_mesh.controller.ready', ServiceCheck.OK)


def test_invalid_controller_service_check(aggregator, fake_http_response):
    fake_http_response('http://localhost:8081/api/status/readiness', status_code=500)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE_CONTROLLER])

    check.submit_controller_readiness_service_check()
    aggregator.assert_service_check('traefik_mesh.controller.ready', ServiceCheck.CRITICAL)


def test_get_version(datadog_agent, dd_run_check, fake_http_response):
    instance = {
        'openmetrics_endpoint': METRICS_URL,
        'traefik_proxy_api_endpoint': 'http://localhost:8080',
        'tags': ['test:traefik_mesh'],
    }
    check = TraefikMeshCheck('traefik_mesh', {}, [instance])
    check.check_id = 'test:123'

    register_metrics(fake_http_response, 'traefik_proxy.txt')
    fake_http_response('http://localhost:8080/api/version', json_data=read_json_fixture('mesh_proxy_version.json'))
    dd_run_check(check)

    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.raw': '2.5.7',
            'version.scheme': 'semver',
            'version.major': '2',
            'version.minor': '5',
            'version.patch': '7',
        },
    )


def test_submit_version(datadog_agent, dd_run_check, fake_http_response):
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    register_metrics(fake_http_response, 'traefik_proxy.txt')

    check.get_version = mock.MagicMock(return_value='2.6.7')
    check.check_id = 'test:123'
    dd_run_check(check)

    version_metadata = {
        'version.raw': '2.6.7',
        'version.scheme': 'semver',
        'version.major': '2',
        'version.minor': '6',
        'version.patch': '7',
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


def test_get_json_handles_http_status_error(fake_http):
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    fake_http.register_response('GET', 'http://example.com/api', HTTPClientStatusError('404 Client Error'))
    assert check._get_json('http://example.com/api') is None


def test_get_json_handles_http_connection_error(fake_http):
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    fake_http.register_response('GET', 'http://example.com/api', _HTTPConnectionError('Connection refused'))
    assert check._get_json('http://example.com/api') is None


@pytest.mark.parametrize(
    'error_type, expected_warning',
    [
        pytest.param(
            _HTTPConnectTimeoutError,
            "Couldn't connect to URL: %s with exception: %s. Please verify the address is reachable",
            id='connect-timeout',
        ),
        pytest.param(
            _HTTPReadTimeoutError,
            "Connection timeout when connecting to %s: %s",
            id='read-timeout',
        ),
    ],
)
def test_get_json_timeout_warning(fake_http, error_type, expected_warning):
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    error = error_type('timed out')
    fake_http.register_response('GET', 'http://example.com/api', error)

    with mock.patch.object(check, 'warning') as warning:
        assert check._get_json('http://example.com/api') is None

    warning.assert_called_once_with(expected_warning, 'http://example.com/api', error)


def test_get_json_handles_http_timeout_error(fake_http):
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    fake_http.register_response('GET', 'http://example.com/api', _HTTPTimeoutError('Read timed out'))
    assert check._get_json('http://example.com/api') is None
