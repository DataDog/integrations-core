# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.base.utils.remote_queries import timing as rq_timing
from datadog_checks.base.utils.remote_queries import upload as rq_upload


def test_agent_config_read_failure_logs_fixed_text_only(monkeypatch, caplog):
    """The config-reading helper swallows read failures into fixed debug text: the config
    layer's exception can quote configuration values."""
    caplog.set_level(logging.DEBUG)

    def broken_get_config(key):
        raise Exception('SECRET_DO_NOT_LOG in the config layer')

    monkeypatch.setattr(rq_upload.datadog_agent, 'get_config', broken_get_config)
    assert rq_upload.get_agent_config('api_key') == ''
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


@pytest.mark.parametrize('request_json', ['{"password": "SECRET_DO_NOT_LOG"', b'\xff'])
def test_parse_agent_rpc_request_rejects_malformed_json(request_json):
    request, timings, failure = rq_events.parse_agent_rpc_request(request_json)

    assert request is None
    assert failure is not None
    assert failure.event_type == 'error'
    metadata = failure.metadata
    assert metadata['status'] == 'FAILED'
    assert metadata['error'] == {
        'code': 'invalid_request',
        'message': 'Invalid remote query request: request_json must be a valid JSON object.',
        'retryable': False,
    }
    assert 'SECRET_DO_NOT_LOG' not in str(metadata)
    # Even a malformed request reports its measured wall: the diagnostics object holds
    # exactly the un-instrumented remainder.
    assert metadata['executionDiagnostics']['contractVersion'] == 1
    assert set(metadata['executionDiagnostics']['producer']) == {'totalMs', 'otherMs'}
    assert isinstance(timings, rq_timing.RemoteQueryProducerTimings)


@pytest.mark.parametrize('request_json', ['[]', 'null', '"SECRET_DO_NOT_LOG"', '1'])
def test_parse_agent_rpc_request_rejects_non_object_json(request_json):
    request, _, failure = rq_events.parse_agent_rpc_request(request_json)

    assert request is None
    assert failure is not None
    assert failure.metadata['error']['code'] == 'invalid_request'
    assert failure.metadata['error']['message'] == 'Invalid remote query request: request_json must be a JSON object.'
    assert 'SECRET_DO_NOT_LOG' not in str(failure.metadata)


VALID_REQUEST = {
    'operation': 'produce_json_pages',
    'target': {'host': 'LOCALHOST.', 'port': 5432, 'dbname': 'datadog_test'},
    'query': 'SELECT 1 AS value',
    'resultDelivery': {
        'runId': '383d34aa-0766-472f-9e27-9190d9a52ab6',
        'taskId': '603f58a7-04cf-4ffe-860b-3885457f885c',
        'artifactVersion': 1,
        'uploadId': 'upload-01k',
        'baseUrl': 'https://dd.datad0g.com/api/unstable/its-agent-intake',
        'limits': {
            'maxFileBytes': 1024,
            'maxResultBytes': 8192,
            'maxRowBytes': 64,
            'maxColumns': 8,
            'maxSchemaBytes': 256,
            'maxPages': 4,
            'timeoutMs': 5000,
        },
    },
}


def test_validate_request_accepts_an_arbitrary_valid_query():
    """Contract validation is the only request gate: any well-formed request, whatever its
    query text, is admitted."""
    request = dict(VALID_REQUEST, query="SELECT 'hello world' AS message")

    parsed = rq_events.validate_request(request)

    assert parsed.query == "SELECT 'hello world' AS message"


def test_emit_agent_rpc_events_closes_the_generator_on_a_callback_failure():
    """The generator's cleanup (page buffers, database resources) runs before the callback
    failure propagates."""
    cleanup = []

    def events():
        try:
            yield rq_contract.RemoteQueryEvent('metadata', {})
        finally:
            cleanup.append('closed')

    def emit(event_type, metadata_json, payload):
        raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        rq_events.emit_agent_rpc_events(emit, events())

    assert cleanup == ['closed']


@pytest.mark.parametrize(
    'is_cancelled, expect_cancelled',
    [
        (True, True),
        (lambda: True, True),
        (False, False),
        (lambda: False, False),
    ],
)
def test_raise_if_cancelled_honors_the_bool_and_callable_shapes(is_cancelled, expect_cancelled):
    check = SimpleNamespace(is_cancelled=is_cancelled)

    if expect_cancelled:
        with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
            rq_events.raise_if_cancelled(check)
        assert failure.value.code == 'cancelled'
        assert failure.value.retryable is True
    else:
        rq_events.raise_if_cancelled(check)


def test_raise_if_cancelled_ignores_a_check_without_a_cancel_hook():
    rq_events.raise_if_cancelled(SimpleNamespace())
