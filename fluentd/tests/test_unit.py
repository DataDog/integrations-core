# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
from datadog_checks.base.stubs.http import FakeHTTPClient
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientError, HTTPClientTimeoutError
from datadog_checks.fluentd import Fluentd

pytestmark = pytest.mark.unit

ENDPOINT = 'http://localhost:24220/api/plugins.json'
CONFIG_ENDPOINT = 'http://localhost:24220/api/config.json'
INSTANCE = {'monitor_agent_url': ENDPOINT, 'tags': ['custom:test']}


@pytest.mark.parametrize('metadata_status', [200, 503])
def test_plugins_and_optional_metadata(
    aggregator: AggregatorStub,
    fake_http: FakeHTTPClient,
    fake_http_response: Callable,
    mocker: MockerFixture,
    datadog_agent: DatadogAgentStub,
    metadata_status: int,
):
    fake_http_response(ENDPOINT, json_data={'plugins': [{'plugin_id': 'output', 'retry_count': 3}]})
    fake_http_response(CONFIG_ENDPOINT, json_data={'version': '1.18.0'}, status_code=metadata_status)
    check = Fluentd('fluentd', {}, [INSTANCE])
    check.check_id = 'test:123'
    mocker.patch.object(check, '_get_version_from_command_line', return_value='1.17.0')

    check.check(None)

    aggregator.assert_metric('fluentd.retry_count', value=3, tags=['plugin_id:output', 'custom:test'])
    aggregator.assert_service_check('fluentd.is_ok', Fluentd.OK, count=1)
    datadog_agent.assert_metadata('test:123', {'version.raw': '1.18.0' if metadata_status == 200 else '1.17.0'})
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', ENDPOINT), ('GET', CONFIG_ENDPOINT)]


@pytest.mark.parametrize('error_type', [HTTPClientConnectionError, HTTPClientTimeoutError])
def test_plugins_unavailable(aggregator: AggregatorStub, fake_http: FakeHTTPClient, error_type: type[HTTPClientError]):
    fake_http.register_response('GET', ENDPOINT, error_type('Monitor unavailable'))
    check = Fluentd('fluentd', {}, [INSTANCE])

    with pytest.raises(error_type, match='Monitor unavailable'):
        check.check(None)

    aggregator.assert_service_check('fluentd.is_ok', Fluentd.CRITICAL, count=1)
    aggregator.assert_all_metrics_covered()
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', ENDPOINT)]
