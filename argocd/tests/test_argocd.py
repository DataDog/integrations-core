# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.argocd import ArgocdCheck

from . import common
from .utils import get_fixture_path


def test_app_controller(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('app_controller_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [common.MOCKED_APP_CONTROLLER_INSTANCE])
    dd_run_check(check)

    for metric in common.APP_CONTROLLER_METRICS:
        if metric in common.NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        elif metric == 'argocd.app_controller.go.memstats.alloc_bytes':
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_api_server(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('api_server_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [common.MOCKED_API_SERVER_INSTANCE])
    dd_run_check(check)

    for metric in common.API_SERVER_METRICS:
        if metric in common.NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        elif metric == 'argocd.api_server.go.memstats.alloc_bytes':
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_repo_server(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('repo_server_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [common.MOCKED_REPO_SERVER_INSTANCE])
    dd_run_check(check)

    for metric in common.REPO_SERVER_METRICS:
        if metric in common.NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        elif metric == 'argocd.repo_server.go.memstats.alloc_bytes':
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()


def test_empty_instance(dd_run_check):
    try:
        check = ArgocdCheck('argocd', {}, [{}])
        dd_run_check(check)
    except Exception as e:
        assert "Must specify at least one of the following:`app_controller_endpoint`, `repo_server_endpoint` or" in str(
            e
        )
