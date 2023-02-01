import mock
import pytest
from tests.common import query_time_series

from datadog_checks.base.types import ServiceCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera check raised an exception: Service not available',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera check raised an exception: Service not available',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero clusters',
        'zero clusters with custom tags',
        'one cluster with bad health',
        'one cluster with bad health and custom tags',
        'one cluster with good health',
        'one cluster with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_read_clusters_and_service_check_can_connect(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
    read_events,
    dd_run_check_count,
    expected_list,
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
        side_effect=[list_hosts],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        side_effect=[read_events],
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            aggregator.assert_service_check(
                'cloudera.can_connect',
                count=expected.get('count'),
                status=expected.get('status'),
                message=expected.get('message'),
                tags=expected.get('tags'),
            )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.CRITICAL, 'message': None, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH'], 'tags_number': 1},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': None,
                    'tags': ['cloudera_cluster:cluster_0', 'tag_0:value_0'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.CRITICAL, 'message': None, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': ['cloudera_cluster:cluster_0', 'tag_0:value_0'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero clusters',
        'zero clusters with custom tags',
        'one cluster with bad health',
        'one cluster with bad health and one tag',
        'one cluster with bad health and custom tags',
        'one cluster with good health',
        'one cluster with good health and one tag',
        'one cluster with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_read_clusters_and_service_check_cluster_health(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
    read_events,
    dd_run_check_count,
    expected_list,
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
        side_effect=[list_hosts],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        side_effect=[read_events],
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            aggregator.assert_service_check(
                'cloudera.cluster.health',
                count=expected.get('count'),
                status=expected.get('status'),
                message=expected.get('message'),
                tags=expected.get('tags'),
            )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)]}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH'], 'tags_number': 1},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['tag_0:value_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['new_tag']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)]}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['tag_0:value_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['new_tag']}],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero clusters',
        'zero clusters with custom tags',
        'one cluster with bad health',
        'one cluster with bad health and one tag',
        'one cluster with bad health and custom tags',
        'one cluster with good health',
        'one cluster with good health and one tag',
        'one cluster with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_read_clusters_and_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
    read_events,
    dd_run_check_count,
    expected_list,
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
        side_effect=[list_hosts],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        side_effect=[read_events],
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in TIMESERIES_METRICS['cluster']:
                aggregator.assert_metric(
                    f'cloudera.cluster.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )
