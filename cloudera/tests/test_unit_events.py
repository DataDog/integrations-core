# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import mock
import pytest
from packaging.version import Version

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, read_events, expected_service_checks, expected_events',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            Exception('Exception reading events'),
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
            Exception('Exception reading events'),
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
            [],
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
            {'number': 0},
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
            [{'msg_text': 'content_0'}],
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
            [{'msg_text': 'content_0'}],
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
)
def test_events(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    read_events,
    expected_service_checks,
    expected_events,
):
    with mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        return_value=Version('7.0.0'),
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        return_value=[],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.query_time_series',
        return_value=[],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.list_hosts',
        return_value=[],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_events',
        side_effect=[read_events],
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
        for expected_event in expected_events:
            aggregator.assert_event(expected_event.get('msg_text'), count=expected_event.get('count'))
