# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query upload."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, BinaryIO, Protocol

from datadog_checks.base.agent import datadog_agent

from .contract import (
    RemoteQueryFailure,
    RemoteQueryResultDelivery,
    RemoteQueryTraceContext,
    RemoteQueryUploadDescriptor,
    SourcePageUploadMetadata,
    canonical_json_bytes,
)
from .events import raise_if_timed_out
from .tracing import NULL_PRODUCER_TRACING, RemoteQueryProducerTracing

LOGGER = logging.getLogger(__name__)


REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE = 'application/vnd.datadog.remote-query.rows+csv;version=1'


REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE = 'final_page_too_large'


REMOTE_QUERY_PAGE_ACCEPTED_STATUS_CODE = 202


REMOTE_QUERY_PAGE_RECEIPT_STATUS = 'accepted'


REMOTE_QUERY_PAGE_RECEIPT_KEYS = frozenset(('upload_id', 'batch_index', 'record_offset', 'source_rows', 'status'))


REMOTE_QUERY_FINALIZE_PENDING_STATUS_CODE = 202


REMOTE_QUERY_FINALIZE_PENDING_STATUS = 'processing'


REMOTE_QUERY_FINALIZE_PENDING_KEYS = frozenset(('status', 'completed_page_count', 'expected_page_count'))


REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY = 'remote_queries.execute.intake_test_drive'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX = 'test-drive-'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE = '1'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH = 63


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN = re.compile(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?')


REMOTE_QUERY_UPLOAD_MAX_RETRIES = 4


REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS = 0.1


REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS = 5.0


REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS = 10


REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS = 55


REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS = 300


REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT = (
    REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS,
    REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class UploadCredentials:
    base_url: str
    upload_id: str
    api_key: str
    app_key: str
    test_drive: str | None
    # The run-wide monotonic hard wall for this session's upload requests; None means the
    # request is not wall-scoped (best-effort abort, or a test double driving the client).
    wall_deadline: float | None = None
    # The validated request tracing carrier, injected as standard distributed-tracing headers
    # on every page, finalize, and abort request; None means the Agent supplied no context
    # (mixed versions) and the upload requests carry no tracing headers.
    trace_context: RemoteQueryTraceContext | None = None


class UploadClient(Protocol):
    def register_descriptor(self, creds: UploadCredentials, body: bytes) -> Mapping[str, Any]: ...

    def put_source_page(
        self, creds: UploadCredentials, page: SourcePageUploadMetadata, body: BinaryIO
    ) -> Mapping[str, Any]: ...

    def finalize_run(self, creds: UploadCredentials, expected_page_count: int) -> Mapping[str, Any]: ...

    def abort(self, creds: UploadCredentials) -> None: ...


class UploadAttemptExpired(Exception):
    """One HTTP upload attempt passed its per-attempt deadline; the run itself may retry."""


class DeadlinedPageBody:
    """A file-like view over one page body that kills its HTTP attempt at a deadline."""

    def __init__(self, body: BinaryIO, deadline: float):
        self._body = body
        self._deadline = deadline

    def read(self, amount: int | None = -1) -> bytes:
        if time.monotonic() > self._deadline:
            raise UploadAttemptExpired('Page upload attempt exceeded its per-attempt deadline.')
        if amount is None or amount < 0:
            return self._body.read()
        return self._body.read(amount)

    def seek(self, *args: Any) -> Any:
        return self._body.seek(*args)

    def tell(self) -> int:
        return self._body.tell()


class RequestsUploadClient:
    """Direct HTTP upload client for its-agent-intake. Imports requests lazily."""

    def __init__(
        self,
        timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT,
        tracing: RemoteQueryProducerTracing | None = None,
    ) -> None:
        self._timeout = timeout
        self._tracing = tracing if tracing is not None else NULL_PRODUCER_TRACING

    def _headers(self, creds: UploadCredentials, content_type: str | None = None) -> dict[str, str]:
        headers = {
            'dd-api-key': creds.api_key,
            'dd-application-key': creds.app_key,
        }
        if content_type is not None:
            headers['Content-Type'] = content_type
        if creds.test_drive:
            test_drive_header = REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX + creds.test_drive
            headers[test_drive_header] = REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE
        if creds.trace_context is not None:
            # Tracing headers ride on every request built from these credentials — page,
            # finalize, abort, and each retry attempt — alongside the unchanged auth,
            # content-length, and Test Drive headers.
            headers.update(creds.trace_context.trace_headers())
        return headers

    def register_descriptor(self, creds: UploadCredentials, body: bytes) -> Mapping[str, Any]:
        """Register the immutable source-page descriptor; retries send byte-identical bodies."""
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/descriptor'.format(creds.base_url.rstrip('/'), creds.upload_id)
        _status, response_body = upload_with_retry(
            'POST', url, headers, body, self._timeout, deadline=creds.wall_deadline
        )
        return parse_json_object_response(response_body, 'descriptor registration')

    def put_source_page(
        self, creds: UploadCredentials, page: SourcePageUploadMetadata, buffer: BinaryIO
    ) -> Mapping[str, Any]:
        """Upload one record-complete source page and return the parsed acceptance receipt.

        The buffered page is streamed as the request body with stable declared source
        metadata; every bounded retry rewinds the buffer and resends byte-identical content
        for the same page index. The handoff succeeds on HTTP 202 exactly — intake admits and
        starts the page there — and any other successful status fails closed; its defensive
        `final_page_too_large` rejection surfaces
        as its own failure code so the writer can split the buffered records and retry the
        same index.
        """
        headers = self._headers(creds, REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE)
        headers['X-DD-Source-Page-Bytes'] = str(page.source_bytes)
        headers['X-DD-Source-Page-Rows'] = str(page.rows)
        headers['X-DD-Record-Offset'] = str(page.record_offset)
        # The buffer is complete and rewound before the request, so the exact source size is
        # declared as a stable Content-Length for one non-chunked request body.
        headers['Content-Length'] = str(page.source_bytes)
        url = '{}/uploads/{}/pages/{}'.format(creds.base_url.rstrip('/'), creds.upload_id, page.batch_index)
        status, response_body = upload_with_retry(
            'PUT',
            url,
            headers,
            buffer,
            self._timeout,
            mapped_error_codes={
                REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE: REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE
            },
            deadline=creds.wall_deadline,
            tracing=self._tracing,
            attempt_spans=True,
        )
        if status != REMOTE_QUERY_PAGE_ACCEPTED_STATUS_CODE:
            raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake page upload answered HTTP {}.'.format(status))
        return parse_json_object_response(response_body, 'page upload')

    def finalize_run(self, creds: UploadCredentials, expected_page_count: int) -> Mapping[str, Any]:
        """Finalize the run with its accepted page count, polling pending until authoritative.

        The request body is exactly `{"expected_page_count": N}` — the number of pages
        intake accepted — and every poll replays it byte for byte. Intake answers HTTP 202
        with the safe pending progress fields while accepted pages are still being recorded
        behind the one-page lead, and HTTP 200 with the authoritative final receipt once
        the expected count is complete. Each pending response is strictly verified and
        retried with bounded backoff; the polling never extends the run-wide wall, so once
        the wall expires the next request fails with the retryable wall timeout and the
        run's existing best-effort abort takes over.
        """
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id)
        request_body = canonical_json_bytes({'expected_page_count': expected_page_count})
        backoff = REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS
        while True:
            status, response_body = upload_with_retry(
                'POST', url, headers, request_body, self._timeout, deadline=creds.wall_deadline, tracing=self._tracing
            )
            if status == 200:
                return parse_json_object_response(response_body, 'run finalize')
            if status != REMOTE_QUERY_FINALIZE_PENDING_STATUS_CODE:
                raise RemoteQueryFailure(
                    'invalid_receipt', 'its-agent-intake run finalize answered HTTP {}.'.format(status)
                )
            verify_finalize_pending_response(
                parse_json_object_response(response_body, 'run finalize'), expected_page_count
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)

    def abort(self, creds: UploadCredentials) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/abort'.format(creds.base_url.rstrip('/'), creds.upload_id)
        try:
            # Abort is cleanup: it must stay possible after the run wall expired (that is
            # exactly when it runs), so it carries no deadline. Its requests carry the
            # abort span's context when the run's producer tracing is active.
            upload_with_retry('POST', url, headers, b'{}', self._timeout, tracing=self._tracing)
        except RemoteQueryFailure:
            LOGGER.debug('Remote query upload abort failed (best-effort)')


def parse_json_object_response(body: bytes, source: str) -> Mapping[str, Any]:
    """Parse one intake response, failing closed on a non-JSON or non-object body."""
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake {} response was not valid JSON.'.format(source))
    if not isinstance(parsed, Mapping):
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake {} response was not a JSON object.'.format(source)
        )
    return parsed


def verify_descriptor_receipt_field(response: Mapping[str, Any], field: str, expected: Any) -> None:
    reported = response.get(field)
    if type(reported) is not type(expected) or reported != expected:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake descriptor response reported {} {!r} instead of {!r}.'.format(field, reported, expected),
        )


def verify_descriptor_response(
    response: Mapping[str, Any],
    upload_id: str,
    descriptor: RemoteQueryUploadDescriptor,
    request_bytes: bytes,
) -> None:
    """Fail closed unless intake's descriptor receipt exactly confirms the registration."""
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake descriptor response was not a JSON object.')
    extra_keys = set(response) - {'upload_id', 'format_version', 'include_schema', 'columns', 'sha256'}
    if extra_keys:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake descriptor response carried unknown key(s): {}.'.format(', '.join(sorted(extra_keys))),
        )
    verify_descriptor_receipt_field(response, 'upload_id', upload_id)
    verify_descriptor_receipt_field(response, 'format_version', descriptor.format_version)
    verify_descriptor_receipt_field(response, 'include_schema', descriptor.include_schema)
    verify_descriptor_receipt_field(response, 'columns', len(descriptor.columns))
    verify_descriptor_receipt_field(response, 'sha256', hashlib.sha256(request_bytes).hexdigest())


def verify_source_page_receipt(response: Mapping[str, Any], upload_id: str, page: SourcePageUploadMetadata) -> None:
    """Fail closed unless intake's acceptance receipt matches the page identity exactly."""
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake page upload response was not a JSON object.')
    extra_keys = set(response) - REMOTE_QUERY_PAGE_RECEIPT_KEYS
    if extra_keys:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake page upload response carried unknown key(s): {}.'.format(', '.join(sorted(extra_keys))),
        )
    reported_upload_id = response.get('upload_id')
    if not isinstance(reported_upload_id, str) or reported_upload_id != upload_id:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake page upload response did not confirm the upload session.'
        )
    verify_page_receipt_field(response, 'batch_index', page.batch_index)
    verify_page_receipt_field(response, 'record_offset', page.record_offset)
    verify_page_receipt_field(response, 'source_rows', page.rows)
    if response.get('status') != REMOTE_QUERY_PAGE_RECEIPT_STATUS:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake page upload response did not report the page as accepted.'
        )


def verify_finalize_pending_response(response: Mapping[str, Any], expected_page_count: int) -> None:
    """Fail closed unless intake's `202` pending receipt is exactly the safe progress fields.

    `status` must be the pinned `processing`; `expected_page_count` must echo the
    accepted count this producer declared, and `completed_page_count` must be a
    well-typed count between zero and it. The pending receipt is progress diagnostics
    only — it never authorizes success — so any unknown key fails closed.
    """
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake run finalize response was not a JSON object.')
    extra_keys = set(response) - REMOTE_QUERY_FINALIZE_PENDING_KEYS
    if extra_keys:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake run finalize response carried unknown key(s): {}.'.format(', '.join(sorted(extra_keys))),
        )
    if response.get('status') != REMOTE_QUERY_FINALIZE_PENDING_STATUS:
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake run finalize response did not report processing.')
    completed = response.get('completed_page_count')
    if type(completed) is not int or completed < 0 or completed > expected_page_count:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake run finalize response did not report a usable completed count.'
        )
    reported_expected = response.get('expected_page_count')
    if type(reported_expected) is not int or reported_expected != expected_page_count:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake run finalize response did not echo the expected page count.'
        )


def finalize_totals(response: Mapping[str, Any]) -> tuple[int, int, int]:
    """Intake's authoritative run totals: `(page_count, total_rows, total_bytes)`.

    Run finalization is the authority for the compact completion receipt, so a response that
    does not report all three totals is an invalid receipt rather than a fallback to local
    source accounting.
    """
    totals = []
    for field in ('page_count', 'total_rows', 'total_bytes'):
        reported = response.get(field)
        if type(reported) is not int or reported < 0:
            raise RemoteQueryFailure(
                'invalid_receipt', 'its-agent-intake run finalize response did not report {}.'.format(field)
            )
        totals.append(reported)
    return totals[0], totals[1], totals[2]


def verify_page_receipt_field(response: Mapping[str, Any], field: str, expected: int) -> None:
    reported = response.get(field)
    if type(reported) is not int or reported != expected:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake page upload response reported {} {!r} instead of {}.'.format(field, reported, expected),
        )


def verify_run_finalize_response(response: Mapping[str, Any], upload_id: str) -> None:
    """Fail closed when intake's authoritative response reports a different upload session."""
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake run finalize response was not a JSON object.')
    reported_upload_id = response.get('upload_id')
    if reported_upload_id is None or reported_upload_id == '':
        # The receipt's totals are already intake-derived, and intake's authoritative result
        # is verified by its-agent downstream, so an absent identity echo is accepted.
        return
    if str(reported_upload_id) != upload_id:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake run finalize response reported upload id {!r} instead of {!r}.'.format(
                str(reported_upload_id), upload_id
            ),
        )


def is_transient_upload_status(status: int) -> bool:
    return status == 408 or status == 429 or status >= 500


def parse_error_code(body: bytes) -> str | None:
    """Read intake's public error code from a rejection body, if it carries one."""
    if not body or not body.strip():
        return None
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(parsed, Mapping):
        return None
    error = parsed.get('error')
    if not isinstance(error, Mapping):
        return None
    code = error.get('code')
    return code if isinstance(code, str) else None


def upload_with_retry(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | BinaryIO,
    timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT,
    mapped_error_codes: Mapping[str, str] | None = None,
    deadline: float | None = None,
    tracing: RemoteQueryProducerTracing | None = None,
    attempt_spans: bool = False,
) -> tuple[int, bytes]:
    """Send one intake request with bounded retries; `deadline` is the run-wide wall.

    `tracing`, when given, carries the active producer span's context into the request
    headers in place of the manual trace-context trio: with `attempt_spans` (page
    uploads) each attempt opens its own `remote_queries.page_upload` span and injects
    it, making the intake request spans children of that attempt, while finalize and
    abort requests inject the whole-call span their caller opened. With no span open —
    tracing inactive or degraded, or a descriptor registration — the manual headers
    stand unchanged.
    """
    import requests  # lazy: only the POC upload path needs it

    tracing = tracing if tracing is not None else NULL_PRODUCER_TRACING
    # The default is an empty mapping, normalized once here: descriptor, finalize, and abort
    # map no intake error codes, so their terminal rejections fail closed as upload_failed.
    if mapped_error_codes is None:
        mapped_error_codes = {}
    if not attempt_spans:
        headers = tracing.inject_request_headers(headers)
    backoff = REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS
    # The exhausted sequence's diagnostic: intake's HTTP status (a public counter) or one of
    # the fixed failure categories assigned below, never the caught exception's text or
    # repr — a transport exception can quote the URL, the request body, or credentials.
    last_failure = 'transport failure'
    for attempt in range(REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1):
        if deadline is not None:
            raise_if_timed_out(deadline)
        if not isinstance(body, bytes):
            # Whole-page retry: rewind the buffer so every attempt sends byte-identical
            # content for the same page index with unchanged declared metadata.
            body.seek(0)
        request_body: bytes | BinaryIO = body
        if deadline is not None and not isinstance(body, bytes):
            attempt_deadline = min(deadline, time.monotonic() + REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS)
            request_body = DeadlinedPageBody(body, attempt_deadline)
        # One span per page upload attempt, retry-tagged; the attempt's injected context
        # replaces the manual trace headers on exactly this attempt's request.
        page_attempt = tracing.begin_page_upload_attempt(retry=attempt > 0) if attempt_spans else None
        # The attempt span's bounded outcome classification: no response is a transport
        # failure and any non-2xx answer a rejection, never the response's or exception's
        # text.
        attempt_error: str | None = 'transport'
        attempt_status: int | None = None
        try:
            resp = requests.request(
                method,
                url,
                headers=page_attempt.inject(headers) if page_attempt is not None else dict(headers),
                data=request_body,
                timeout=timeout,
            )
        except UploadAttemptExpired:
            last_failure = 'the page upload attempt exceeded its per-attempt deadline'
        except requests.exceptions.RequestException:
            last_failure = 'transport failure'
        else:
            attempt_status = resp.status_code
            if 200 <= resp.status_code < 300:
                attempt_error = None
                return resp.status_code, resp.content
            attempt_error = 'rejected'
            if is_transient_upload_status(resp.status_code):
                last_failure = 'HTTP status {}'.format(resp.status_code)
            else:
                error_code = parse_error_code(resp.content)
                mapped_code = mapped_error_codes.get(error_code) if error_code is not None else None
                if mapped_code is not None:
                    # A terminal rejection intake defines a producer behavior for (today the
                    # defensive final_page_too_large), surfaced as its own failure code.
                    raise RemoteQueryFailure(
                        mapped_code, 'its-agent-intake rejected the upload with error code {}.'.format(error_code)
                    )
                raise RemoteQueryFailure(
                    'upload_failed', 'upload to its-agent-intake rejected with status {}'.format(resp.status_code)
                )
        finally:
            if page_attempt is not None:
                page_attempt.finish(error=attempt_error, http_status=attempt_status)
        if attempt == REMOTE_QUERY_UPLOAD_MAX_RETRIES:
            break
        time.sleep(backoff)
        backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)
    raise RemoteQueryFailure(
        'upload_failed',
        'upload to its-agent-intake failed after {} attempts: {}'.format(
            REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, last_failure
        ),
        retryable=True,
    )


def get_agent_config(key: str) -> str:
    try:
        value = datadog_agent.get_config(key)
    except Exception:
        # Fixed text and the fixed key name only: the config layer's exception can quote
        # configuration values.
        LOGGER.debug('Unable to read agent config %s', key)
        return ''
    if value is None:
        return ''
    return str(value)


def validate_test_drive_name(value: str | None) -> str | None:
    """Normalize and validate the configured intake Test Drive name.

    The Agent config value names a Test Drive to route intake uploads to. When valid, the
    uploader emits the header `test-drive-<name>: 1`; when absent or invalid, no Test Drive
    header is emitted so the upload follows the permanent-service path. The name is restricted
    to lowercase ASCII alphanumerics and hyphens so it cannot inject arbitrary headers.
    """
    if value is None:
        return None
    name = value.strip().lower()
    if not name:
        return None
    valid = (
        len(name) <= REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH
        and REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN.fullmatch(name) is not None
    )
    if not valid:
        # The configured value never reaches the log; only the verdict and the grammar it
        # failed. The value is customer configuration text, not a safe diagnostic.
        LOGGER.warning(
            'Ignoring invalid remote query intake Test Drive name: it must be 1-%d '
            'lowercase ASCII alphanumerics or hyphens, starting and ending with an alphanumeric.',
            REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH,
        )
        return None
    return name


def resolve_upload_credentials(
    delivery: RemoteQueryResultDelivery,
    started_at: float,
    trace_context: RemoteQueryTraceContext | None = None,
) -> UploadCredentials:
    """Build the session credentials, carrying the run-wide wall for upload retries."""
    test_drive = validate_test_drive_name(get_agent_config(REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY))
    return UploadCredentials(
        base_url=delivery.base_url,
        upload_id=delivery.upload_id,
        api_key=get_agent_config('api_key'),
        app_key=get_agent_config('app_key'),
        test_drive=test_drive,
        wall_deadline=started_at + delivery.limits.timeout_ms / 1000,
        trace_context=trace_context,
    )


def safe_abort(client: UploadClient, creds: UploadCredentials) -> None:
    if not creds.base_url or not creds.upload_id:
        return
    try:
        client.abort(creds)
    except Exception:
        # Fixed text only: the caught exception can quote the URL, the request body, or
        # credentials embedded in a transport error string.
        LOGGER.debug('Remote query upload abort failed (best-effort)')
