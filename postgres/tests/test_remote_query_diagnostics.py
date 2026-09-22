# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.postgres import remote_query

from .remote_query_fakes import (
    UPLOAD_ID,
    FakePool,
    FakeUploadClient,
    MutableClock,
    assembled_pages,
    assert_failed_event,
    assert_success,
    collect_events,
    event_metadata,
    instrument_postgres_fakes,
    make_check,
    patch_upload_credentials,
    two_row_boundary_request,
    valid_request,
    wide_row_pool,
)


def test_producer_reports_phase_diagnostics_for_a_successful_run(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clock = MutableClock()
    monkeypatch.setattr(remote_query.time, 'monotonic', clock.monotonic)
    instrument_postgres_fakes(monkeypatch, clock)
    pool = FakePool(rows=[(1,), (2,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    final = assert_success(events)
    # The final metadata gained exactly one key: the optional execution diagnostics.
    assert set(final) == {'status', 'upload_receipt', 'stats', 'executionDiagnostics'}
    producer = final['executionDiagnostics']['producer']
    assert final['executionDiagnostics']['contractVersion'] == 1
    assert producer == {
        'totalMs': 5375,
        # Connection acquisition, BEGIN, the statement timeout, the five session pins, the
        # DECLARE, the vendor-type lookup, and the COPY dispatch are setup.
        'databaseSetupMs': 3125,
        # Three copy.read calls (the two records and the empty end-of-stream read).
        'databaseFetchMs': 1125,
        # Real record-assembly work with this clock runs in well under a millisecond.
        'encodeAndPageBuildMs': 0,
        'pageUploadMs': 625,
        'finalizeMs': 250,
        # The ROLLBACK teardown runs outside every phase and lands in the remainder.
        'otherMs': 250,
        'timeToFirstPageMs': 4875,
        'pageCount': 1,
        'rowCount': 2,
        'byteCount': len(assembled_pages(fake)[0]),
        'pageUploadMinMs': 625,
        'pageUploadP50Ms': 625,
        'pageUploadP95Ms': 625,
        'pageUploadMaxMs': 625,
    }
    # The diagnostics total and stats.elapsedMs are the same wall.
    assert final['stats']['elapsedMs'] == producer['totalMs']
    # The injected upload client makes no HTTP attempts, so the attempt counters stay
    # unmeasured (absent, never zero).
    assert 'uploadAttemptCount' not in producer
    assert 'uploadRetryCount' not in producer


def test_mid_run_failure_reports_honest_partial_diagnostics(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clock = MutableClock()
    monkeypatch.setattr(remote_query.time, 'monotonic', clock.monotonic)
    instrument_postgres_fakes(monkeypatch, clock)
    # A two-page boundary whose second page upload fails: the first page is acknowledged
    # and counted, the second attempt's wall is measured but never promoted.
    request = two_row_boundary_request(monkeypatch)
    pool = wide_row_pool()

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

    events = collect_events(request, make_check(pool=pool), client=fake)

    error = event_metadata(events[-1])
    assert_failed_event(events, 'upload_failed')
    # The error metadata gained exactly one key: the optional execution diagnostics.
    assert set(error) == {'status', 'error', 'stats', 'executionDiagnostics'}
    assert fake.abort_calls == 1
    assert fake.run_finalize_calls == 0
    # The read-only transaction rolled back when the failed upload unwound produce.
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'
    first_page_bytes = len(assembled_pages(fake)[0])
    assert error['stats'] == {
        'rowsEmitted': 1,
        'pagesEmitted': 1,
        'bytesEmitted': first_page_bytes,
        'elapsedMs': 5375,
    }
    assert error['executionDiagnostics'] == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 5375,
            'databaseSetupMs': 3125,
            # Two copy.read calls: the page closes at the target while the second record
            # is fed, so its failed upload aborts the record loop before the empty
            # end-of-stream read.
            'databaseFetchMs': 750,
            'encodeAndPageBuildMs': 0,
            # Both upload walls are kept: the acknowledged page and the failed attempt's.
            'pageUploadMs': 1250,
            # finalizeMs is absent: finalize never ran. uploadAttemptCount/RetryCount are
            # absent too: the injected client makes no HTTP attempts.
            'otherMs': 250,
            'timeToFirstPageMs': 4125,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': first_page_bytes,
            # The distribution holds only the acknowledged page's wall.
            'pageUploadMinMs': 625,
            'pageUploadP50Ms': 625,
            'pageUploadP95Ms': 625,
            'pageUploadMaxMs': 625,
        },
    }
