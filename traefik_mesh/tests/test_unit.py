# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics
from datadog_checks.traefik_mesh import TraefikMeshCheck

from .common import OM_METRICS, OM_MOCKED_INSTANCE, OPTIONAL_METRICS, get_fixture_path


def test_check_mock_traefik_mesh_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('traefik_proxy.txt'))
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in OM_METRICS:
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, 'test:traefik_mesh')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('traefik_mesh.openmetrics.health', ServiceCheck.OK)
    assert_service_checks(aggregator)


def test_check_mock_invalid_traefik_mesh_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = TraefikMeshCheck('traefik_mesh', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
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