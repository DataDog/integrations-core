# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
from packaging.version import Version

from datadog_checks.base.types import ServiceCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS
from tests.common import query_time_series

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, read_clusters, expected_can_connects, expected_cluster_healths, expected_metrics',
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
            [{'name': 'cluster_0', 'entity_status': 'BAD_HEALTH'}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_0']}],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {
                    'name': 'cluster_0',
                    'entity_status': 'BAD_HEALTH',
                    'tags': [{'name': 'tag_0', 'value': 'value_0'}],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_0', 'tag_0:value_0']}],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0', 'tag_0:value_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [{'name': 'cluster_0', 'entity_status': 'BAD_HEALTH'}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [{'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [{'name': 'cluster_0', 'entity_status': 'GOOD_HEALTH'}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_0']}],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {
                    'name': 'cluster_0',
                    'entity_status': 'GOOD_HEALTH',
                    'tags': [{'name': 'tag_0', 'value': 'value_0'}],
                }
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_0', 'tag_0:value_0']}],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0', 'tag_0:value_0']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [{'name': 'cluster_0', 'entity_status': 'GOOD_HEALTH'}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {'name': 'cluster_0', 'entity_status': 'BAD_HEALTH'},
                {'name': 'cluster_1', 'entity_status': 'BAD_HEALTH'},
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_0']},
                {'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_1']},
            ],
            [
                {'count': 1, 'tags': ['cloudera_cluster:cluster_0']},
                {'count': 1, 'tags': ['cloudera_cluster:cluster_1']},
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [
                {'name': 'cluster_0', 'entity_status': 'BAD_HEALTH'},
                {'name': 'cluster_1', 'entity_status': 'BAD_HEALTH'},
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [
                {'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']},
                {'count': 1, 'status': ServiceCheck.CRITICAL, 'tags': ['cloudera_cluster:cluster_1', 'new_tag']},
            ],
            [
                {'count': 1, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']},
                {'count': 1, 'tags': ['cloudera_cluster:cluster_1', 'new_tag']},
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            [
                {'name': 'cluster_0', 'entity_status': 'GOOD_HEALTH'},
                {'name': 'cluster_1', 'entity_status': 'GOOD_HEALTH'},
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_0']},
                {'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_1']},
            ],
            [
                {'count': 1, 'tags': ['cloudera_cluster:cluster_0']},
                {'count': 1, 'tags': ['cloudera_cluster:cluster_1']},
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            [
                {'name': 'cluster_0', 'entity_status': 'GOOD_HEALTH'},
                {'name': 'cluster_1', 'entity_status': 'GOOD_HEALTH'},
            ],
            [{'count': 1, 'status': ServiceCheck.OK, 'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag']}],
            [
                {'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']},
                {'count': 1, 'status': ServiceCheck.OK, 'tags': ['cloudera_cluster:cluster_1', 'new_tag']},
            ],
            [
                {'count': 1, 'tags': ['cloudera_cluster:cluster_0', 'new_tag']},
                {'count': 1, 'tags': ['cloudera_cluster:cluster_1', 'new_tag']},
            ],
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
        'two clusters with bad health',
        'two clusters with bad health and custom tags',
        'two clusters with good health',
        'two clusters with good health and custom tags',
    ],
)
def test_read_clusters(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    read_clusters,
    expected_can_connects,
    expected_cluster_healths,
    expected_metrics,
):
    with mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        return_value=Version('7.0.0'),
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        side_effect=[read_clusters],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.query_time_series',
        side_effect=query_time_series,
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.list_hosts',
        return_value=[],
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
        for expected_cluster_health in expected_cluster_healths:
            aggregator.assert_service_check(
                'cloudera.cluster.health',
                count=expected_cluster_health.get('count'),
                status=expected_cluster_health.get('status'),
                message=expected_cluster_health.get('message'),
                tags=expected_cluster_health.get('tags'),
            )
        for expected_metric in expected_metrics:
            for metric in TIMESERIES_METRICS['cluster']:
                aggregator.assert_metric(
                    f'cloudera.cluster.{metric}', count=expected_metric.get('count'), tags=expected_metric.get('tags')
                )
