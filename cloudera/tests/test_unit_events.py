# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import mock
import pytest
from tests.common import query_time_series

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, list_hosts, read_events, dd_run_check_count, expected_service_checks, '
    'expected_events',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'exception': 'Exception reading events'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'exception': 'Exception reading events'},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
            [],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {'number': 0},
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [],
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
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
            [],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {
                'number': 1,
                'content': ['content_'],
            },
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [{'count': 1, 'msg_text': f'content_{i}'} for i in range(1)],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            {
                'number': 1,
                'content': ['content_'],
            },
            1,
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
            [{'count': 1, 'msg_text': f'content_{i}'} for i in range(1)],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'zero events',
        'zero events with custom tags',
        'one event',
        'one event with custom tags',
    ],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'list_hosts', 'read_events'],
)
def test_events(
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
    expected_events,
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
        for expected_service_check in expected_service_checks:
            aggregator.assert_service_check(
                'cloudera.can_connect',
                count=expected_service_check.get('count'),
                status=expected_service_check.get('status'),
                message=expected_service_check.get('message'),
                tags=expected_service_check.get('tags'),
            )
        for expected_event in expected_events:
            aggregator.assert_event(expected_event.get('msg_text'), count=expected_event.get('count'))
