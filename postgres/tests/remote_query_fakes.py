# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Shared Postgres remote-query test fakes.

The intake-side upload client and the native COPY CSV record builders are shared by the
unit suite and the real-database integration suite, so the two prove the same wire
expectations against one fake rather than two drifting copies.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import Any

from datadog_checks.base.utils import remote_queries as rq


class FakeUploadClient:
    """Intake-side fake: one descriptor registration, page acceptance receipts, finalize totals.

    Page PUTs answer the pinned acceptance receipt — no per-page final metadata exists at
    acceptance — and the default finalize returns authoritative totals over the recorded
    pages, so the producer's stats and compact receipt come from finalization.
    ``reject_first_page_too_large`` answers page 0's first PUT with intake's defensive
    final_page_too_large rejection, so a run exercises the split-and-retry path; every
    attempt (rejected or accepted) is recorded in ``put_attempts``.
    """

    def __init__(
        self,
        put_page_response=None,
        put_log=None,
        reject_first_page_too_large=False,
    ):
        # SimpleNamespace(batch_index, record_offset, source_bytes, rows, payload)
        self.descriptor_bodies = []
        self.put_page_calls = []
        self.put_attempts = []
        self.run_finalize_calls = 0
        self.finalize_expected_page_counts = []
        self.abort_calls = 0
        self.reject_first_page_too_large = reject_first_page_too_large
        # When unset, the receipt carries shape-valid intake-derived metadata; tests pass a
        # mapping (or a callable taking the page metadata) to mutate or reject it.
        self.put_page_response = put_page_response
        self.put_log = put_log

    def register_descriptor(self, creds, body):
        self.descriptor_bodies.append(body)
        registered = json.loads(body)
        return {
            'upload_id': creds.upload_id,
            'format_version': registered['format_version'],
            'include_schema': registered['include_schema'],
            'columns': len(registered['columns']),
            'sha256': hashlib.sha256(body).hexdigest(),
        }

    def put_source_page(self, creds, page, body):
        payload = body.read()
        self.put_attempts.append(page.batch_index)
        if self.reject_first_page_too_large and page.batch_index == 0 and self.put_attempts.count(0) == 1:
            raise rq.RemoteQueryFailure(
                rq.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake rejected the final page size.'
            )
        self.put_page_calls.append(
            SimpleNamespace(
                batch_index=page.batch_index,
                record_offset=page.record_offset,
                source_bytes=page.source_bytes,
                rows=page.rows,
                payload=payload,
            )
        )
        if self.put_log is not None:
            self.put_log.append(('put', page.batch_index, page.source_bytes, page.rows))
        if self.put_page_response is not None:
            response = self.put_page_response
            if callable(response):
                response = response(page)
        else:
            response = {
                'upload_id': creds.upload_id,
                'batch_index': page.batch_index,
                'record_offset': page.record_offset,
                'source_rows': page.rows,
                'status': 'accepted',
            }
        return response

    def finalize_run(self, creds, expected_page_count):
        self.run_finalize_calls += 1
        self.finalize_expected_page_counts.append(expected_page_count)
        return {
            'upload_id': creds.upload_id,
            'page_count': len(self.put_page_calls),
            'total_rows': sum(call.rows for call in self.put_page_calls),
            'total_bytes': sum(call.source_bytes for call in self.put_page_calls),
        }

    def abort(self, creds):
        self.abort_calls += 1

    def pages(self):
        """Each completed page's exact uploaded source bytes, keyed by batch index."""
        return {call.batch_index: call.payload for call in self.put_page_calls}


def native_field(value: Any) -> str:
    """The expected native COPY CSV field for one value, computed independently.

    ``FORCE_QUOTE *`` quotes every non-null value — with internal quotes doubled — and
    NULL is the sole unquoted field, the two-character \\N marker.
    """
    if value is None:
        return '\\N'
    if isinstance(value, bool):
        value = 't' if value else 'f'
    elif isinstance(value, bytes):
        value = '\\x' + value.hex()
    return '"{}"'.format(str(value).replace('"', '""'))


def native_record(*values: Any) -> bytes:
    """The expected native COPY CSV record for one row of values."""
    return (','.join(native_field(value) for value in values) + '\n').encode('utf-8')


def patch_allowlist_disabled(monkeypatch):
    monkeypatch.setattr(rq, 'is_query_allowlist_enabled', lambda: False)


def event_metadata(event):
    return event.metadata


def assert_success(events):
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    return event_metadata(events[-1])
