# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from mock import patch

from datadog_checks.argocd import ArgocdCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    API_SERVER_METRICS,
    APP_CONTROLLER_METRICS,
    APPSET_CONTROLLER_METRICS,
    MOCKED_API_SERVER_INSTANCE,
    MOCKED_APP_CONTROLLER_INSTANCE,
    MOCKED_APP_CONTROLLER_WITH_OTHER_PARAMS,
    MOCKED_APPSET_CONTROLLER_INSTANCE,
    MOCKED_NOTIFICATIONS_CONTROLLER_INSTANCE,
    MOCKED_REPO_SERVER_INSTANCE,
    NOT_EXPOSED_METRICS,
    NOTIFICATIONS_CONTROLLER_METRICS,
    REPO_SERVER_METRICS,
)
from .utils import get_fixture_path


@pytest.mark.parametrize(
    'namespace, instance, metrics',
    [
        ('app_controller', MOCKED_APP_CONTROLLER_INSTANCE, APP_CONTROLLER_METRICS),
        ('app_controller', MOCKED_APP_CONTROLLER_WITH_OTHER_PARAMS, APP_CONTROLLER_METRICS),
        ('appset_controller', MOCKED_APPSET_CONTROLLER_INSTANCE, APPSET_CONTROLLER_METRICS),
        ('api_server', MOCKED_API_SERVER_INSTANCE, API_SERVER_METRICS),
        ('repo_server', MOCKED_REPO_SERVER_INSTANCE, REPO_SERVER_METRICS),
        ('notifications_controller', MOCKED_NOTIFICATIONS_CONTROLLER_INSTANCE, NOTIFICATIONS_CONTROLLER_METRICS),
    ],
)
def test_app_controller(dd_run_check, aggregator, mock_http_response, namespace, instance, metrics):
    mock_http_response(file_path=get_fixture_path('{}_metrics.txt'.format(namespace)))
    endpoint = instance.get('{}_endpoint'.format(namespace))
    tags = ["endpoint:{}".format(endpoint)]
    check = ArgocdCheck('argocd', {}, [instance])
    dd_run_check(check)

    for metric in metrics:
        if metric in NOT_EXPOSED_METRICS:
            aggregator.assert_metric(metric, count=0)
        elif metric == 'argocd.{}.go.memstats.alloc_bytes'.format(namespace):
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=tags)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check(f'argocd.{namespace}.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match="Must specify at least one of the following:"
        "`app_controller_endpoint`, `appset_controller_endpoint`, `repo_server_endpoint`, `api_server_endpoint` or"
        " `notifications_controller_endpoint`.",
    ):
        check = ArgocdCheck('argocd', {}, [{}])
        dd_run_check(check)


def test_app_controller_service_check(dd_run_check, aggregator, mock_http_response):
    # Test for transformer. The prometheus source submits a 1 or 0. 1 being OK and 0 being CRITICAL.
    # Anything else will be reported as UNKNOWN.
    mock_http_response(file_path=get_fixture_path('app_controller_metrics.txt'))
    check = ArgocdCheck('argocd', {}, [MOCKED_APP_CONTROLLER_INSTANCE])
    dd_run_check(check)

    aggregator.assert_service_check(
        'argocd.app_controller.cluster.connection.status',
        ServiceCheck.OK,
        tags=['endpoint:http://app_controller:8082', 'name:bar'],
    )
    aggregator.assert_service_check(
        'argocd.app_controller.cluster.connection.status',
        ServiceCheck.CRITICAL,
        tags=['endpoint:http://app_controller:8082', 'name:foo'],
    )
    aggregator.assert_service_check(
        'argocd.app_controller.cluster.connection.status',
        ServiceCheck.UNKNOWN,
        tags=['endpoint:http://app_controller:8082', 'name:baz'],
    )
    aggregator.assert_service_check(
        'argocd.app_controller.cluster.connection.status',
        ServiceCheck.UNKNOWN,
        tags=['endpoint:http://app_controller:8082', 'name:faz'],
    )


@patch('datadog_checks.argocd.check.PY2', True)
def test_py2():
    # Test to ensure that a ConfigurationError is raised when running with Python 2.
    with pytest.raises(ConfigurationError, match="This version of the integration is only available when using py3."):
        ArgocdCheck('argocd', {}, [MOCKED_APP_CONTROLLER_INSTANCE])
