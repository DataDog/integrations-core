# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict

from datadog_checks.argocd import ArgocdCheck
from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics

from . import common
from .utils import get_fixture_path


def test_app_controller(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('app_controller_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [common.MOCKED_APP_CONTROLLER_INSTANCE])
    dd_run_check(check)

    for metric in common.APP_CONTROLLER_METRICS:
        if metric in common.NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    # aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_api_server(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('api_server_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [common.MOCKED_API_SERVER_INSTANCE])
    dd_run_check(check)

    for metric in common.API_SERVER_METRICS:
        if metric in common.NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    # aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()


def test_repo_server(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('REPO_SERVer_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [common.MOCKED_REPO_SERVER_INSTANCE])
    dd_run_check(check)

    for metric in common.REPO_SERVER_METRICS:
        if metric in common.NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    # aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
    aggregator.assert_all_metrics_covered()
# def test_check(dd_run_check, aggregator, instance):
#     # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
#     check = ArgocdCheck('argocd', {}, [instance])
#     dd_run_check(check)

#     aggregator.assert_all_metrics_covered()
#     aggregator.assert_metrics_using_metadata(get_metadata_metrics())


# def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
#     # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
#     check = ArgocdCheck('argocd', {}, [instance])
#     dd_run_check(check)
#     aggregator.assert_service_check('argocd.can_connect', ArgocdCheck.CRITICAL)
