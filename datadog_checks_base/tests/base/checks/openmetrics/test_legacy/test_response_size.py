# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.utils.http import DEFAULT_OPENMETRICS_MAX_RESPONSE_SIZE, ResponseSizeLimitExceeded

from ..payload_server import VALID_PAYLOAD, make_large_payload, serve_payload

MIB = 1024 * 1024


def get_check(url, **options):
    instance = {
        'prometheus_url': url,
        'namespace': 'test',
        'metrics': [{'my_metric': 'my_metric'}],
        **options,
    }
    check = OpenMetricsBaseCheck('openmetrics_check', {}, [instance])
    check.check_id = 'test:123'
    return check, instance


def test_default_limit():
    check, instance = get_check('http://localhost:1/metrics')
    handler = check.get_http_handler(check.get_scraper_config(instance))

    assert handler.max_response_size == DEFAULT_OPENMETRICS_MAX_RESPONSE_SIZE * MIB


@pytest.mark.parametrize(
    'value, expected',
    [
        pytest.param(2, 2 * MIB, id='custom'),
        pytest.param(0, None, id='disabled'),
    ],
)
def test_configured_limit(value, expected):
    check, instance = get_check('http://localhost:1/metrics', max_response_size=value)
    handler = check.get_http_handler(check.get_scraper_config(instance))

    assert handler.max_response_size == expected


@pytest.mark.parametrize('compress', [True, False])
def test_payload_within_limit(aggregator, compress):
    with serve_payload(VALID_PAYLOAD, compress=compress) as url:
        check, instance = get_check(url, max_response_size=1)
        check.check(instance)

    aggregator.assert_metric('test.my_metric', 42, tags=['foo:bar'])


@pytest.mark.parametrize('compress', [True, False])
def test_payload_exceeding_limit_without_newline(aggregator, compress):
    with serve_payload(make_large_payload(4 * MIB), compress=compress) as url:
        check, instance = get_check(url, max_response_size=1)

        with pytest.raises(ResponseSizeLimitExceeded, match='exceeds the maximum allowed size'):
            check.check(instance)


def test_payload_exceeding_limit_with_telemetry(aggregator):
    # The size of the response must be bounded regardless of the `telemetry` option
    with serve_payload(make_large_payload(4 * MIB)) as url:
        check, instance = get_check(url, max_response_size=1, telemetry=True)

        with pytest.raises(ResponseSizeLimitExceeded):
            check.check(instance)


def test_limit_disabled(aggregator):
    body = VALID_PAYLOAD + b'# TYPE other gauge\n' + b'other{padding="' + make_large_payload(2 * MIB) + b'"} 1\n'
    with serve_payload(body) as url:
        check, instance = get_check(url, max_response_size=0, metrics=[{'my_metric': 'my_metric'}, {'other': 'other'}])
        check.check(instance)

    aggregator.assert_metric('test.my_metric', 42, tags=['foo:bar'])
