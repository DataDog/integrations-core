# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, read_clusters, read_events, dd_run_check_count, expected_exception, '
    'expected_service_checks',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'bad_client'},
            {},
            {'number': 0},
            {'number': 0},
            1,
            pytest.raises(
                Exception,
                match='`cloudera_client` is unsupported or unknown: bad_client',
            ),
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
            {},
            {'number': 0},
            {'number': 0},
            1,
            pytest.raises(
                Exception,
                match='`cloudera_client` is unsupported or unknown: bad_client',
            ),
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `cloudera_client` is unsupported or unknown: bad_client',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'cm_client'},
            {'version': '7.0.0'},
            {'number': 0},
            {'number': 0},
            1,
            does_not_raise(),
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
    ],
    ids=['exception', 'exception with custom tags', 'cm_client'],
    indirect=['instance', 'cloudera_version', 'read_clusters', 'read_events'],
)
def test_client(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    read_clusters,
    read_events,
    dd_run_check_count,
    expected_exception,
    expected_service_checks,
):
    with expected_exception, mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        side_effect=[cloudera_version],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
        side_effect=[read_clusters],
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
