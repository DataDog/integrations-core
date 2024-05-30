# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics
from datadog_checks.traefik_mesh import TraefikMeshCheck

from .common import (
    OM_METRICS,
    OM_MOCKED_INSTANCE,
    OM_MOCKED_INSTANCE_CONTROLLER,
    OPTIONAL_METRICS,
    get_fixture_path,
    read_json_fixture,
)


def test_check_mock_traefik_mesh_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('traefik_proxy.txt'))
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


def test_check_mock_invalid_traefik_mesh_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
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


def test_submit_node_ready_status(aggregator, dd_run_check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('traefik_proxy.txt'))
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


def test_valid_controller_service_check(aggregator, mock_http_response):
    mock_http_response(status_code=200)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE_CONTROLLER])

    check.submit_controller_readiness_service_check()
    aggregator.assert_service_check('traefik_mesh.controller.ready', ServiceCheck.OK)


def test_invalid_controller_service_check(aggregator, mock_http_response):
    mock_http_response(status_code=500)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE_CONTROLLER])

    check.submit_controller_readiness_service_check()
    aggregator.assert_service_check('traefik_mesh.controller.ready', ServiceCheck.CRITICAL)


def test_submit_version(datadog_agent, dd_run_check, mock_http_response):
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    mock_http_response(file_path=get_fixture_path('traefik_proxy.txt'))

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
