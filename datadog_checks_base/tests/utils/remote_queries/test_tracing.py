# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import sys

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing

from .helpers import PARENT_ID, TRACE_ID, make_tracing


def test_root_span_carries_run_identity_and_the_success_terminal(delivery):
    tracing, tracer = make_tracing()
    stats = rq_contract.RemoteQueryRunStats(rows_emitted=3, pages_emitted=1, bytes_emitted=7)

    tracing.open_root(delivery)
    tracing.note_page_acknowledged()
    tracing.succeed(stats)
    tracing.close()

    [root] = tracer.spans
    assert root.name == rq_tracing.REMOTE_QUERY_PRODUCER_ROOT_SPAN_OPERATION
    # The root continues the request's carrier: its parent is the action span's context.
    assert root.child_of.trace_id == int(TRACE_ID)
    assert root.child_of.span_id == int(PARENT_ID)
    assert root.service == rq_tracing.REMOTE_QUERY_PRODUCER_SPAN_SERVICE
    assert root.resource == 'postgres'
    assert root.activate is False
    assert root.tags == {
        rq_tracing.REMOTE_QUERY_SPAN_RUN_ID_TAG: 'run-1',
        rq_tracing.REMOTE_QUERY_SPAN_TASK_ID_TAG: 'task-1',
        rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_ID_TAG: 'upload-1',
        rq_tracing.REMOTE_QUERY_SPAN_INTEGRATION_TAG: 'postgres',
        rq_tracing.REMOTE_QUERY_SPAN_ORIGIN_TAG: 'datadog-agent-integrations',
        rq_tracing.REMOTE_QUERY_SPAN_STATUS_TAG: 'SUCCEEDED',
    }
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_PAGE_COUNT_METRIC] == 1
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_ROW_COUNT_METRIC] == 3
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_BYTE_COUNT_METRIC] == 7
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_ATTEMPT_COUNT_METRIC] == 0
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_RETRY_COUNT_METRIC] == 0
    # The first acknowledged page's wall from the root start — the first receipt-verified,
    # counted page.
    assert isinstance(root.metrics[rq_tracing.REMOTE_QUERY_SPAN_TIME_TO_FIRST_PAGE_METRIC], int)
    assert root.error == 0
    assert root.finished
    # close flushes the supported singleton exactly once, best-effort.
    assert tracer.flushes == 1


def test_root_span_records_the_failure_code_and_partial_counters(delivery):
    tracing, tracer = make_tracing(integration=None)

    tracing.open_root(delivery)
    tracing.begin_page_upload_attempt(retry=False).finish(error='rejected', http_status=503)
    tracing.begin_page_upload_attempt(retry=True).finish(error=None, http_status=202)
    tracing.fail('upload_failed', rq_contract.RemoteQueryRunStats(pages_emitted=1, rows_emitted=2, bytes_emitted=5))
    tracing.close()

    root = tracer.spans[0]
    assert root.name == rq_tracing.REMOTE_QUERY_PRODUCER_ROOT_SPAN_OPERATION
    assert root.tags[rq_tracing.REMOTE_QUERY_SPAN_STATUS_TAG] == 'FAILED'
    assert root.tags[rq_tracing.REMOTE_QUERY_SPAN_ERROR_TYPE_TAG] == 'upload_failed'
    assert root.error == 1
    assert rq_tracing.REMOTE_QUERY_SPAN_INTEGRATION_TAG not in root.tags
    # An unknown integration leaves the resource unset — ddtrace then defaults it to the
    # operation name.
    assert root.resource is None
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_PAGE_COUNT_METRIC] == 1
    # The attempt counters count each HTTP page upload attempt exactly once, a retry
    # being any attempt beyond a page's first.
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_ATTEMPT_COUNT_METRIC] == 2
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_RETRY_COUNT_METRIC] == 1


def test_phase_spans_follow_real_execution_order_and_close_before_the_root(delivery):
    tracing, tracer = make_tracing()

    tracing.open_root(delivery)
    with tracing.phase('database_setup'):
        tracing.enter_fetch()
        tracing.enter_fetch()
    with tracing.phase('encode_and_page_build'):
        tracing.enter_fetch()
        tracing.begin_page_upload_attempt(retry=False).finish(error=None, http_status=202)
        tracing.enter_fetch()
    with tracing.finalize_span():
        pass
    tracing.succeed(rq_contract.RemoteQueryRunStats())
    tracing.close()

    assert [span.name for span in tracer.spans] == [
        'remote_queries.producer',
        'remote_queries.database_setup',
        'remote_queries.database_fetch',
        'remote_queries.encode_and_page_build',
        'remote_queries.database_fetch',
        'remote_queries.page_upload',
        'remote_queries.database_fetch',
        'remote_queries.finalize',
    ]
    root, _setup, header_fetch, encode, _fetch, upload, _tail_fetch, finalize = tracer.spans
    # Phase spans are the root's children; fetch regions and the upload attempt are
    # children of the phase they run inside — the producer's own nesting.
    assert header_fetch.child_of.name == 'remote_queries.database_setup'
    assert encode.child_of is root
    assert upload.child_of is encode
    assert finalize.child_of is root
    # One fetch region span per page window, never one per read.
    assert len(tracer.by_name('remote_queries.database_fetch')) == 3
    # Every span finished before the root, so the trace is complete.
    assert all(span.finished for span in tracer.spans)


def test_a_raising_tracer_degrades_to_noop_spans_without_touching_the_run(delivery):
    tracing, tracer = make_tracing(refuse_span=rq_tracing.REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION, refuse_flush=True)

    tracing.open_root(delivery)
    # The first page-upload attempt span is refused: the run's spans degrade.
    assert tracing.begin_page_upload_attempt(retry=False) is None
    with tracing.phase('encode_and_page_build'):
        tracing.enter_fetch()
    assert tracing.enter_phase('database_setup') is None
    assert tracing.begin_page_upload_attempt(retry=True) is None
    tracing.fail('upload_failed', rq_contract.RemoteQueryRunStats())
    tracing.close()

    # The root still finishes with its terminal tags and the refusing flush is
    # swallowed: no span, tag, or flush failure escapes or leaks an unfinished trace.
    [root] = tracer.spans
    assert root.name == rq_tracing.REMOTE_QUERY_PRODUCER_ROOT_SPAN_OPERATION
    assert root.finished
    assert root.tags[rq_tracing.REMOTE_QUERY_SPAN_ERROR_TYPE_TAG] == 'upload_failed'
    assert tracer.flushes == 1


def test_factory_falls_back_to_the_null_tracing_when_ddtrace_cannot_import(monkeypatch):
    # ddtrace's pytest plugin preloads parts of the package in this process, so the block
    # pins the exact submodule the factory imports: the from-import halts either way.
    monkeypatch.setitem(sys.modules, 'ddtrace.propagation.http', None)

    assert rq_tracing.open_remote_query_producer_tracing(None, 'postgres') is rq_tracing.NULL_PRODUCER_TRACING


@pytest.mark.parametrize('carrier', [None, {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 1}])
def test_factory_builds_the_parent_context_from_the_validated_carrier(carrier):
    validated = rq_contract.RemoteQueryTraceContext.model_validate(carrier) if carrier is not None else None

    tracing = rq_tracing.open_remote_query_producer_tracing(validated, 'clickhouse')

    assert isinstance(tracing, rq_tracing.RemoteQueryProducerTracing)
    if validated is None:
        # No carrier: the producer root starts a local root trace.
        assert tracing._parent_context is None
    else:
        assert tracing._parent_context.trace_id == int(TRACE_ID)
        assert tracing._parent_context.span_id == int(PARENT_ID)
        assert tracing._parent_context.sampling_priority == 1
