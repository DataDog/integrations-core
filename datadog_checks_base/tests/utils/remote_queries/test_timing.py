# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import hashlib
import json
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import timing as rq_timing
from datadog_checks.base.utils.remote_queries import upload as rq_upload

from .helpers import AdvancingUploads, acceptance_receipt, descriptor, string_cell


def test_phase_nesting_suspends_the_enclosing_accumulation():
    # A scripted accumulator clock: the values below are the reads in order. The fetch runs
    # inside the encode phase, so the fetch's wall must leave the encode bucket and land in
    # its own, and the un-instrumented remainder must land in otherMs.
    values = iter([0.0, 0.5, 0.5, 0.75, 1.0, 1.25, 1.5])
    timings = rq_timing.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.phase('database_setup'):
        pass  # exits at 0.5
    with timings.phase('encode_and_page_build'):
        with timings.phase('database_fetch'):
            pass  # 0.75 -> 1.0
        pass  # encode resumes at 1.0 and exits at 1.25
    assert timings.metadata() == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 1500,
            'databaseSetupMs': 500,
            'databaseFetchMs': 250,
            'encodeAndPageBuildMs': 500,
            'otherMs': 250,
        },
    }


def test_source_page_writer_upload_inside_encode_is_excluded_from_encode(delivery, creds):
    # finish() runs inside the encode phase, so the final page's upload and the finalize
    # suspend the encode accumulation instead of leaking into it; the enclosing encode
    # segment between the two (the page receipt verification) stays in the encode bucket.
    clock = {'now': 0.0}
    stats = rq_contract.RemoteQueryRunStats()
    uploads = AdvancingUploads(clock, put_source_page_seconds=0.5, finalize_seconds=0.375)
    timings = rq_timing.RemoteQueryProducerTimings(0.0, clock=lambda: clock['now'])
    writer = rq_pages.SourcePageWriter(delivery, creds, uploads, descriptor(), lambda: None, stats, timings)
    with timings.phase('encode_and_page_build'):
        writer.add_row([string_cell('1')])
        clock['now'] += 0.25  # measured encode work
        writer.finish()
        clock['now'] += 0.125  # page receipt verification back in the encode bucket
    assert timings.metadata(stats) == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 1250,
            'encodeAndPageBuildMs': 375,
            'pageUploadMs': 500,
            'finalizeMs': 375,
            'otherMs': 0,
            'timeToFirstPageMs': 750,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': stats.bytes_emitted,
            'pageUploadMinMs': 500,
            'pageUploadP50Ms': 500,
            'pageUploadP95Ms': 500,
            'pageUploadMaxMs': 500,
        },
    }


@pytest.mark.parametrize(
    'ascending_ms,quantile,expected',
    [
        ([10.0], 0.50, 10.0),
        ([10.0], 0.95, 10.0),
        ([10.0, 20.0], 0.50, 10.0),  # ceil(0.50*2) = 1
        ([10.0, 20.0], 0.95, 20.0),  # ceil(0.95*2) = 2
        ([10.0, 20.0, 30.0], 0.50, 20.0),  # ceil(1.5) = 2
        ([10.0, 20.0, 30.0], 0.95, 30.0),  # ceil(2.85) = 3
        ([float(value) for value in range(1, 21)], 0.50, 10.0),  # ceil(10) = 10
        ([float(value) for value in range(1, 21)], 0.95, 19.0),  # ceil(19) = 19: not the max
    ],
)
def test_nearest_rank_percentile_table(ascending_ms, quantile, expected):
    assert rq_timing.nearest_rank_percentile(ascending_ms, quantile) == expected


def test_page_upload_distribution_uses_nearest_rank_percentiles():
    # Three completed pages with upload walls of 125, 250, and 375 ms. The scripted clock
    # values are the accumulator's reads in order: each page's upload enter/exit pair plus
    # the one acknowledgment read (only the first page's acknowledgment reads the clock, for
    # the first-page time) and the final emission read.
    values = iter([0.0, 0.125, 0.125, 0.125, 0.375, 0.375, 0.75, 1.125])
    timings = rq_timing.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.page_upload():
        pass
    timings.note_page_acknowledged()
    with timings.page_upload():
        pass
    timings.note_page_acknowledged()
    with timings.page_upload():
        pass
    timings.note_page_acknowledged()
    assert timings.metadata() == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 1125,
            'pageUploadMs': 750,
            'otherMs': 375,
            'timeToFirstPageMs': 125,
            'pageUploadMinMs': 125,
            'pageUploadP50Ms': 250,
            'pageUploadP95Ms': 375,
            'pageUploadMaxMs': 375,
        },
    }


def test_zero_page_run_omits_the_upload_distribution_fields():
    values = iter([0.0, 0.5, 1.0])
    timings = rq_timing.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.phase('finalize'):
        pass
    assert timings.metadata() == {
        'contractVersion': 1,
        'producer': {'totalMs': 1000, 'finalizeMs': 500, 'otherMs': 500},
    }


def test_metadata_reports_only_measured_fields():
    # Nothing ran beyond reading the clock: the minimal shape carries only the measured run
    # wall and its remainder, exactly what a malformed request reports.
    values = iter([0.25])
    timings = rq_timing.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    assert timings.metadata() == {'contractVersion': 1, 'producer': {'totalMs': 250, 'otherMs': 250}}


def test_other_ms_clamps_to_zero_when_measured_phases_exceed_the_total():
    # A clock that runs backward between the phase exit and emission would make the measured
    # phases larger than the total; the remainder clamps to zero instead of going negative.
    values = iter([0.0, 1.0, 0.5])
    timings = rq_timing.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.phase('database_fetch'):
        pass
    diagnostics = timings.metadata()
    assert diagnostics['producer']['databaseFetchMs'] == 1000
    assert diagnostics['producer']['otherMs'] == 0


def test_retry_accounting_includes_failed_attempts_and_backoff_exactly_once(monkeypatch, delivery, creds):
    import requests

    clock = {'now': 0.0}
    monkeypatch.setattr(rq_timing.time, 'monotonic', lambda: clock['now'])

    # The retry backoff advances the same monotonic clock, so the page's upload wall provably
    # includes it. The advance is pinned to a dyadic quarter second (instead of the real 0.1 s
    # first backoff) so the accumulated float arithmetic stays exact; what is under test is
    # that the backoff is counted once, not its exact production value.
    def fake_sleep(seconds):
        clock['now'] += 0.125

    monkeypatch.setattr(rq_timing.time, 'sleep', fake_sleep)
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(method)
        if url.endswith('/descriptor'):
            clock['now'] += 0.5
            registered = json.loads(data)
            return SimpleNamespace(
                status_code=200,
                content=json.dumps(
                    {
                        'upload_id': creds.upload_id,
                        'format_version': registered['format_version'],
                        'include_schema': registered['include_schema'],
                        'columns': len(registered['columns']),
                        'sha256': hashlib.sha256(data).hexdigest(),
                    }
                ).encode(),
            )
        if url.endswith('/finalize'):
            clock['now'] += 0.5
            return SimpleNamespace(
                status_code=200,
                content=json.dumps(
                    {'upload_id': creds.upload_id, 'page_count': 1, 'total_rows': 1, 'total_bytes': 40}
                ).encode(),
            )
        if len(calls) == 2:
            clock['now'] += 3.0
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        clock['now'] += 7.0
        # Echo the declared source page metadata in the acceptance receipt so the
        # identity verification passes.
        batch_index = int(url.rsplit('/', 1)[-1])
        return SimpleNamespace(
            status_code=202,
            content=json.dumps(
                acceptance_receipt(
                    batch_index,
                    int(headers['X-DD-Record-Offset']),
                    int(headers['X-DD-Source-Page-Rows']),
                    upload_id=creds.upload_id,
                )
            ).encode(),
        )

    monkeypatch.setattr(requests, 'request', request)
    stats = rq_contract.RemoteQueryRunStats()
    timings = rq_timing.RemoteQueryProducerTimings(0.0)
    client = rq_upload.RequestsUploadClient(timings=timings)
    writer = rq_pages.SourcePageWriter(delivery, creds, client, descriptor(), lambda: None, stats, timings)

    writer.add_row([string_cell('1')])
    result = writer.finish()

    # The descriptor registration precedes the page PUT; finalize is the last call.
    assert calls == ['POST', 'PUT', 'PUT', 'POST']
    assert result == {
        'uploadId': creds.upload_id,
        'pageCount': 1,
        'totalRows': 1,
        'totalBytes': 40,
    }
    # The page's upload wall is exactly the failed attempt (3 s) plus the backoff (0.125 s)
    # plus the successful attempt (7 s), each counted once; the descriptor registration and
    # finalize are their own POSTs, so the registration wall lands in the otherMs remainder.
    # The finalize totals replaced the producer's conservative accounting, so byteCount is
    # intake's 40, not the page's source or bound bytes.
    assert timings.metadata(stats) == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 11125,
            'pageUploadMs': 10125,
            'finalizeMs': 500,
            'otherMs': 500,
            'timeToFirstPageMs': 10625,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': 40,
            'uploadAttemptCount': 2,
            'uploadRetryCount': 1,
            'pageUploadMinMs': 10125,
            'pageUploadP50Ms': 10125,
            'pageUploadP95Ms': 10125,
            'pageUploadMaxMs': 10125,
        },
    }
    assert stats.bytes_emitted == 40
