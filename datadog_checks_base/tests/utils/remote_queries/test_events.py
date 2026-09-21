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


@pytest.mark.parametrize('value,expected', [(None, True), (' yes ', True), ('false', False), (False, False)])
def test_allowlist_default_and_config(monkeypatch, value, expected):
    monkeypatch.setattr(rq_events.datadog_agent, 'get_config', lambda _: value)
    assert rq_events.is_query_allowlist_enabled() is expected


def test_agent_config_read_failures_log_fixed_text_only(monkeypatch, caplog):
    """Both config-reading helpers swallow read failures into fixed debug text: the config
    layer's exception can quote configuration values."""
    caplog.set_level(logging.DEBUG)

    def broken_get_config(key):
        raise Exception('SECRET_DO_NOT_LOG in the config layer')

    monkeypatch.setattr(rq_events.datadog_agent, 'get_config', broken_get_config)
    assert rq_upload.get_agent_config('api_key') == ''
    assert rq_events.is_query_allowlist_enabled() is True
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
