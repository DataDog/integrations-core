# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.remote_queries.contract import RemoteQueryEvent


class QueryHandler:
    """A remote-query capability handler used to exercise the base dispatch."""

    execution_closed = False
    started_at: float | None = None

    def resolve(self, request: Mapping[str, Any]) -> Iterator[RemoteQueryEvent]:
        yield RemoteQueryEvent('final', {'status': 'MATCHED', 'target': request['target']})

    def execute(self, request: Mapping[str, Any], started_at: float) -> Iterator[RemoteQueryEvent]:
        self.started_at = started_at
        try:
            yield RemoteQueryEvent('metadata', {'status': 'STARTED', 'query': request['query']})
            yield RemoteQueryEvent('final', {'status': 'SUCCEEDED'})
        finally:
            self.execution_closed = True


class QueryCheck(AgentCheck):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(QueryCheck, self).__init__(*args, **kwargs)
        self.handler = QueryHandler()

    def get_remote_query_handler(self) -> QueryHandler:
        return self.handler


@pytest.mark.parametrize('operation', ['resolve_target', 'produce_json_pages'])
def test_monitoring_check_rejects_remote_queries(operation: str):
    """Ordinary checks have no handler and must fail explicitly, without entering their monitoring loop."""
    events = []
    AgentCheck().run_remote_query(json.dumps({'operation': operation}), lambda *event: events.append(event))
    assert len(events) == 1
    assert events[0][0] == 'error'
    assert json.loads(events[0][1])['error']['code'] == 'unsupported_operation'
    assert events[0][2] == b''


@pytest.mark.parametrize('request_json', ['{', '[]', '{"operation": []}', '{"operation": "unknown"}'])
def test_invalid_request_does_not_reach_the_handler(request_json: str):
    """Reject malformed requests before invoking the capability handler."""
    events = []
    QueryCheck().run_remote_query(request_json, lambda *event: events.append(event))
    assert len(events) == 1
    assert json.loads(events[0][1])['error']['code'] == 'invalid_request'


@pytest.mark.parametrize('operation', ['resolve_target', 'produce_json_pages'])
def test_dispatches_to_the_handler(operation: str):
    """The selected operation must reach the handler with the decoded request."""
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
        assert json.loads(events[-1][1])['status'] == 'SUCCEEDED'
        # The execution receives the monotonic run start captured at the request-parse
        # boundary: a usable timestamp, not later than this check.
        assert isinstance(check.handler.started_at, float)
        assert check.handler.execution_closed


def test_emit_failure_closes_execution():
    """A consumer failure must release producer resources before propagating."""
    check = QueryCheck()

    def emit(event_type: str, metadata_json: str, payload: bytes) -> None:
        raise RuntimeError('consumer stopped')

    with pytest.raises(RuntimeError, match='consumer stopped'):
        check.run_remote_query('{"operation":"produce_json_pages", "query":"SELECT 1"}', emit)
    assert check.handler.execution_closed
