# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.weaviate import WeaviateCheck

from .common import API_METRICS, MOCKED_INSTANCE, OM_METRICS, get_fixture_path

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'fname, metrics',
    [
        ('weaviate_openmetrics.txt', OM_METRICS),
        ('weaviate_nodes_api.json', API_METRICS),
    ],
)
def test_check_mock_weaviate_responses(dd_run_check, aggregator, mock_http_response, fname, metrics):
    mock_http_response(file_path=get_fixture_path(f'{fname}'))
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in metrics:
        aggregator.assert_metric(metric, at_least=1)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    if fname == 'weaviate_openmetrics.txt':
        aggregator.assert_service_check('weaviate.openmetrics.health', ServiceCheck.OK)
    else:
        aggregator.assert_service_check('weaviate.node.status', ServiceCheck.OK)


def test_check_failed_liveness(dd_run_check, aggregator, mock_http_response):
    mock_http_response(status_code=404)
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    dd_run_check(check)

    # No metrics should be submitted
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('weaviate.liveness.status', ServiceCheck.CRITICAL)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  field required',
    ):
        check = WeaviateCheck('weaviate', {}, [{}])
        dd_run_check(check)


@pytest.mark.parametrize(
    'instance',
    [
        ({'openmetrics_endpoint': 'weaviate:2112/metrics'}),
        ({'weaviate_api_endpoint': 'https://localhost:2112/metrics'}),
    ],
)
@pytest.mark.unit
def test_custom_validation(dd_run_check, instance):
    for k, v in instance.items():
        with pytest.raises(
            Exception,
            match=f'{k}: {v} is incorrectly configured',
        ):
            check = WeaviateCheck('weaviate', {}, [instance])
            dd_run_check(check)
