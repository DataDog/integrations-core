# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import threading
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


# ---------------------------------------------------------------------------
# Cancellation-lifecycle participation of the bridge call
# ---------------------------------------------------------------------------


class BlockingHandler:
    """A handler whose execution parks until the test releases it."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.resolved = 0
        self.executed = 0
        self.execution_closed = False

    def resolve(self, request: Mapping[str, Any]) -> Iterator[RemoteQueryEvent]:
        self.resolved += 1
        yield RemoteQueryEvent('final', {'status': 'MATCHED'})

    def execute(self, request: Mapping[str, Any], started_at: float) -> Iterator[RemoteQueryEvent]:
        self.executed += 1
        self.started.set()
        try:
            yield RemoteQueryEvent('metadata', {'status': 'STARTED'})
            assert self.release.wait(timeout=WAIT_TIMEOUT)
            yield RemoteQueryEvent('final', {'status': 'SUCCEEDED'})
        finally:
            self.execution_closed = True


class LifecycleQueryCheck(AgentCheck):
    """A check that opted into the cancellation lifecycle and holds a parking handler."""

    _lifecycle_managed = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = BlockingHandler()
        self.shutdown_calls = 0
        self.check_entered = threading.Event()
        self.release_check = threading.Event()
        self.release_check.set()

    def get_remote_query_handler(self) -> BlockingHandler:
        return self.handler

    def check(self, _):
        self.check_entered.set()
        assert self.release_check.wait(timeout=WAIT_TIMEOUT)

    def shutdown(self) -> None:
        self.shutdown_calls += 1


# Upper bound for waits on another thread; tests only ever wait for a signal that is
# already on its way.
WAIT_TIMEOUT = 5


def request_json(operation: str) -> str:
    return json.dumps({'operation': operation, 'target': {'dbname': 'warehouse'}, 'query': 'SELECT 1'})


@pytest.mark.parametrize('operation', ['resolve_target', 'produce_json_pages'])
def test_remote_call_after_cancel_is_refused_at_admission(operation: str):
    """A cancelled check refuses new remote calls with one retryable cancelled event.

    The call never reaches the handler: the check is being torn down, and the fixed
    outcome lets the backend re-dispatch after a reschedule instead of waiting on a
    stream from a dead check.
    """
    check = LifecycleQueryCheck()
    check.cancel()
    assert check.shutdown_calls == 1

    events = []
    check.run_remote_query(request_json(operation), lambda *event: events.append(event))

    assert len(events) == 1
    assert events[0][0] == 'error'
    assert json.loads(events[0][1])['error'] == {
        'code': 'cancelled',
        'message': 'Remote query run was cancelled.',
        'retryable': True,
    }
    assert events[0][2] == b''
    assert check.handler.resolved == 0
    assert check.handler.executed == 0
    # The refusal is not a second teardown.
    assert check.shutdown_calls == 1


def test_cancel_during_remote_call_defers_teardown_until_it_unwinds():
    """Teardown must wait for the bridge call, never run beside it.

    Releasing the check's resources under an active call tears down the pool and clients
    the call still uses, so the failure surfaces later as an unrelated error.
    """
    check = LifecycleQueryCheck()
    events = []
    thread = threading.Thread(
        target=lambda: check.run_remote_query(request_json('produce_json_pages'), lambda *event: events.append(event))
    )
    thread.start()
    assert check.handler.started.wait(timeout=WAIT_TIMEOUT)

    check.cancel()

    # The cancel is recorded, but the call is still executing so nothing may be released.
    assert check.is_cancelled
    assert check.shutdown_calls == 0

    check.handler.release.set()
    thread.join(timeout=WAIT_TIMEOUT)
    assert not thread.is_alive()
    # The call finished normally and the teardown ran once, after the unwind.
    assert [event[0] for event in events] == ['metadata', 'final']
    assert json.loads(events[-1][1])['status'] == 'SUCCEEDED'
    assert check.handler.execution_closed
    assert check.shutdown_calls == 1


def test_emit_failure_during_remote_call_still_releases_and_finalizes():
    """A cancel followed by an emit-callback failure unwinds in order: the generator is
    closed first, then the admission releases and the teardown runs exactly once."""
    check = LifecycleQueryCheck()
    failures = []

    def emit(event_type: str, metadata_json: str, payload: bytes) -> None:
        raise RuntimeError('consumer stopped')

    def run() -> None:
        try:
            check.run_remote_query(request_json('produce_json_pages'), emit)
        except BaseException as error:
            failures.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    assert check.handler.started.wait(timeout=WAIT_TIMEOUT)
    check.cancel()
    check.handler.release.set()
    thread.join(timeout=WAIT_TIMEOUT)
    assert not thread.is_alive()

    assert len(failures) == 1
    assert isinstance(failures[0], RuntimeError)
    # The producer was released (its generator closed) before the teardown ran.
    assert check.handler.execution_closed
    assert check.shutdown_calls == 1


@pytest.mark.parametrize('release_first', ['remote', 'run'], ids=['remote_first', 'run_first'])
def test_teardown_waits_for_a_run_and_remote_call_together(release_first):
    """A scheduled run and a remote call in flight together on one check.

    The teardown runs exactly once, and only after both operations have unwound —
    whichever leaves first, because each admission is counted.
    """
    check = LifecycleQueryCheck('test', {}, [{}])
    events = []
    remote = threading.Thread(
        target=lambda: check.run_remote_query(request_json('produce_json_pages'), lambda *event: events.append(event))
    )
    run_result = []
    scheduled = threading.Thread(target=lambda: run_result.append(check.run()))
    remote.start()
    assert check.handler.started.wait(timeout=WAIT_TIMEOUT)
    check.release_check.clear()
    scheduled.start()
    assert check.check_entered.wait(timeout=WAIT_TIMEOUT)

    check.cancel()
    assert check.shutdown_calls == 0

    if release_first == 'remote':
        check.handler.release.set()
        remote.join(timeout=WAIT_TIMEOUT)
        assert not remote.is_alive()
        assert check.shutdown_calls == 0
        check.release_check.set()
    else:
        check.release_check.set()
        scheduled.join(timeout=WAIT_TIMEOUT)
        assert not scheduled.is_alive()
        assert check.shutdown_calls == 0
        check.handler.release.set()
    remote.join(timeout=WAIT_TIMEOUT)
    scheduled.join(timeout=WAIT_TIMEOUT)
    assert not remote.is_alive()
    assert not scheduled.is_alive()

    assert check.shutdown_calls == 1
    assert [event[0] for event in events] == ['metadata', 'final']
    assert run_result == ['']


def test_plain_check_dispatch_still_works_after_cancel():
    """Without the opt-in, the bridge dispatch keeps its previous behavior: cancel is
    inert for it, so a later call dispatches to the handler normally."""
    check = QueryCheck()
    check.cancel()

    events = []
    check.run_remote_query(request_json('produce_json_pages'), lambda *event: events.append(event))

    assert [event[0] for event in events] == ['metadata', 'final']
    assert check.handler.execution_closed
