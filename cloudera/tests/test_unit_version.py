# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext as does_not_raise

import mock
import pytest
from packaging.version import Version

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, cloudera_version, expected_exception, expected_service_checks',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            Exception('Service not available'),
            pytest.raises(
                Exception,
                match='Service not available',
            ),
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
            Exception('Service not available'),
            pytest.raises(
                Exception,
                match='Service not available',
            ),
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
            None,
            pytest.raises(
                Exception,
                match='Cloudera Manager Version is unsupported or unknown: None',
            ),
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
            None,
            pytest.raises(
                Exception,
                match='Cloudera Manager Version is unsupported or unknown: None',
            ),
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
            Version('5.0.0'),
            pytest.raises(
                Exception,
                match='Cloudera Manager Version is unsupported or unknown: 5.0.0',
            ),
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
            Version('5.0.0'),
            pytest.raises(
                Exception,
                match='Cloudera Manager Version is unsupported or unknown: 5.0.0',
            ),
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
            Version('7.0.0'),
            does_not_raise(),
            [{'status': ServiceCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            Version('7.0.0'),
            does_not_raise(),
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
)
def test_version(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    cloudera_version,
    expected_exception,
    expected_service_checks,
):
    with expected_exception, mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.get_version',
        side_effect=[cloudera_version],
    ), mock.patch(
        'datadog_checks.cloudera.client.cm_client.CmClient.read_clusters',
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
