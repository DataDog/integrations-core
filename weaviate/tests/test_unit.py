# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.common import round_value
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.weaviate import WeaviateCheck
from datadog_checks.weaviate.check import NODE_STATUS_VALUES

from .common import API_METRICS, MOCKED_INSTANCE, OM_METRICS, OM_MOCKED_INSTANCE, get_fixture_path

pytestmark = pytest.mark.unit


def test_check_mock_weaviate_openmetrics(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('weaviate_openmetrics.txt'))
    check = WeaviateCheck('weaviate', {}, [OM_MOCKED_INSTANCE])
    dd_run_check(check)

    for metric in OM_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('weaviate.openmetrics.health', ServiceCheck.OK)


def test_check_mock_weaviate_nodes(aggregator, mock_http_response):
    mock_http_response(file_path=get_fixture_path('weaviate_nodes_api.json'))
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check._submit_node_metrics()

    for metric in API_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('weaviate.node.status', ServiceCheck.OK)


def test_check_failed_liveness(aggregator, mock_http_response):
    mock_http_response(status_code=404)
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check._submit_liveness_metrics()

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


def test_check_mock_weaviate_metadata(datadog_agent, mock_http_response):
    mock_http_response(file_path=get_fixture_path('weaviate_meta_api.json'))
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check.check_id = 'test:123'
    check._submit_version_metadata()
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


def test_node_status_values_mapping():
    # Kills the core/NumberReplacer mutants at check.py:20 that alter individual NODE_STATUS_VALUES entries.
    assert NODE_STATUS_VALUES == {'HEALTHY': 0, 'UNHEALTHY': 1, 'UNAVAILABLE': 2, 'UNKNOWN': 3}


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:24 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert WeaviateCheck.DEFAULT_METRIC_LIMIT == 0


def test_metadata_entrypoint_skipped_when_collection_disabled(datadog_agent, mock_http_response):
    # Kills the core/RemoveDecorator mutant at check.py:39 that drops @AgentCheck.metadata_entrypoint.
    mock_http_response(file_path=get_fixture_path('weaviate_meta_api.json'))
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check.check_id = 'test:123'
    datadog_agent._config['enable_metadata_collection'] = False
    check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_metadata_parses_version_with_more_than_three_parts(datadog_agent, mock_http_response):
    # Kills ReplaceComparisonOperator mutants at check.py:48 (>=3 -> ==3/<=3) and the
    # NumberReplacer mutant at check.py:49 (version_split[0] -> version_split[-1]).
    mock_http_response(json_data={'version': '2.5.9.1'})
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check.check_id = 'test:123'
    check._submit_version_metadata()

    datadog_agent.assert_metadata(
        'test:123',
        {
            'version.scheme': 'semver',
            'version.major': '2',
            'version.minor': '5',
            'version.patch': '9',
            'version.raw': '2.5.9',
        },
    )


def test_metadata_skips_version_with_fewer_than_three_parts(datadog_agent, mock_http_response):
    # Kills the core/NumberReplacer mutant at check.py:48 (>=3 -> >=2), which would index out of
    # range on a two-segment version instead of skipping it.
    mock_http_response(json_data={'version': '1.2'})
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check.check_id = 'test:123'
    check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_liveness_latency_value(mocker, aggregator, mock_http_response):
    # Kills the core/ReplaceBinaryOperator and core/NumberReplacer mutants at check.py:76 that
    # alter the latency formula `(end_time - start_time) * 1000` rounded to 2 decimals. end_time
    # is chosen as more than double start_time so `%` also diverges from `-`.
    mocker.patch('time.time', side_effect=[2.0, 9.500126])
    mock_http_response(status_code=200)
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check._submit_liveness_metrics()

    expected_latency = round_value((9.500126 - 2.0) * 1000, 2)
    aggregator.assert_metric('weaviate.http.latency_ms', value=expected_latency)


def test_node_metrics_use_zero_defaults_when_counts_missing(aggregator, mock_http_response):
    # Kills the core/NumberReplacer mutants at check.py:106, 107 and 113 that change the
    # 0 defaults for shardCount/objectCount to 1 or -1 when those keys are absent.
    node_data = {
        'nodes': [
            {
                'name': 'weaviate-0',
                'status': 'HEALTHY',
                'version': '1.0.0',
                'gitHash': 'abc123',
                'stats': {'unused': True},
                'shards': [{'name': 'shard-a', 'class': 'Foo'}],
            }
        ]
    }
    mock_http_response(json_data=node_data)
    check = WeaviateCheck('weaviate', {}, [MOCKED_INSTANCE])
    check._submit_node_metrics()

    aggregator.assert_metric('weaviate.node.stats.shards', value=0)
    aggregator.assert_metric('weaviate.node.stats.objects', value=0)
    aggregator.assert_metric('weaviate.node.shard.objects', value=0)
