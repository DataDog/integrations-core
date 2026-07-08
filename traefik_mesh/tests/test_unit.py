# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest
import requests

from datadog_checks.base.constants import ServiceCheck
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

pytestmark = pytest.mark.unit


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


def test_check_mock_traefik_mesh_openmetrics_v3(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('traefik_proxy_v3.txt'))
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


def test_get_version(datadog_agent, dd_run_check, mock_http_response_per_endpoint):
    from datadog_checks.dev.http import MockResponse

    instance = {
        'openmetrics_endpoint': 'http://localhost:8080/metrics',
        'traefik_proxy_api_endpoint': 'http://localhost:8080',
        'tags': ['test:traefik_mesh'],
    }
    check = TraefikMeshCheck('traefik_mesh', {}, [instance])
    check.check_id = 'test:123'

    mock_http_response_per_endpoint(
        {
            'http://localhost:8080/metrics': [MockResponse(file_path=get_fixture_path('traefik_proxy.txt'))],
            'http://localhost:8080/api/version': [MockResponse(file_path=get_fixture_path('mesh_proxy_version.json'))],
        }
    )
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


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:20 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert TraefikMeshCheck.DEFAULT_METRIC_LIMIT == 0


def test_submit_mesh_ready_status_true_string_reports_one(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at check.py:72 (status == 'true' -> status is 'true'):
    # json.loads produces a fresh, non-interned string so an `is` comparison would not match, and also kills
    # the core/NumberReplacer mutants that change the true-case gauge value from 1 to 2 or to 0.
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    nodes = json.loads('[{"Name": "node-a", "IP": "10.0.0.1", "Ready": "true"}]')

    check.submit_mesh_ready_status(nodes)

    aggregator.assert_metric('traefik_mesh.node.ready', value=1, count=1)


def test_submit_mesh_ready_status_non_true_reports_zero(aggregator):
    # Complements the above so the true/false branches of `1 if status == 'true' else 0` are both covered.
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    nodes = json.loads('[{"Name": "node-a", "IP": "10.0.0.1", "Ready": "false"}]')

    check.submit_mesh_ready_status(nodes)

    aggregator.assert_metric('traefik_mesh.node.ready', value=0, count=1)


def test_get_mesh_ready_status_returns_none_for_empty_status(mock_http_response):
    # Kills the core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at check.py:79: both collapse
    # `if not node_status:` to a check equivalent to `if node_status:`, which would return the falsy `[]`
    # unchanged instead of the explicit `None`.
    mock_http_response(json_data=[])
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE_CONTROLLER])

    assert check.get_mesh_ready_status() is None


def test_metadata_entrypoint_skips_submit_version_when_disabled(
    datadog_agent, dd_run_check, mock_http_response_per_endpoint
):
    # Kills the core/RemoveDecorator mutant at check.py:99 (removing @AgentCheck.metadata_entrypoint from
    # _submit_version): without the decorator, version metadata would still be submitted while disabled, even
    # though `get_version()` here is wired to succeed (unlike OM_MOCKED_INSTANCE, which has no version endpoint
    # and would report zero metadata either way).
    from datadog_checks.dev.http import MockResponse

    instance = {
        'openmetrics_endpoint': 'http://localhost:8080/metrics',
        'traefik_proxy_api_endpoint': 'http://localhost:8080',
        'tags': ['test:traefik_mesh'],
    }
    check = TraefikMeshCheck('traefik_mesh', {}, [instance])
    check.check_id = 'test:123'
    datadog_agent._config['enable_metadata_collection'] = False

    mock_http_response_per_endpoint(
        {
            'http://localhost:8080/metrics': [MockResponse(file_path=get_fixture_path('traefik_proxy.txt'))],
            'http://localhost:8080/api/version': [MockResponse(file_path=get_fixture_path('mesh_proxy_version.json'))],
        }
    )
    dd_run_check(check)

    datadog_agent.assert_metadata_count(0)


def test_get_json_timeout_is_handled(mocker):
    # Kills the core/ExceptionReplacer mutant at check.py:119 (requests.exceptions.Timeout -> an undefined
    # exception name): the broken except clause raises NameError instead of returning None gracefully.
    mocker.patch('requests.Session.get', side_effect=requests.exceptions.Timeout)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])

    assert check._get_json('http://localhost:8080/some-endpoint') is None
