# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS

# from datadog_checks.dev.utils import get_metadata_metrics
#
# from .common import CAN_CONNECT_TAGS, CLUSTER_1_HEALTH_TAGS, CLUSTER_TMP_HEALTH_TAGS, METRICS
# from .conftest import get_timeseries_resource
# from .conftest import query_time_series
from .common import query_time_series

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'bad_client'},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `cloudera_client` is unsupported or unknown: bad_client',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'bad_client', 'tags': ['new_tag']},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `cloudera_client` is unsupported or unknown: bad_client',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
    ],
    indirect=['instance'],
)
def test_client_and_service_check_can_connect(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    dd_run_check_count,
    expected_list,
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
    'instance, cloudera_version, read_clusters, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Service not available',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Service not available',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown: None',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown: None',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '5.0.0'},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown: 5.0.0',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '5.0.0'},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: Cloudera Manager Version is unsupported or unknown: 5.0.0',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
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
        'none',
        'none with custom tags',
        'unsupported',
        'unsupported with custom tags',
        'supported',
        'supported with custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters'],
)
def test_version_and_service_check_can_connect(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    dd_run_check_count,
    expected_list,
):
    with mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        side_effect=[cloudera_version],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        side_effect=[read_clusters],
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
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
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
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
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
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
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
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_read_clusters_and_service_check_can_connect(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
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
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            1,
            [{'status': ServiceCheck.CRITICAL, 'message': None, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH'], 'tags_number': 1},
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
            1,
            [{'status': ServiceCheck.CRITICAL, 'message': None, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_read_clusters_and_service_check_cluster_health(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
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
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)]}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH'], 'tags_number': 1},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['tag_0:value_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['BAD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['new_tag']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)]}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1},
            {'number': 0},
            1,
            [{'count': 1, 'ts_tags': [f'cloudera_cluster:cluster_{i}' for i in range(1)] + ['tag_0:value_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_read_clusters_and_cluster_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in TIMESERIES_METRICS['cluster']:
                aggregator.assert_metric(
                    f'cloudera.cluster.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': None,
                    'tags': ['cloudera_cluster:cluster_0', 'cloudera_hostname:host_0', 'cloudera_rack_id:rack_id_0'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': None,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': None,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': ['cloudera_cluster:cluster_0', 'cloudera_hostname:host_0', 'cloudera_rack_id:rack_id_0'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ],
                }
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero hosts',
        'zero hosts with custom tags',
        'one host with bad health',
        'one host with bad health and one tag',
        'one host with bad health and custom tags',
        'one host with good health',
        'one host with good health and one tag',
        'one host with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_list_hosts_and_service_check_host_health(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            aggregator.assert_service_check(
                'cloudera.host.health',
                count=expected.get('count'),
                status=expected.get('status'),
                message=expected.get('message'),
                tags=expected.get('tags'),
            )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'native_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_host:host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'native_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_host:host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'native_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_host:host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'native_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_host:host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'native_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_host:host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'native_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_host:host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero hosts',
        'zero hosts with custom tags',
        'one host with bad health',
        'one host with bad health and one tag',
        'one host with bad health and custom tags',
        'one host with good health',
        'one host with good health and one tag',
        'one host with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_list_hosts_and_host_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in NATIVE_METRICS['host']:
                aggregator.assert_metric(
                    f'cloudera.host.{metric}', count=expected.get('count'), tags=expected.get('native_tags')
                )
            for metric in TIMESERIES_METRICS['host']:
                aggregator.assert_metric(
                    f'cloudera.host.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, ' 'expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_role:role_host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_role:role_host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_role:role_host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_role:role_host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_role:role_host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_role:role_host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero hosts',
        'zero hosts with custom tags',
        'one host with bad health',
        'one host with bad health and one tag',
        'one host with bad health and custom tags',
        'one host with good health',
        'one host with good health and one tag',
        'one host with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_list_hosts_and_role_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in TIMESERIES_METRICS['role']:
                aggregator.assert_metric(
                    f'cloudera.role.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, ' 'expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_disk:disk_host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_disk:disk_host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_disk:disk_host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_disk:disk_host_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'tags_number': 1, 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_disk:disk_host_0',
                        'tag_0:value_0',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['GOOD_HEALTH'], 'rack_id': 'rack_id_0'},
            1,
            [
                {
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_disk:disk_host_0',
                        'new_tag',
                        'cloudera_rack_id:rack_id_0',
                    ]
                },
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero hosts',
        'zero hosts with custom tags',
        'one host with bad health',
        'one host with bad health and one tag',
        'one host with bad health and custom tags',
        'one host with good health',
        'one host with good health and one tag',
        'one host with good health and custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_list_hosts_and_disk_metrics(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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
    ):
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected in expected_list:
            for metric in TIMESERIES_METRICS['disk']:
                aggregator.assert_metric(
                    f'cloudera.disk.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, dd_run_check_count, expected_service_checks, '
    'expected_metrics',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': {'^cluster.*'}}},
            {'version': '7.0.0'},
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
            1,
            [{'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'clusters': {'include': ['^cluster.*']}},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_', 'cluster_new_'], 'status': ['GOOD_HEALTH', 'GOOD_HEALTH']},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts'],
)
def test_autodiscover_clusters(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
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


#
# @pytest.mark.parametrize('cloudera_api_exception', ['Service not available'], indirect=True)
# def test_given_cloudera_check_when_v7_read_clusters_exception_from_cloudera_client_then_emits_critical_service(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     cloudera_version_7_0_0,
#     cloudera_api_exception,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         side_effect=cloudera_api_exception,
#     ):
#         # Given
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#     aggregator.assert_service_check(
#         'cloudera.can_connect',
#         AgentCheck.CRITICAL,
#         tags=CAN_CONNECT_TAGS,
#         message="Cloudera check raised an exception: (Service not available)\nReason: None\n",
#     )
#
#
# def test_given_cloudera_check_when_bad_health_cluster_then_emits_cluster_health_critical(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     cloudera_version_7_0_0,
#     list_one_cluster_bad_health_resource,
#     list_hosts_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_one_cluster_bad_health_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ):
#         # Given
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         aggregator.assert_service_check(
#             'cloudera.cluster.health',
#             AgentCheck.CRITICAL,
#             message='BAD_HEALTH',
#             tags=CLUSTER_1_HEALTH_TAGS,
#         )
#         aggregator.assert_service_check(
#             'cloudera.can_connect',
#             AgentCheck.OK,
#             tags=CAN_CONNECT_TAGS,
#         )
#
#
# def test_given_cloudera_check_when_good_health_cluster_then_emits_cluster_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     cloudera_version_7_0_0,
#     list_one_cluster_good_health_resource,
#     list_hosts_resource,
#     read_events_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_one_cluster_good_health_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         return_value=read_events_resource,
#     ):
#         # Given
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         for category, metrics in METRICS.items():
#             for metric in metrics:
#                 aggregator.assert_metric(f'cloudera.{category}.{metric}')
#
#         aggregator.assert_service_check(
#             'cloudera.can_connect',
#             AgentCheck.OK,
#             tags=CAN_CONNECT_TAGS,
#         )
#         aggregator.assert_service_check(
#             'cloudera.cluster.health',
#             AgentCheck.OK,
#             tags=CLUSTER_1_HEALTH_TAGS,
#         )
#         expected_msg_text = (
#             'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient '
#             'has thrown exception, unwinding now'
#         )
#
#         aggregator.assert_event(msg_text=expected_msg_text, count=1)
#         aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
#         aggregator.assert_all_metrics_covered()
#
#
# def test_given_cloudera_check_when_no_events_response_then_no_event_collection(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     cloudera_version_7_0_0,
#     list_one_cluster_good_health_resource,
#     list_hosts_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_one_cluster_good_health_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         side_effect=Exception,
#     ):
#         # Given
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         aggregator.assert_service_check(
#             'cloudera.can_connect',
#             AgentCheck.OK,
#             tags=CAN_CONNECT_TAGS,
#         )
#         expected_content = (
#             'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient '
#             'has thrown exception, unwinding now'
#         )
#         # verify that event is not collected, but check still works normally
#         aggregator.assert_event(msg_text=expected_content, count=0)
#
#
# def test_autodiscover_configured_include_not_array_then_exception_is_raised(
#     dd_run_check,
#     cloudera_check,
#     instance_autodiscover_include_not_array,
#     cloudera_version_7_0_0,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), pytest.raises(
#         Exception,
#         match='Setting `include` must be an array',
#     ):
#         check = cloudera_check(instance_autodiscover_include_not_array)
#         dd_run_check(check)
#
#
# def test_given_cloudera_check_when_autodiscover_configured_with_one_entry_dict_then_emits_configured_cluster_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance_autodiscover_include_with_one_entry_dict,
#     cloudera_version_7_0_0,
#     list_two_clusters_with_one_tmp_resource,
#     list_hosts_resource,
#     read_events_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_two_clusters_with_one_tmp_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         return_value=read_events_resource,
#     ):
#         # Given
#         check = cloudera_check(instance_autodiscover_include_with_one_entry_dict)
#         # When
#         dd_run_check(check)
#         # Then
#         for category, metrics in METRICS.items():
#             for metric in metrics:
#                 aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
#         aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
#         aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)
#
#
# def test_autodiscover_configured_with_two_entries_dict_then_emits_configured_cluster_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance_autodiscover_include_with_two_entries_dict,
#     cloudera_version_7_0_0,
#     list_two_clusters_with_one_tmp_resource,
#     list_hosts_resource,
#     read_events_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_two_clusters_with_one_tmp_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         return_value=read_events_resource,
#     ):
#         # Given
#         check = cloudera_check(instance_autodiscover_include_with_two_entries_dict)
#         # When
#         dd_run_check(check)
#         # Then
#         for category, metrics in METRICS.items():
#             for metric in metrics:
#                 aggregator.assert_metric(f'cloudera.{category}.{metric}', count=2)
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
#         aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
#         aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)
#         aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_TMP_HEALTH_TAGS,
#         count=1)
#
#
# def test_given_cloudera_check_when_autodiscover_configured_with_str_then_emits_configured_cluster_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance_autodiscover_include_with_str,
#     cloudera_version_7_0_0,
#     list_two_clusters_with_one_tmp_resource,
#     list_hosts_resource,
#     read_events_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_two_clusters_with_one_tmp_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         return_value=read_events_resource,
#     ):
#         # Given
#         check = cloudera_check(instance_autodiscover_include_with_str)
#         # When
#         dd_run_check(check)
#         # Then
#         for category, metrics in METRICS.items():
#             for metric in metrics:
#                 aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
#         aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
#         aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)
#
#
# def test_given_cloudera_check_when_autodiscover_exclude_configured_then_emits_configured_cluster_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance_autodiscover_exclude,
#     cloudera_version_7_0_0,
#     list_two_clusters_with_one_tmp_resource,
#     list_hosts_resource,
#     read_events_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_two_clusters_with_one_tmp_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         return_value=read_events_resource,
#     ):
#         # Given
#         check = cloudera_check(instance_autodiscover_exclude)
#         # When
#         dd_run_check(check)
#         # Then
#         for category, metrics in METRICS.items():
#             for metric in metrics:
#                 aggregator.assert_metric(f'cloudera.{category}.{metric}', count=1)
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
#         aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
#         aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=1)
#
#
# def test_given_cloudera_check_when_autodiscover_empty_clusters_then_emits_zero_cluster_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance_autodiscover_include_with_one_entry_dict,
#     cloudera_version_7_0_0,
#     list_empty_clusters_resource,
#     list_hosts_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_empty_clusters_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ):
#         # Given
#         check = cloudera_check(instance_autodiscover_include_with_one_entry_dict)
#         # When
#         dd_run_check(check)
#         # Then
#         for category, metrics in METRICS.items():
#             for metric in metrics:
#                 aggregator.assert_metric(f'cloudera.{category}.{metric}', count=0)
#
#         aggregator.assert_service_check('cloudera.can_connect', AgentCheck.OK, tags=CAN_CONNECT_TAGS)
#         aggregator.assert_service_check('cloudera.cluster.health', AgentCheck.OK, tags=CLUSTER_1_HEALTH_TAGS, count=0)
#
#
# def test_given_custom_queries_then_retrieve_metrics_unit(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     list_one_cluster_good_health_resource,
#     cloudera_version_7_0_0,
#     instance,
#     get_custom_timeseries_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_one_cluster_good_health_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         return_value=get_custom_timeseries_resource,
#     ):
#         # Given
#         instance['custom_queries'] = [
#             {'query': "select foo"},  # foo is given category of cluster in common.py
#         ]
#
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         aggregator.assert_metric("cloudera.cluster.foo")
