# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.checks.openmetrics.v2.base import OpenMetricsBaseCheckV2
from datadog_checks.base.utils.http import DEFAULT_OPENMETRICS_MAX_RESPONSE_SIZE

from ..payload_server import VALID_PAYLOAD, make_large_payload, serve_payload

MIB = 1024 * 1024


def get_check(url, **options):
    check = OpenMetricsBaseCheckV2(
        'test', {}, [{'openmetrics_endpoint': url, 'namespace': 'test', 'metrics': ['my_metric'], **options}]
    )
    check.check_id = 'test:123'
    return check


def get_limit(check):
    check.run_check_initializations()
    return check.scrapers[check.instance['openmetrics_endpoint']].http.max_response_size


def test_default_limit():
    assert get_limit(get_check('http://localhost:1/metrics')) == DEFAULT_OPENMETRICS_MAX_RESPONSE_SIZE * MIB


@pytest.mark.parametrize(
    'value, expected',
    [
        pytest.param(2, 2 * MIB, id='custom'),
        pytest.param(0, None, id='disabled'),
    ],
)
def test_configured_limit(value, expected):
    assert get_limit(get_check('http://localhost:1/metrics', max_response_size=value)) == expected


@pytest.mark.parametrize('compress', [True, False])
def test_payload_within_limit(aggregator, dd_run_check, compress):
    with serve_payload(VALID_PAYLOAD, compress=compress) as url:
        dd_run_check(get_check(url, max_response_size=1))

        aggregator.assert_metric('test.my_metric', 42, tags=[f'endpoint:{url}', 'foo:bar'])


@pytest.mark.parametrize('compress', [True, False])
def test_payload_exceeding_limit_without_newline(dd_run_check, compress):
    with serve_payload(make_large_payload(4 * MIB), compress=compress) as url:
        check = get_check(url, max_response_size=1)

        with pytest.raises(Exception, match='exceeds the maximum allowed size'):
            dd_run_check(check)
