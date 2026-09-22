# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.remote_queries.contract import RemoteQueryEvent
from datadog_checks.base.utils.remote_queries.timing import RemoteQueryProducerTimings


class QueryCheck(AgentCheck):
    remote_query_operations = frozenset({'resolve_target', 'produce_json_pages'})

    def resolve_remote_query(self, request: Mapping[str, Any]) -> Iterator[RemoteQueryEvent]:
        yield RemoteQueryEvent('final', {'status': 'MATCHED', 'target': request['target']})

    def execute_remote_query(
        self, request: Mapping[str, Any], timings: RemoteQueryProducerTimings
    ) -> Iterator[RemoteQueryEvent]:
        try:
            yield RemoteQueryEvent('metadata', {'status': 'STARTED', 'query': request['query']})
            yield RemoteQueryEvent('final', {'status': 'SUCCEEDED', 'executionDiagnostics': timings.metadata()})
        finally:
            self.execution_closed = True


def test_monitoring_check_rejects_remote_queries():
    """Ordinary checks must fail explicitly, without entering their monitoring loop."""
    events = []
    AgentCheck().run_remote_query('{"operation":"produce_json_pages"}', lambda *event: events.append(event))
    assert len(events) == 1
    assert events[0][0] == 'error'
    assert json.loads(events[0][1])['error']['code'] == 'unsupported_operation'
    assert events[0][2] == b''


@pytest.mark.parametrize('request_json', ['{', '[]', '{"operation": []}', '{"operation": "unknown"}'])
def test_invalid_request_does_not_enter_check_hooks(request_json: str):
    """Reject malformed requests before invoking a database-specific implementation."""
    events = []
    QueryCheck().run_remote_query(request_json, lambda *event: events.append(event))
    assert len(events) == 1
    assert json.loads(events[0][1])['error']['code'] == 'invalid_request'


@pytest.mark.parametrize('operation', ['resolve_target', 'produce_json_pages'])
def test_dispatches_to_check_hook(operation: str):
    """The selected operation must reach the loaded check with the decoded request."""
    request = {'operation': operation, 'target': {'dbname': 'warehouse'}, 'query': 'SELECT 1'}
    events = []
    check = QueryCheck()
    check.run_remote_query(json.dumps(request), lambda *event: events.append(event))
    assert all(event[2] == b'' for event in events)
    if operation == 'resolve_target':
        assert len(events) == 1
        assert json.loads(events[0][1]) == {'status': 'MATCHED', 'target': request['target']}
    else:
        assert [event[0] for event in events] == ['metadata', 'final']
        assert json.loads(events[0][1])['query'] == request['query']
        assert 'executionDiagnostics' in json.loads(events[-1][1])
        assert check.execution_closed


def test_operation_must_be_explicitly_supported():
    """An execution-only check must not enter a resolution hook."""
    check = QueryCheck()
    check.remote_query_operations = frozenset({'produce_json_pages'})
    events = []
    check.run_remote_query('{"operation":"resolve_target"}', lambda *event: events.append(event))
    assert len(events) == 1
    assert json.loads(events[0][1])['error']['code'] == 'unsupported_operation'


def test_emit_failure_closes_execution():
    """A consumer failure must release producer resources before propagating."""
    check = QueryCheck()

    def emit(event_type: str, metadata_json: str, payload: bytes) -> None:
        raise RuntimeError('consumer stopped')

    with pytest.raises(RuntimeError, match='consumer stopped'):
        check.run_remote_query('{"operation":"produce_json_pages", "query":"SELECT 1"}', emit)
    assert check.execution_closed
