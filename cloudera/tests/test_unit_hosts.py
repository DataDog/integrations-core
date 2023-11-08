# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
import string

import mock
import pytest
from packaging.version import Version

from datadog_checks.base.types import ServiceCheck
from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS
from tests.common import query_time_series

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, list_hosts, expected_can_connects, expected_host_healths, expected_metrics',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            Exception('Service not available'),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera check raised an exception: Service not available',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 0}],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            Exception('Service not available'),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera check raised an exception: Service not available',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
            [{'count': 0}],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 0}],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [{'count': 0}],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {
                    'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                    'name': 'host_0',
                    'entity_status': 'BAD_HEALTH',
                    'num_cores': 8,
                    'num_physical_cores': 8,
                    'total_phys_mem_bytes': 33079799808,
                    'rack_id': 'rack_id_0',
                    'tags': [],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'tags': ['cloudera_cluster:cluster_0', 'cloudera_hostname:host_0', 'cloudera_rack_id:rack_id_0'],
                }
            ],
            [
                {
                    'count': 1,
                    'tags': ['cloudera_cluster:cluster_0', 'cloudera_hostname:host_0', 'cloudera_rack_id:rack_id_0'],
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'cloudera_host:host_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {
                    'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                    'name': 'host_0',
                    'entity_status': 'BAD_HEALTH',
                    'num_cores': 8,
                    'num_physical_cores': 8,
                    'total_phys_mem_bytes': 33079799808,
                    'rack_id': 'rack_id_0',
                    'tags': [{'name': 'tag_0', 'value': 'value_0'}],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'tag_0:value_0',
                    ],
                }
            ],
            [
                {
                    'count': 1,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'tag_0:value_0',
                    ],
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'cloudera_host:host_0',
                        'tag_0:value_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [
                {
                    'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                    'name': 'host_0',
                    'entity_status': 'BAD_HEALTH',
                    'num_cores': 8,
                    'num_physical_cores': 8,
                    'total_phys_mem_bytes': 33079799808,
                    'rack_id': 'rack_id_0',
                    'tags': [],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'new_tag',
                    ],
                }
            ],
            [
                {
                    'count': 1,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'new_tag',
                    ],
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'cloudera_host:host_0',
                        'new_tag',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {
                    'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                    'name': 'host_0',
                    'entity_status': 'GOOD_HEALTH',
                    'num_cores': 8,
                    'num_physical_cores': 8,
                    'total_phys_mem_bytes': 33079799808,
                    'rack_id': 'rack_id_0',
                    'tags': [],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['cloudera_cluster:cluster_0', 'cloudera_hostname:host_0', 'cloudera_rack_id:rack_id_0'],
                }
            ],
            [
                {
                    'count': 1,
                    'tags': ['cloudera_cluster:cluster_0', 'cloudera_hostname:host_0', 'cloudera_rack_id:rack_id_0'],
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'cloudera_host:host_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {
                    'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                    'name': 'host_0',
                    'entity_status': 'GOOD_HEALTH',
                    'num_cores': 8,
                    'num_physical_cores': 8,
                    'total_phys_mem_bytes': 33079799808,
                    'rack_id': 'rack_id_0',
                    'tags': [{'name': 'tag_0', 'value': 'value_0'}],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'tag_0:value_0',
                    ],
                }
            ],
            [
                {
                    'count': 1,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'tag_0:value_0',
                    ],
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'cloudera_host:host_0',
                        'tag_0:value_0',
                    ],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [
                {
                    'host_id': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                    'name': 'host_0',
                    'entity_status': 'GOOD_HEALTH',
                    'num_cores': 8,
                    'num_physical_cores': 8,
                    'total_phys_mem_bytes': 33079799808,
                    'rack_id': 'rack_id_0',
                    'tags': [],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'new_tag',
                    ],
                }
            ],
            [
                {
                    'count': 1,
                    'tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'new_tag',
                    ],
                    'ts_tags': [
                        'cloudera_cluster:cluster_0',
                        'cloudera_hostname:host_0',
                        'cloudera_rack_id:rack_id_0',
                        'cloudera_host:host_0',
                        'new_tag',
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
)
def test_list_hosts(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    list_hosts,
    expected_can_connects,
    expected_host_healths,
    expected_metrics,
):
    with mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        return_value=Version('7.0.0'),
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        return_value=[{'name': 'cluster_0', 'entity_status': 'GOOD_HEALTH'}],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.query_time_series',
        side_effect=query_time_series,
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.list_hosts',
        side_effect=[list_hosts],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        return_value=[],
    ):
        check = cloudera_check(instance)
        dd_run_check(check)
        for expected_can_connect in expected_can_connects:
            aggregator.assert_service_check(
                'cloudera.can_connect',
                count=expected_can_connect.get('count'),
                status=expected_can_connect.get('status'),
                message=expected_can_connect.get('message'),
                tags=expected_can_connect.get('tags'),
            )
        for expected_host_health in expected_host_healths:
            aggregator.assert_service_check(
                'cloudera.host.health',
                count=expected_host_health.get('count'),
                status=expected_host_health.get('status'),
                message=expected_host_health.get('message'),
                tags=expected_host_health.get('tags'),
            )
        for expected_metric in expected_metrics:
            for metric in NATIVE_METRICS['host']:
                aggregator.assert_metric(
                    f'cloudera.host.{metric}', count=expected_metric.get('count'), tags=expected_metric.get('tags')
                )
            for metric in TIMESERIES_METRICS['host']:
                aggregator.assert_metric(
                    f'cloudera.host.{metric}', count=expected_metric.get('count'), tags=expected_metric.get('ts_tags')
                )
