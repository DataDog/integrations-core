# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query upload."""

from __future__ import annotations

import json
import logging
import random
import re
import socket
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, BinaryIO, Protocol

from datadog_checks.base.agent import datadog_agent

from .contract import (
    RemoteQueryFailure,
    RemoteQueryResultDelivery,
    RemoteQueryTraceContext,
    SourcePageUploadMetadata,
    canonical_json_bytes,
)
from .events import raise_if_timed_out
from .tracing import NULL_PRODUCER_TRACING, RemoteQueryProducerTracing

LOGGER = logging.getLogger(__name__)


REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE = 'text/csv'


REMOTE_QUERY_RESULT_FILE_TOO_LARGE_ERROR_CODE = 'result_file_too_large'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY = 'remote_queries.execute.intake_test_drive'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX = 'test-drive-'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE = '1'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH = 63


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN = re.compile(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?')


# The intake base URL receives the org API key, so it is validated here against the Agent's own
# site, independently of whatever transport delivered `resultDelivery`. The accepted shape is
# exactly `https://<site host>[:443]` plus an optional path of plain segments: no userinfo,
# query, fragment, backslash, percent-encoding, dot segment, whitespace, or control character.
REMOTE_QUERY_INTAKE_HOST_LABEL = r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?'


REMOTE_QUERY_INTAKE_PATH_SEGMENT = r'(?!\.{1,2}(?:/|\Z))[A-Za-z0-9._~-]+'


REMOTE_QUERY_INTAKE_BASE_URL_PATTERN = re.compile(
    r'\A(?i:https)://(?P<host>{label}(?:\.{label})+)(?::443)?(?P<path>(?:/{segment})*/?)\Z'.format(
        label=REMOTE_QUERY_INTAKE_HOST_LABEL, segment=REMOTE_QUERY_INTAKE_PATH_SEGMENT
    )
)


REMOTE_QUERY_INTAKE_SITE_PATTERN = re.compile(r'\A{label}(?:\.{label})+\Z'.format(label=REMOTE_QUERY_INTAKE_HOST_LABEL))


REMOTE_QUERY_INTAKE_BASE_URL_MAX_LENGTH = 2048


REMOTE_QUERY_UPLOAD_MAX_RETRIES = 4


REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS = 0.1


REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS = 5.0


REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS = 10


REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS = 360


REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS = 360


# The longest one socket send may block while the request is written, i.e. how long intake (or
# a proxy in front of it) may stop draining the body before the attempt is abandoned. The
# (connect, read) timeout tuple cannot express this: urllib3 keeps the connect timeout on the
# socket while the body is sent and applies the read timeout only once the response is awaited.
# Each send is also capped by what remains of the attempt's deadline.
REMOTE_QUERY_UPLOAD_HTTP_WRITE_TIMEOUT_SECONDS = 30


REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT = (
    REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS,
    REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class UploadCredentials:
    base_url: str
    upload_id: str
    api_key: str
    test_drive: str | None
    # The run-wide monotonic hard wall for this session's upload requests; None means the
    # request is not wall-scoped (best-effort abort, or a test double driving the client).
    wall_deadline: float | None = None
    # The validated request tracing carrier, injected as standard distributed-tracing headers
    # on every page, finalize, and abort request; None means the Agent supplied no context
    # (mixed versions) and the upload requests carry no tracing headers.
    trace_context: RemoteQueryTraceContext | None = None


class UploadClient(Protocol):
    def register_descriptor(self, creds: UploadCredentials, body: bytes) -> None: ...

    def put_source_page(self, creds: UploadCredentials, page: SourcePageUploadMetadata, body: BinaryIO) -> None: ...

    def finalize_run(self, creds: UploadCredentials, expected_page_count: int) -> None: ...

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


def stall_bounded_pool_classes(write_timeout: float, deadline: float | None) -> dict[str, type]:
    """Build urllib3 pool classes whose connections bound each body send.

    urllib3 leaves the connect timeout on the socket while it writes the request, so a
    slow-draining peer would be cut off after the connect timeout. Connections from these
    pools instead raise the socket timeout to `write_timeout` as soon as they are connected,
    capped by the time left until `deadline` (a `time.monotonic` value, or None for no
    deadline). urllib3 then restores the read timeout itself once the body is sent.
    A send that stalls past the deadline raises `UploadAttemptExpired`.

    The classes are built per call because urllib3 constructs connections itself and gives
    callers no way to hand a per-request value to them.
    """
    from urllib3.connection import HTTPConnection, HTTPSConnection
    from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

    class StallBoundedConnection:
        def _bound_send_timeout(self) -> None:
            timeout = float(write_timeout)
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise UploadAttemptExpired('Page upload attempt exceeded its per-attempt deadline.')
                timeout = min(timeout, remaining)
            self.sock.settimeout(timeout)

        def connect(self) -> None:
            super().connect()
            self._bound_send_timeout()

        def send(self, data: Any) -> None:
            # A reused connection is reset to the connect timeout before each request.
            if self.sock is not None:
                self._bound_send_timeout()
            try:
                super().send(data)
            except socket.timeout:
                if deadline is not None and time.monotonic() >= deadline:
                    raise UploadAttemptExpired('Page upload attempt exceeded its per-attempt deadline.')
                raise

    class Connection(StallBoundedConnection, HTTPConnection):
        pass

    class SecureConnection(StallBoundedConnection, HTTPSConnection):
        pass

    class Pool(HTTPConnectionPool):
        ConnectionCls = Connection

    class SecurePool(HTTPSConnectionPool):
        ConnectionCls = SecureConnection

    return {'http': Pool, 'https': SecurePool}


def stall_bounded_adapter(write_timeout: float, deadline: float | None) -> Any:
    """A `requests` adapter that bounds each request-body send; see `stall_bounded_pool_classes`."""
    from requests.adapters import HTTPAdapter
    from urllib3.poolmanager import pool_classes_by_scheme

    pool_classes = stall_bounded_pool_classes(write_timeout, deadline)

    class StallBoundedAdapter(HTTPAdapter):
        def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
            super().init_poolmanager(*args, **kwargs)
            self.poolmanager.pool_classes_by_scheme = pool_classes

        def proxy_manager_for(self, proxy: str, **proxy_kwargs: Any) -> Any:
            manager = super().proxy_manager_for(proxy, **proxy_kwargs)
            # SOCKS managers carry their own pool classes, which are left untouched.
            if manager.pool_classes_by_scheme is pool_classes_by_scheme:
                manager.pool_classes_by_scheme = pool_classes
            return manager

    return StallBoundedAdapter()


class RequestsUploadClient:
    """Direct HTTP upload client for its-agent-intake. Imports requests lazily."""

    def __init__(
        self,
        timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT,
        tracing: RemoteQueryProducerTracing | None = None,
        write_timeout: float = REMOTE_QUERY_UPLOAD_HTTP_WRITE_TIMEOUT_SECONDS,
    ) -> None:
        self._timeout = timeout
        self._write_timeout = write_timeout
        self._tracing = tracing if tracing is not None else NULL_PRODUCER_TRACING

    def _headers(self, creds: UploadCredentials, content_type: str | None = None) -> dict[str, str]:
        headers = {
            'dd-api-key': creds.api_key,
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

    def register_descriptor(self, creds: UploadCredentials, body: bytes) -> None:
        """Register the immutable descriptor; retries send byte-identical bodies."""
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/descriptor'.format(creds.base_url.rstrip('/'), creds.upload_id)
        status, _ = upload_with_retry(
            'POST', url, headers, body, self._timeout, deadline=creds.wall_deadline, write_timeout=self._write_timeout
        )
        verify_no_content_response(status, 'descriptor registration')

    def put_source_page(self, creds: UploadCredentials, page: SourcePageUploadMetadata, buffer: BinaryIO) -> None:
        """Upload a complete page, acknowledged only after intake records it.

        Retries rewind the same fixed-length, uncompressed body. An oversized result file
        is surfaced separately so the writer can split records and retry the same index.
        """
        headers = self._headers(creds, REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE)
        headers['X-DD-Source-Page-Rows'] = str(page.rows)
        headers['X-DD-Record-Offset'] = str(page.record_offset)
        headers['Content-Length'] = str(page.source_bytes)
        url = '{}/uploads/{}/pages/{}'.format(creds.base_url.rstrip('/'), creds.upload_id, page.batch_index)
        status, _ = upload_with_retry(
            'PUT',
            url,
            headers,
            buffer,
            self._timeout,
            mapped_error_codes={
                REMOTE_QUERY_RESULT_FILE_TOO_LARGE_ERROR_CODE: REMOTE_QUERY_RESULT_FILE_TOO_LARGE_ERROR_CODE
            },
            deadline=creds.wall_deadline,
            tracing=self._tracing,
            attempt_spans=True,
            write_timeout=self._write_timeout,
        )
        verify_no_content_response(status, 'page upload')

    def finalize_run(self, creds: UploadCredentials, expected_page_count: int) -> None:
        """Finalize with the recorded page count; a 204 confirms completion."""
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id)
        status, _ = upload_with_retry(
            'POST',
            url,
            headers,
            canonical_json_bytes({'expected_page_count': expected_page_count}),
            self._timeout,
            deadline=creds.wall_deadline,
            tracing=self._tracing,
            write_timeout=self._write_timeout,
        )
        verify_no_content_response(status, 'run finalize')

    def abort(self, creds: UploadCredentials) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/abort'.format(creds.base_url.rstrip('/'), creds.upload_id)
        try:
            # Abort is cleanup: it must stay possible after the run wall expired (that is
            # exactly when it runs), so it carries no deadline. Its requests carry the
            # abort span's context when the run's producer tracing is active.
            upload_with_retry(
                'POST', url, headers, b'{}', self._timeout, tracing=self._tracing, write_timeout=self._write_timeout
            )
        except RemoteQueryFailure:
            LOGGER.debug('Remote query upload abort failed (best-effort)')


def verify_no_content_response(status: int, operation: str) -> None:
    """Only intake's synchronous, status-only acknowledgement confirms success."""
    if status != 204:
        raise RemoteQueryFailure('upload_failed', 'its-agent-intake {} answered HTTP {}.'.format(operation, status))


def is_transient_upload_status(status: int) -> bool:
    return status in (500, 503)


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
    write_timeout: float = REMOTE_QUERY_UPLOAD_HTTP_WRITE_TIMEOUT_SECONDS,
) -> tuple[int, bytes]:
    """Send one intake request with bounded retries; `deadline` is the run-wide wall.

    `timeout` is the (connect, read) pair; `write_timeout` separately bounds how long one
    send of the request body may stall, capped by the page attempt's deadline when there is one.

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
    attempt = 0
    failures = 0
    while True:
        if deadline is not None:
            raise_if_timed_out(deadline)
        if not isinstance(body, bytes):
            # Whole-page retry: rewind the buffer so every attempt sends byte-identical
            # content for the same page index with unchanged declared metadata.
            body.seek(0)
        request_body: bytes | BinaryIO = body
        attempt_deadline: float | None = None
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
            # One session per attempt: its adapter is bound to this attempt's deadline, and a
            # fresh connection is what lets the write timeout replace the connect timeout.
            with requests.Session() as session:
                adapter = stall_bounded_adapter(write_timeout, attempt_deadline)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                resp = session.request(
                    method,
                    url,
                    headers=page_attempt.inject(headers) if page_attempt is not None else dict(headers),
                    data=request_body,
                    timeout=timeout,
                    allow_redirects=False,
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
                    # defensive result_file_too_large), surfaced as its own failure code.
                    raise RemoteQueryFailure(
                        mapped_code, 'its-agent-intake rejected the upload with error code {}.'.format(error_code)
                    )
                raise RemoteQueryFailure(
                    'upload_failed',
                    'upload to its-agent-intake rejected with status {} and error code {}.'.format(
                        resp.status_code, error_code or 'unknown'
                    ),
                )
        finally:
            if page_attempt is not None:
                page_attempt.finish(error=attempt_error, http_status=attempt_status)
        # Intake uses unavailable for capacity as well as interruption/shutdown. With
        # a run wall, retry all 503s until that wall; no distinct capacity code exists.
        if attempt_status != 503 or deadline is None:
            failures += 1
            if failures > REMOTE_QUERY_UPLOAD_MAX_RETRIES:
                break
        delay = random.uniform(backoff / 2, backoff)
        if deadline is not None:
            delay = min(delay, max(0, deadline - time.monotonic()))
        time.sleep(delay)
        backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)
        attempt += 1
    raise RemoteQueryFailure(
        'upload_failed',
        'upload to its-agent-intake failed after {} attempts: {}'.format(attempt + 1, last_failure),
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


def validate_intake_base_url(base_url: str, site: str | None) -> None:
    """Fail closed unless `base_url` may receive the org API key: an https URL on the Agent's site.

    The host must be the configured Datadog site or a subdomain of it, with no port other than
    443; the path may only be plain segments. A missing or malformed site fails closed too. The
    error text never echoes the URL, which is hostile input until this check passes.
    """
    site = (site or '').strip().lower()
    if not site:
        raise RemoteQueryFailure(
            'invalid_request', 'resultDelivery.baseUrl cannot be checked: the Agent site is not configured.'
        )
    if REMOTE_QUERY_INTAKE_SITE_PATTERN.match(site) is None:
        raise RemoteQueryFailure(
            'invalid_request', 'resultDelivery.baseUrl cannot be checked: the Agent site is not a valid host.'
        )
    match = (
        REMOTE_QUERY_INTAKE_BASE_URL_PATTERN.match(base_url)
        if len(base_url) <= REMOTE_QUERY_INTAKE_BASE_URL_MAX_LENGTH
        else None
    )
    if match is None:
        raise RemoteQueryFailure(
            'invalid_request',
            'resultDelivery.baseUrl must be an https URL without userinfo, query, fragment, or unusual path or port.',
        )
    host = match.group('host').lower()
    if host != site and not host.endswith('.' + site):
        raise RemoteQueryFailure('invalid_request', "resultDelivery.baseUrl must be on the Agent's site.")


def resolve_upload_credentials(
    delivery: RemoteQueryResultDelivery,
    started_at: float,
    trace_context: RemoteQueryTraceContext | None = None,
) -> UploadCredentials:
    """Build the upload credentials, carrying the run-wide wall for upload retries.

    The delivery's base URL is validated against the Agent's site before the API key is read,
    so the key can never be handed to a URL this module has not itself accepted.
    """
    validate_intake_base_url(delivery.base_url, get_agent_config('site'))
    test_drive = validate_test_drive_name(get_agent_config(REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY))
    return UploadCredentials(
        base_url=delivery.base_url,
        upload_id=delivery.upload_id,
        api_key=get_agent_config('api_key'),
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
