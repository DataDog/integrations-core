# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext as does_not_raise

import mock
import pytest

from datadog_checks.base.types import ServiceCheck

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    'instance, expected_exception, expected_service_checks',
    [
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'bad_client'},
            pytest.raises(
                Exception,
                match='`cloudera_client` is unsupported or unknown: bad_client',
            ),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `cloudera_client` is unsupported or unknown: bad_client',
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'bad_client', 'tags': ['new_tag']},
            pytest.raises(
                Exception,
                match='`cloudera_client` is unsupported or unknown: bad_client',
            ),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.CRITICAL,
                    'message': 'Cloudera API Client is none: `cloudera_client` is unsupported or unknown: bad_client',
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            does_not_raise(),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag']},
            does_not_raise(),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'cloudera_client': 'cm_client'},
            does_not_raise(),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['new_tag'], 'cloudera_client': 'cm_client'},
            does_not_raise(),
            [
                {
                    'count': 1,
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'new_tag'],
                }
            ],
        ),
    ],
    ids=[
        'exception',
        'exception with custom tags',
        'cloudera_client by default',
        'cloudera_client by default with custom tags',
        'cloudera_client cm_client',
        'cloudera_client cm_client with custom tags',
    ],
)
@pytest.mark.usefixtures('cloudera_cm_client')
def test_client(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    expected_exception,
    expected_service_checks,
):
    with expected_exception:
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


def test_client_ssl(dd_run_check, cloudera_check, cloudera_cm_client):
    instance = {
        'api_url': 'http://localhost:8080/api/v48/',
        'cloudera_client': 'cm_client',
        'verify_ssl': True,
        'ssl_ca_cert': 'ssl_ca_cert_path',
        'cert_file': 'cert_file_path',
        'key_file': 'key_file_path',
    }
    check = cloudera_check(instance)
    dd_run_check(check)
    cloudera_cm_client.assert_called_once_with(
        mock.ANY,
        api_url='http://localhost:8080/api/v48/',
        workload_username='~',
        workload_password='~',
        pools_size=4,
        max_parallel_requests=4,
        verify_ssl=True,
        ssl_ca_cert='ssl_ca_cert_path',
        cert_file='cert_file_path',
        key_file='key_file_path',
    )
