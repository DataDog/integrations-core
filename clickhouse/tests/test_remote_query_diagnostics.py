# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.clickhouse import remote_query
from datadog_checks.clickhouse.remote_query import iter_agent_rpc_stream_events

from .remote_query_fakes import (
    BOUND_ROW,
    UPLOAD_ID,
    FakeUploadClient,
    MutableClock,
    assembled_pages,
    assert_failed_event,
    assert_success,
    event_metadata,
    instrument_clickhouse_fakes,
    make_check,
    make_client,
    patch_allowlist_disabled,
    patch_upload_credentials,
    prefix_bytes,
    row_object_bound,
    two_row_boundary_request,
    two_row_client,
    valid_request,
)


def test_producer_reports_phase_diagnostics_for_a_successful_run(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clock = MutableClock()
    monkeypatch.setattr(remote_query.time, 'monotonic', clock.monotonic)
    instrument_clickhouse_fakes(monkeypatch, clock)
    clickhouse_client = make_client(rows=[[1], [2]])
    fake = FakeUploadClient()

    def client_factory(_check, _timeout_seconds):
        clock.advance_seconds(0.125)
        return clickhouse_client

    events = list(iter_agent_rpc_stream_events(valid_request(), make_check(), fake, client_factory))

    final = assert_success(events)
    # The final metadata gained exactly one key: the optional execution diagnostics.
    assert set(final) == {'status', 'upload_receipt', 'stats', 'executionDiagnostics'}
    producer = final['executionDiagnostics']['producer']
    assert final['executionDiagnostics']['contractVersion'] == 1
    # Two raw stream reads serve the whole result: the first chunk carries the header rows
    # and both data rows; the second read returns the empty tail.
    assert clickhouse_client.stream.read_count == 2
    assert producer == {
        'totalMs': 2125,
        # Client creation (in the factory), the stream open, and the descriptor registration
        # are setup.
        'databaseSetupMs': 375,
        # Every raw stream read is a fetch: two reads here.
        'databaseFetchMs': 750,
        # Real parse/encode work with this clock runs in well under a millisecond.
        'encodeAndPageBuildMs': 0,
        'pageUploadMs': 500,
        'finalizeMs': 250,
        # The stream and client teardown run outside every phase and land in the remainder.
        'otherMs': 250,
        'timeToFirstPageMs': 1625,
        'pageCount': 1,
        'rowCount': 2,
        'byteCount': len(assembled_pages(fake)[0]),
        'pageUploadMinMs': 500,
        'pageUploadP50Ms': 500,
        'pageUploadP95Ms': 500,
        'pageUploadMaxMs': 500,
    }
    # The diagnostics total and stats.elapsedMs are the same wall.
    assert final['stats']['elapsedMs'] == producer['totalMs']
    # The injected upload client makes no HTTP attempts, so the attempt counters stay
    # unmeasured (absent, never zero).
    assert 'uploadAttemptCount' not in producer
    assert 'uploadRetryCount' not in producer


def test_mid_run_failure_reports_honest_partial_diagnostics(monkeypatch):
    clock = MutableClock()
    monkeypatch.setattr(remote_query.time, 'monotonic', clock.monotonic)
    instrument_clickhouse_fakes(monkeypatch, clock)
    # A two-page boundary whose second page upload fails: the first page is acknowledged
    # and counted, the second attempt's wall is measured but never promoted.
    request = two_row_boundary_request(monkeypatch, extra_bound_bytes=-1)
    clickhouse_client = two_row_client()

    def fail_second_page(page):
        if page.batch_index == 1:
            raise rq_contract.RemoteQueryFailure('upload_failed', 'transient exhausted', retryable=True)
        return {
            'upload_id': UPLOAD_ID,
            'batch_index': page.batch_index,
            'record_offset': page.record_offset,
            'source_rows': page.rows,
            'status': 'accepted',
        }

    fake = FakeUploadClient(put_page_response=fail_second_page)

    def client_factory(_check, _timeout_seconds):
        clock.advance_seconds(0.125)
        return clickhouse_client

    events = list(iter_agent_rpc_stream_events(request, make_check(), fake, client_factory))

    error = event_metadata(events[-1])
    assert_failed_event(events, 'upload_failed')
    # The error metadata gained exactly one key: the optional execution diagnostics.
    assert set(error) == {'status', 'error', 'stats', 'executionDiagnostics'}
    assert fake.run_finalize_calls == 0
    assert fake.abort_calls == 1
    assert clickhouse_client.stream.closed
    assert clickhouse_client.closed
    # The producer's conservative accounting for the accepted page: its final-JSON bound,
    # not the smaller CSV source bytes it uploaded.
    first_page_bound = len(prefix_bytes()) + len(rq_pages.PAGE_SUFFIX) + row_object_bound(BOUND_ROW)
    assert error['stats']['elapsedMs'] == 2375
    assert error['executionDiagnostics'] == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 2375,
            'databaseSetupMs': 375,
            'databaseFetchMs': 750,
            'encodeAndPageBuildMs': 0,
            # Both upload walls are kept: the acknowledged page and the failed attempt's.
            'pageUploadMs': 1000,
            # finalizeMs is absent: finalize never ran. uploadAttemptCount/RetryCount are
            # absent too: the injected client makes no HTTP attempts.
            'otherMs': 250,
            'timeToFirstPageMs': 1250,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': first_page_bound,
            # The distribution holds only the acknowledged page's wall.
            'pageUploadMinMs': 500,
            'pageUploadP50Ms': 500,
            'pageUploadP95Ms': 500,
            'pageUploadMaxMs': 500,
        },
    }
