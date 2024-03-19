# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random

import mock
import pytest
from packaging.version import Version

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, query_time_series, expected_service_checks, expected_metrics',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'custom_queries': [{'query': "select foo"}]},
            Exception('Exception running custom query'),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'custom_queries': [{'query': "select foo"}]},
            [
                {
                    'metric': 'cluster.foo',
                    'value': random.uniform(0, 1000),
                    'tags': ['cloudera_cluster:cluster_0'],
                }
            ],
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 1, 'tags': ['cloudera_cluster:cluster_0']}],
        ),
    ],
    ids=['exception running custom query', 'one custom query configured'],
)
def test_custom_queries(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    query_time_series,
    expected_service_checks,
    expected_metrics,
):
    with mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        return_value=Version('7.0.0'),
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        return_value=[],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.query_time_series',
        side_effect=[query_time_series],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.list_hosts',
        return_value=[],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        return_value=[],
    ):
        check = cloudera_check(instance)
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
            aggregator.assert_metric(
                "cloudera.cluster.foo", count=expected_metric.get('count'), tags=expected_metric.get('tags')
            )
