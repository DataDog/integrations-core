# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from tests.common import query_time_series

from datadog_checks.base.types import ServiceCheck
from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_list_hosts_and_service_check_host_health(
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
                'cloudera.host.health',
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
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_list_hosts_and_host_metrics(
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
            for metric in NATIVE_METRICS['host']:
                aggregator.assert_metric(
                    f'cloudera.host.{metric}', count=expected.get('count'), tags=expected.get('native_tags')
                )
            for metric in TIMESERIES_METRICS['host']:
                aggregator.assert_metric(
                    f'cloudera.host.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, ' 'expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_list_hosts_and_role_metrics(
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
            for metric in TIMESERIES_METRICS['role']:
                aggregator.assert_metric(
                    f'cloudera.role.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_list',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'exception': 'Service not available'},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 0},
            {'number': 0},
            1,
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 1, 'prefix': ['cluster_'], 'status': ['GOOD_HEALTH']},
            {'number': 1, 'prefix': ['host_'], 'status': ['BAD_HEALTH'], 'rack_id': 'rack_id_0'},
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
            {'number': 0},
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
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_list_hosts_and_disk_metrics(
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
            for metric in TIMESERIES_METRICS['disk']:
                aggregator.assert_metric(
                    f'cloudera.disk.{metric}', count=expected.get('count'), tags=expected.get('ts_tags')
                )
