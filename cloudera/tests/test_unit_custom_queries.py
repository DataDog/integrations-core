# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, fixture_query_time_series, dd_run_check_count,'
    ' expected_service_checks, expected_metrics',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'custom_queries': [{'query': "select foo"}]},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            {'exception': 'Exception running custom query'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 0}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'custom_queries': [{'query': "select foo"}]},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            {'category': 'cluster', 'metrics': {'cluster': ['foo']}, 'name': 'example'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 1}],
        ),
    ],
    ids=['exception running custom query', 'one custom query configured'],
    indirect=['cloudera_version', 'read_clusters', 'list_hosts', 'read_events', 'fixture_query_time_series'],
)
def test_custom_queries(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    list_hosts,
    read_events,
    fixture_query_time_series,
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
        side_effect=[fixture_query_time_series],
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
        for expected_service_check in expected_service_checks:
            aggregator.assert_service_check(
                'cloudera.can_connect',
                count=expected_service_check.get('count'),
                status=expected_service_check.get('status'),
                message=expected_service_check.get('message'),
                tags=expected_service_check.get('tags'),
            )
        for expected_metric in expected_metrics:
            aggregator.assert_metric("cloudera.cluster.foo", count=expected_metric.get('count'))
