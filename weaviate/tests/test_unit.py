# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path
from urllib.parse import urljoin

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.weaviate import WeaviateCheck

from .common import API_METRICS, MOCKED_INSTANCE, OM_METRICS, OM_MOCKED_INSTANCE, get_fixture_path

pytestmark = pytest.mark.unit


def test_check_mock_weaviate_openmetrics(dd_run_check, aggregator, fake_http, fake_http_response):
    fake_http_response(
        OM_MOCKED_INSTANCE['openmetrics_endpoint'], Path(get_fixture_path('weaviate_openmetrics.txt')).read_bytes()
    )
    check = WeaviateCheck('weaviate', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    fake_http.assert_all_responses_consumed()
    for metric in OM_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('weaviate.openmetrics.health', ServiceCheck.OK)


def test_check_mock_weaviate_nodes(aggregator, fake_http, fake_http_response):
    fake_http_response(
        urljoin(MOCKED_INSTANCE['weaviate_api_endpoint'], '/v1/nodes'),
        json_data=json.loads(Path(get_fixture_path('weaviate_nodes_api.json')).read_bytes()),
    )
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check._submit_node_metrics()
    fake_http.assert_all_responses_consumed()

    for metric in API_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('weaviate.node.status', ServiceCheck.OK)


def test_check_failed_liveness(aggregator, fake_http, fake_http_response):
    fake_http_response(urljoin(MOCKED_INSTANCE['weaviate_api_endpoint'], '/v1/.well-known/live'), status_code=404)
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check._submit_liveness_metrics()
    fake_http.assert_all_responses_consumed()

    # No metrics should be submitted
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('weaviate.liveness.status', ServiceCheck.CRITICAL)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
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
def test_custom_validation(dd_run_check, instance):
    for k, v in instance.items():
        with pytest.raises(
            Exception,
            match=f'{k}: {v} is incorrectly configured',
        ):
            check = WeaviateCheck('weaviate', {}, [instance])
            dd_run_check(check)


def test_check_mock_weaviate_metadata(datadog_agent, fake_http, fake_http_response):
    fake_http_response(
        urljoin(MOCKED_INSTANCE['weaviate_api_endpoint'], '/v1/meta'),
        json_data=json.loads(Path(get_fixture_path('weaviate_meta_api.json')).read_bytes()),
    )
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check.check_id = 'test:123'
    check._submit_version_metadata()
    fake_http.assert_all_responses_consumed()
    raw_version = '1.19.1'

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
