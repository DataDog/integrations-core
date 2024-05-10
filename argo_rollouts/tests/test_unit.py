# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.argo_rollouts import ArgoRolloutsCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics

from .common import OM_METRICS, OM_MOCKED_INSTANCE, get_fixture_path


def test_check_mock_argo_rollouts_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('openmetrics.txt'))
    check = ArgoRolloutsCheck('argo_rollouts', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in OM_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('argo_rollouts.openmetrics.health', ServiceCheck.OK)
    assert_service_checks(aggregator)


def test_check_mock_invalid_argo_rollouts_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = ArgoRolloutsCheck('argo_rollouts', {}, [OM_MOCKED_INSTANCE])
    with pytest.raises(Exception):
        dd_run_check(check)

    aggregator.assert_service_check('argo_rollouts.openmetrics.health', ServiceCheck.CRITICAL)
    assert_service_checks(aggregator)


def test_check_mock_labels_rename(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('label_rename.txt'))
    check = ArgoRolloutsCheck('argo_rollouts', {}, [OM_MOCKED_INSTANCE])
    relabeled_tags = ['argo_rollouts_namespace:default', 'argo_rollouts_name:rollouts-demo', 'go_version:go1.20.12']
    dd_run_check(check)

    aggregator.assert_metric('argo_rollouts.rollout.info')
    for tag in relabeled_tags:
        aggregator.assert_metric_has_tag('argo_rollouts.rollout.info', tag)


def test_version_metadata(datadog_agent, dd_run_check, mock_http_response):
    """
    Test metadata version collection with V2 implementation
    """
    mock_http_response(file_path=get_fixture_path('openmetrics.txt'))
    check = ArgoRolloutsCheck('argo_rollouts', {}, [OM_MOCKED_INSTANCE])
    check.check_id = 'test:123'
    dd_run_check(check)

    # Version from fixture
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '1',
        'version.minor': '6',
        'version.patch': '4',
        'version.build': 'a312af9',
        'version.raw': 'v1.6.4+a312af9',
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
