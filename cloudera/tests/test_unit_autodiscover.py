import mock
import pytest
from tests.common import query_time_series

from datadog_checks.base.types import ServiceCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_service_checks, '
    'expected_metrics',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': {'^cluster.*'}}},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Setting `include` must be an array',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag'], 'clusters': {'include': {'^cluster.*'}}},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Setting `include` must be an array',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': [[]]}},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `include` entries must be a map or a string',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag'], 'clusters': {'include': [[]]}},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `include` entries must be a map or a string',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': ['^cluster.*']}},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': ['^cluster.*']}},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_', 'cluster_new_'], 'status': ['GOOD_HEALTH', 'GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}']} for i in range(1)]
            + [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_new_{i}']} for i in range(1)],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'limit': 5, 'include': ['^cluster.*']}},
            {'version': '7.0.0'},
            {'number': 10, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}']} for i in range(5)]
            + [{'count': 0, 'ts_tags': [f'cloudera_cluster:cluster_{i}']} for i in range(5, 10)],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': ['.*'], 'exclude': ['^tmp_.*']}},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_', 'tmp_'], 'status': ['GOOD_HEALTH', 'GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}']} for i in range(1)]
            + [{'count': 0, 'ts_tags': [f'cloudera_cluster:tmp_{i}']} for i in range(1)],
        ),
        (
            {
                'api_url': 'http://localhost:8080/api/v48/',
                'clusters': {'include': [{'.*': {}}], 'exclude': ['^tmp_.*']},
            },
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_', 'tmp_'], 'status': ['GOOD_HEALTH', 'GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}']} for i in range(1)]
            + [{'count': 0, 'ts_tags': [f'cloudera_cluster:tmp_{i}']} for i in range(1)],
        ),
    ],
    ids=[
        'exception include type',
        'exception include type with custom tags',
        'exception include entry type',
        'exception include entry type with custom tags',
        'configured cluster autodiscover with zero clusters',
        'configured cluster autodiscover with two different prefix clusters',
        'configured cluster autodiscover with ten clusters and limit',
        'configured cluster autodiscover with two different prefix clusters and one of them excluded',
        'configured cluster autodiscover (with dict) with two different prefix clusters and one of them excluded',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_autodiscover_clusters(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
    read_events,
    dd_run_check_count,
    expected_service_checks,
    expected_metrics,
):
    with mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        side_effect=[cloudera_version],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        side_effect=[read_clusters],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.query_time_series',
        side_effect=query_time_series,
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.list_hosts',
        side_effect=[list_hosts, list_hosts, list_hosts, list_hosts, list_hosts],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        side_effect=[read_events],
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected_service_check in expected_service_checks:
            aggregator.assert_service_check(
                'cloudera.can_connect',
                count=expected_service_check.get('count'),
                status=expected_service_check.get('status'),
                message=expected_service_check.get('message'),
                tags=expected_service_check.get('tags'),
            )
        for expected_metric in expected_metrics:
            for metric in TIMESERIES_METRICS['cluster']:
                aggregator.assert_metric(
                    f'cloudera.cluster.{metric}',
                    count=expected_metric.get('count'),
                    tags=expected_metric.get('ts_tags'),
                )
