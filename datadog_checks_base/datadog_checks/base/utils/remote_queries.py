# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""JSON-page contracts, bounded page buffering, and direct intake uploads.

Database execution and value normalization belong to integration adapters. Only
metadata and the compact receipt return through the Agent's native callback.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, BinaryIO, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.config import is_affirmative

LOGGER = logging.getLogger(__name__)


REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY = 'remote_queries.execute.enable_query_allowlist'


REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES = frozenset(('false', 'no', '0', 'n', 'off'))


REMOTE_QUERY_UPLOAD_MAX_FILE_BYTES = 128 * 1024 * 1024


REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES = 100 * 1024 * 1024 * 1024


REMOTE_QUERY_DEFAULT_TIMEOUT_MS = 30_000


REMOTE_QUERY_ARTIFACT_VERSION = 1


PAGE_SUFFIX = b']}}'


RemoteQueryEmit = Callable[[str, str, bytes], None]


class RemoteQueryTarget(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    host: StrictStr | None = Field(default=None, min_length=1)
    port: StrictInt | None = Field(default=None, ge=1, le=65535)
    dbname: StrictStr | None = Field(default=None, min_length=1)
    database_instance: StrictStr | None = Field(default=None, min_length=1)

    @field_validator('host')
    @classmethod
    def normalize_host(cls, value: str | None) -> str | None:
        if value is None:
            return None
        host = value.strip().lower()
        if host.endswith('.'):
            host = host[:-1]
        if not host:
            raise ValueError('host must be a non-empty string')
        return host

    @field_validator('dbname')
    @classmethod
    def validate_dbname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value:
            raise ValueError('dbname must be a non-empty string')
        if value != value.strip():
            raise ValueError('dbname must not contain surrounding whitespace')
        return value

    @field_validator('database_instance')
    @classmethod
    def validate_database_instance(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError('database_instance must be a non-empty string')
        if value != value.strip():
            raise ValueError('database_instance must not contain surrounding whitespace')
        return value

    @model_validator(mode='after')
    def validate_selector_mode(self) -> 'RemoteQueryTarget':
        null_fields = [
            field_name
            for field_name in ('host', 'port', 'dbname', 'database_instance')
            if field_name in self.model_fields_set and getattr(self, field_name) is None
        ]
        if null_fields:
            raise ValueError('{} must not be null'.format(', '.join(null_fields)))

        if self.database_instance is not None:
            # database_instance selects a loaded check instance; an accompanying dbname
            # requests a logical execution database on that instance's endpoint. Only the
            # endpoint fields are a different selector mode.
            if self.model_fields_set & {'host', 'port'}:
                raise ValueError('target must use exactly one selector mode: database_instance or host/port/dbname')
            return self

        if self.host is None or self.port is None or self.dbname is None:
            raise ValueError('host/port/dbname target requires host, port, and dbname')
        return self


class RemoteQueryUploadLimits(BaseModel):
    """Backend-injected effective limits. Server-owned; never invented by the integration."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    max_file_bytes: StrictInt = Field(alias='maxFileBytes', ge=1, le=REMOTE_QUERY_UPLOAD_MAX_FILE_BYTES)
    max_result_bytes: StrictInt = Field(alias='maxResultBytes', ge=1, le=REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES)
    max_row_bytes: StrictInt = Field(alias='maxRowBytes', ge=1)
    max_columns: StrictInt = Field(alias='maxColumns', ge=1)
    max_schema_bytes: StrictInt = Field(alias='maxSchemaBytes', ge=1)
    # The page-count ceiling itself is worker/intake-owned: the integration only enforces
    # the delivered value.
    max_pages: StrictInt = Field(alias='maxPages', ge=1)
    # The delivery-injected timeout is the run-wide monotonic hard wall: it covers target
    # resolution, query execution, page construction, upload, and retries, and no instance
    # configuration may lengthen it. An instance-configured database timeout may shorten
    # the effective database statement timeout, never the wall itself.
    timeout_ms: StrictInt = Field(default=REMOTE_QUERY_DEFAULT_TIMEOUT_MS, alias='timeoutMs', ge=1)

    @model_validator(mode='after')
    def validate_limit_relations(self) -> 'RemoteQueryUploadLimits':
        if self.max_row_bytes > self.max_file_bytes:
            raise ValueError('maxRowBytes must not exceed maxFileBytes: a row must fit inside one page')
        if self.max_schema_bytes > self.max_file_bytes:
            raise ValueError('maxSchemaBytes must not exceed maxFileBytes')
        if self.max_file_bytes > self.max_result_bytes:
            raise ValueError('maxFileBytes must not exceed maxResultBytes')
        return self


class RemoteQueryResultDelivery(BaseModel):
    """Backend-injected upload instructions and artifact contract metadata.

    The Agent forwards the run-scoped intake session instructions (``uploadId``,
    ``baseUrl``), the effective server-owned limits, the artifact contract version, and the
    authoritative run/task identity used in every page envelope. The session is identified
    by ``uploadId`` alone; the upload calls authorize with the org API/application keys from
    Agent config. Every field is server-owned: the integration validates what it receives
    and never invents values.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    run_id: StrictStr = Field(alias='runId', min_length=1)
    task_id: StrictStr = Field(alias='taskId', min_length=1)
    artifact_version: Literal[REMOTE_QUERY_ARTIFACT_VERSION] = Field(alias='artifactVersion')
    upload_id: StrictStr = Field(alias='uploadId', min_length=1)
    base_url: StrictStr = Field(alias='baseUrl', min_length=1)
    limits: RemoteQueryUploadLimits


class RemoteQueryRequest(BaseModel):
    """A single remote query execution producing bounded JSON result pages."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['produce_json_pages'] = Field(alias='operation')
    target: RemoteQueryTarget
    query: StrictStr = Field(min_length=1)
    include_schema: StrictBool = Field(default=False, alias='includeSchema')
    result_delivery: RemoteQueryResultDelivery = Field(alias='resultDelivery')


@dataclass
class RemoteQueryRunStats:
    """Mutable run accounting shared with the page writer so failures can report partials."""

    rows_emitted: int = 0
    pages_emitted: int = 0
    bytes_emitted: int = 0


@dataclass(frozen=True)
class PageUploadMetadata:
    """The complete identity of one produced page, declared in the page PUT headers.

    Every field is computed while the page is buffered, so the page request and any whole-page
    retry carry stable metadata, and intake's authoritative page receipt is compared against
    these exact values before the run may advance to the next page.
    """

    batch_index: int
    record_offset: int
    page_bytes: int
    rows: int
    sha256_hex: str


@dataclass(frozen=True)
class RemoteQueryEvent:
    event_type: str
    metadata: Mapping[str, Any]
    payload: bytes = b''


class RemoteQueryFailure(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


JSON_NUMBER_PATTERN = re.compile(r'\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\Z')


NON_FINITE_NUMERIC_TEXT = frozenset(('NaN', 'Infinity', '-Infinity'))


def encode_non_finite_text(out: bytearray, text: str) -> None:
    out += json.dumps(text).encode('utf-8')


def encode_raw_number_text(out: bytearray, text: str) -> None:
    if not JSON_NUMBER_PATTERN.match(text):
        raise RemoteQueryFailure('unsupported_value', 'Database returned invalid JSON numeric text.')
    out += text.encode('utf-8')


def encode_decimal(out: bytearray, value: Decimal) -> None:
    if value.is_finite():
        encode_raw_number_text(out, str(value))
        return
    if value.is_nan():
        encode_non_finite_text(out, 'NaN')
    elif value > 0:
        encode_non_finite_text(out, 'Infinity')
    else:
        encode_non_finite_text(out, '-Infinity')


def encode_float(out: bytearray, value: float) -> None:
    if math.isfinite(value):
        # Python repr is the shortest string that round-trips the float.
        encode_raw_number_text(out, repr(value))
    elif math.isnan(value):
        encode_non_finite_text(out, 'NaN')
    elif value > 0:
        encode_non_finite_text(out, 'Infinity')
    else:
        encode_non_finite_text(out, '-Infinity')


def page_prefix(
    *,
    run_id: str,
    task_id: str,
    batch_index: int,
    record_offset: int,
    agent_hostname: str,
    schema_json: bytes | None,
) -> bytes:
    """The envelope bytes through the opening of ``data.items``, with no trailing space.

    ``agent_hostname`` is the executing host's Agent-reported identity, always stamped so the
    console can attribute a run to the agent that produced its pages. It is host identity,
    not job data, so it is threaded from the executing check instance, never the delivery.
    """
    head = (
        '{"version":1,"run_id":%s,"task_id":%s,"batch_index":%d,"record_offset":%d,"agent_hostname":%s,'
        % (json.dumps(run_id), json.dumps(task_id), batch_index, record_offset, json.dumps(agent_hostname))
    ).encode('utf-8')
    parts = [head]
    if schema_json is not None:
        parts.append(b'"schema":')
        parts.append(schema_json)
        parts.append(b',')
    parts.append(b'"data":{"items":[')
    return b''.join(parts)


class PageWriter:
    """Keep one page in RAM through its retries; never accumulate the full result.

    The Agent admits one execution at a time. Each adapter must call discard in
    its finally block so query/encoding failures also release the active page.
    """

    def __init__(
        self,
        delivery: RemoteQueryResultDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        agent_hostname: str,
        schema_json: bytes | None,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
    ):
        self._delivery = delivery
        self._creds = creds
        self._client = client
        self._agent_hostname = agent_hostname
        self._schema_json = schema_json
        self._guard = guard
        self._stats = stats
        self._buffer: io.BytesIO | None = None
        self._page_bytes = 0
        self._page_rows = 0
        self._page_record_offset = 0
        self._page_sha = hashlib.sha256()

    def add_row(self, row_bytes: bytes) -> None:
        if self._buffer is None:
            self._begin_page()
        limits = self._delivery.limits
        page_needed = self._page_bytes + bool(self._page_rows) + len(row_bytes) + len(PAGE_SUFFIX)
        if page_needed > limits.max_file_bytes and self._page_rows:
            self._close_page()
            self._begin_page()
            page_needed = self._page_bytes + len(row_bytes) + len(PAGE_SUFFIX)
        if page_needed > limits.max_file_bytes:
            raise RemoteQueryFailure('row_too_large', 'A single row plus the page envelope exceeds maxFileBytes.')
        if self._stats.bytes_emitted + page_needed > limits.max_result_bytes:
            raise RemoteQueryFailure('max_result_bytes_exceeded', 'Result pages exceed maxResultBytes.')
        if self._page_rows:
            self._append(b',')
        self._append(row_bytes)
        self._page_rows += 1
        self._stats.rows_emitted += 1

    def finish(self) -> dict[str, Any]:
        if self._buffer is None and self._schema_json is not None and self._stats.pages_emitted == 0:
            self._begin_page()  # Preserve schema discovery for an empty result.
        if self._buffer is not None:
            self._close_page()
        response = self._client.finalize_run(self._creds)
        verify_run_finalize_response(response, self._creds.upload_id)
        return {
            'uploadId': self._creds.upload_id,
            'pageCount': self._stats.pages_emitted,
            'totalRows': self._stats.rows_emitted,
            'totalBytes': self._stats.bytes_emitted,
        }

    def discard(self) -> None:
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None

    def _begin_page(self) -> None:
        if self._stats.pages_emitted >= self._delivery.limits.max_pages:
            raise RemoteQueryFailure('max_pages_exceeded', 'Page count reached maxPages.')
        prefix = page_prefix(
            run_id=self._delivery.run_id,
            task_id=self._delivery.task_id,
            batch_index=self._stats.pages_emitted,
            record_offset=self._stats.rows_emitted,
            agent_hostname=self._agent_hostname,
            schema_json=self._schema_json,
        )
        if len(prefix) + len(PAGE_SUFFIX) > self._delivery.limits.max_file_bytes:
            raise RemoteQueryFailure('row_too_large', 'Page envelope exceeds maxFileBytes.')
        self._buffer = io.BytesIO()
        self._page_record_offset = self._stats.rows_emitted
        self._page_sha = hashlib.sha256()
        self._page_bytes = 0
        self._page_rows = 0
        self._append(prefix)

    def _close_page(self) -> None:
        self._guard()
        self._append(PAGE_SUFFIX)
        metadata = PageUploadMetadata(
            batch_index=self._stats.pages_emitted,
            record_offset=self._page_record_offset,
            page_bytes=self._page_bytes,
            rows=self._page_rows,
            sha256_hex=self._page_sha.hexdigest(),
        )
        try:
            self._buffer.seek(0)
            receipt = self._client.put_page(self._creds, metadata, self._buffer)
            verify_page_response(receipt, metadata)
        finally:
            self.discard()
        self._stats.pages_emitted += 1
        self._stats.bytes_emitted += self._page_bytes

    def _append(self, data: bytes) -> None:
        self._buffer.write(data)
        self._page_sha.update(data)
        self._page_bytes += len(data)


def raise_if_timed_out(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise RemoteQueryFailure('timeout', 'Remote query exceeded timeoutMs.', retryable=True)


def remaining_wall_ms(deadline: float) -> int:
    """The wall's remaining milliseconds, clamped to at least 1.

    Derived database timeouts must never reach 0: a zero PostgreSQL statement timeout or a
    zero ClickHouse ``max_execution_time`` would disable the database-side protection
    entirely instead of expiring the run.
    """
    return max(1, int((deadline - time.monotonic()) * 1000))


def raise_if_cancelled(check: Any) -> None:
    # The Agent runtime exposes ``is_cancelled`` as a plain bool attribute on the check
    # object, while other runtimes (and test doubles) may expose a callable hook; honor
    # both shapes. An absent attribute carries no cancellation signal.
    is_cancelled = getattr(check, 'is_cancelled', None)
    if is_cancelled is None:
        return
    cancelled = is_cancelled() if callable(is_cancelled) else is_cancelled
    if cancelled:
        raise RemoteQueryFailure('cancelled', 'Remote query run was cancelled.', retryable=True)


def normalize_target(target: Mapping[str, Any]) -> RemoteQueryTarget:
    try:
        return RemoteQueryTarget.model_validate(target)
    except ValidationError as e:
        raise ValueError(validation_message(e)) from e


def is_query_allowlist_enabled() -> bool:
    try:
        config_value = datadog_agent.get_config(REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY)
    except Exception:
        LOGGER.debug('Unable to read remote query allowlist configuration', exc_info=True)
        return True

    if config_value is None:
        return True
    if isinstance(config_value, str):
        normalized_value = config_value.strip().lower()
        return normalized_value not in REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES

    return is_affirmative(config_value)


REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY = 'remote_queries.execute.intake_test_drive'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX = 'test-drive-'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE = '1'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH = 63


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN = re.compile(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?')


REMOTE_QUERY_UPLOAD_MAX_RETRIES = 4


REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS = 0.1


REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS = 5.0


REMOTE_QUERY_PAGE_UPLOAD_IN_PROGRESS_ERROR_CODE = 'page_upload_in_progress'


REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS = 10


# The socket read timeout below is only a stall backstop: it fires when the socket is fully
# silent for its full span, so a slow-drip response never triggers it and it is not a wall on
# one request's duration. The attempt bound is that wall: it bounds one whole-page upload
# HTTP attempt below the effective public request ceiling measured through the intake data
# plane (~123-124 s, public frontend ingress), with more than 2x headroom, so a page that
# cannot fit the window (application work is budgeted at ~50 s) fails and retries instead of
# hanging until the edge kill or the stall backstop fires.
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


class UploadClient(Protocol):
    def put_page(self, creds: UploadCredentials, page: PageUploadMetadata, body: BinaryIO) -> Mapping[str, Any]: ...

    def finalize_run(self, creds: UploadCredentials) -> Mapping[str, Any]: ...

    def abort(self, creds: UploadCredentials) -> None: ...


class UploadAttemptExpired(Exception):
    """One HTTP upload attempt passed its per-attempt deadline; the run itself may retry."""


class DeadlinedPageBody:
    """A file-like view over one page body that kills its HTTP attempt at a deadline.

    A page is fully buffered before its request starts, so the request carries a stable
    Content-Length and streams the body through ``read``. Checking the attempt deadline at
    every read bounds the attempt's wall-clock upload time even while the socket keeps
    accepting bytes, which the socket-level stall timeout cannot do. The position lives in
    the underlying buffer, so the retry loop's whole-page rewind applies to the view too.
    """

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
    """Direct-page HTTP upload client for its-agent-intake. Imports requests lazily."""

    def __init__(self, timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT) -> None:
        self._timeout = timeout

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
        return headers

    def put_page(self, creds: UploadCredentials, page: PageUploadMetadata, buffer: BinaryIO) -> Mapping[str, Any]:
        """Upload one complete page as a single PUT and return the parsed page receipt.

        The buffered page is streamed as the request body with stable declared metadata;
        every bounded retry rewinds the buffer and resends byte-identical content for the
        same page index.
        """
        headers = self._headers(creds, 'application/json')
        headers['X-DD-Page-Bytes'] = str(page.page_bytes)
        headers['X-DD-Page-Rows'] = str(page.rows)
        headers['X-DD-Record-Offset'] = str(page.record_offset)
        headers['X-DD-Page-SHA256'] = page.sha256_hex
        # The buffer is complete and rewound before the request, so the exact page size is
        # declared as a stable Content-Length for one non-chunked request body.
        headers['Content-Length'] = str(page.page_bytes)
        url = '{}/uploads/{}/pages/{}'.format(creds.base_url.rstrip('/'), creds.upload_id, page.batch_index)
        _status, response_body = upload_with_retry(
            'PUT',
            url,
            headers,
            buffer,
            self._timeout,
            retryable_error_codes=frozenset((REMOTE_QUERY_PAGE_UPLOAD_IN_PROGRESS_ERROR_CODE,)),
            deadline=creds.wall_deadline,
        )
        return parse_page_receipt_body(response_body)

    def finalize_run(self, creds: UploadCredentials) -> Mapping[str, Any]:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id)
        _status, body = upload_with_retry('POST', url, headers, b'{}', self._timeout, deadline=creds.wall_deadline)
        return parse_finalize_run_body(body)

    def abort(self, creds: UploadCredentials) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/abort'.format(creds.base_url.rstrip('/'), creds.upload_id)
        try:
            # Abort is cleanup: it must stay possible after the run wall expired (that is
            # exactly when it runs), so it carries no deadline.
            upload_with_retry('POST', url, headers, b'{}', self._timeout)
        except RemoteQueryFailure:
            LOGGER.debug('Remote query upload abort failed (best-effort)', exc_info=True)


def parse_page_receipt_body(body: bytes) -> Mapping[str, Any]:
    """Parse the page-upload response, failing closed on a non-JSON or non-object body."""
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake page upload response was not valid JSON.')
    if not isinstance(parsed, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake page upload response was not a JSON object.')
    return parsed


def parse_finalize_run_body(body: bytes) -> Mapping[str, Any]:
    """Parse the run-finalize response, failing closed on a non-JSON or non-object body."""
    if not body or not body.strip():
        return {}
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake run finalize response was not valid JSON.')
    if not isinstance(parsed, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake run finalize response was not a JSON object.')
    return parsed


def verify_page_response(response: Mapping[str, Any], page: PageUploadMetadata) -> None:
    """Fail closed unless intake's authoritative page receipt matches the produced page.

    Every receipt field the producer declared is compared exactly before the buffer is
    deleted and the next page may be produced. The object ``key`` is server-derived and
    opaque to the producer, so it is validated structurally; its exact value is verified
    downstream by its-agent.
    """
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake page upload response was not a JSON object.')
    key = response.get('key')
    if not isinstance(key, str) or not key:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake page upload response did not carry a usable object key.'
        )
    verify_page_receipt_field(response, 'batch_index', page.batch_index)
    verify_page_receipt_field(response, 'record_offset', page.record_offset)
    verify_page_receipt_field(response, 'bytes', page.page_bytes)
    verify_page_receipt_field(response, 'rows', page.rows)
    reported_sha256 = response.get('sha256')
    if reported_sha256 != page.sha256_hex:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake page upload response reported sha256 {!r} instead of {!r}.'.format(
                str(reported_sha256), page.sha256_hex
            ),
        )


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
        # The compact receipt is the integration's own accounting; intake's authoritative
        # result is verified by its-agent, so an absent identity echo is accepted.
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
    retryable_error_codes: frozenset[str] = frozenset(),
    deadline: float | None = None,
) -> tuple[int, bytes]:
    """Send one intake request with bounded retries; ``deadline`` is the run-wide wall.

    With a deadline, no attempt starts after the wall and every whole-page attempt is
    additionally bounded by ``REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS`` capped at the wall,
    so a bounded retry sequence can never meaningfully extend the wall. A page attempt
    that passes its own bound is killed mid-body and retried with whole-page rewind.
    """
    import requests  # lazy: only the POC upload path needs it

    backoff = REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS
    last_err: Any = None
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
        try:
            resp = requests.request(method, url, headers=dict(headers), data=request_body, timeout=timeout)
        except UploadAttemptExpired as e:
            last_err = e
        except requests.exceptions.RequestException as e:
            last_err = e
        else:
            if 200 <= resp.status_code < 300:
                return resp.status_code, resp.content
            if is_transient_upload_status(resp.status_code) or (
                retryable_error_codes and parse_error_code(resp.content) in retryable_error_codes
            ):
                last_err = 'status {}'.format(resp.status_code)
            else:
                raise RemoteQueryFailure(
                    'upload_failed', 'upload to its-agent-intake rejected with status {}'.format(resp.status_code)
                )
        if attempt == REMOTE_QUERY_UPLOAD_MAX_RETRIES:
            break
        time.sleep(backoff)
        backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)
    raise RemoteQueryFailure(
        'upload_failed',
        'upload to its-agent-intake failed after {} attempts: {}'.format(REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, last_err),
        retryable=True,
    )


def get_agent_config(key: str) -> str:
    try:
        value = datadog_agent.get_config(key)
    except Exception:
        LOGGER.debug('Unable to read agent config %s', key, exc_info=True)
        return ''
    if value is None:
        return ''
    return str(value)


def validate_test_drive_name(value: str | None) -> str | None:
    """Normalize and validate the configured intake Test Drive name.

    The Agent config value names a Test Drive to route intake uploads to. When valid, the
    uploader emits the header ``test-drive-<name>: 1``; when absent or invalid, no Test Drive
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
        LOGGER.warning(
            'Ignoring invalid remote query intake Test Drive name %r: it must be 1-%d '
            'lowercase ASCII alphanumerics or hyphens, starting and ending with an alphanumeric.',
            value,
            REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH,
        )
        return None
    return name


def resolve_upload_credentials(delivery: RemoteQueryResultDelivery, started_at: float) -> UploadCredentials:
    """Build the session credentials, carrying the run-wide wall for upload retries.

    The wall is derived from the same started-at origin and delivered timeout the producer
    uses for its monotonic guard, so the guard and the upload client enforce one deadline.
    """
    test_drive = validate_test_drive_name(get_agent_config(REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY))
    return UploadCredentials(
        base_url=delivery.base_url,
        upload_id=delivery.upload_id,
        api_key=get_agent_config('api_key'),
        app_key=get_agent_config('app_key'),
        test_drive=test_drive,
        wall_deadline=started_at + delivery.limits.timeout_ms / 1000,
    )


def safe_abort(client: UploadClient, creds: UploadCredentials) -> None:
    if not creds.base_url or not creds.upload_id:
        return
    try:
        client.abort(creds)
    except Exception:
        LOGGER.debug('Remote query upload abort failed (best-effort)', exc_info=True)


def started_metadata(request: RemoteQueryRequest) -> dict[str, Any]:
    delivery = request.result_delivery
    limits = delivery.limits
    return {
        'status': 'STARTED',
        'operation': request.operation,
        'includeSchema': request.include_schema,
        'resultDelivery': {
            'runId': delivery.run_id,
            'taskId': delivery.task_id,
            'uploadId': delivery.upload_id,
            'baseUrl': delivery.base_url,
            'artifactVersion': delivery.artifact_version,
            'limits': {
                'maxFileBytes': limits.max_file_bytes,
                'maxResultBytes': limits.max_result_bytes,
                'maxRowBytes': limits.max_row_bytes,
                'maxColumns': limits.max_columns,
                'maxSchemaBytes': limits.max_schema_bytes,
                'maxPages': limits.max_pages,
                'timeoutMs': limits.timeout_ms,
            },
        },
    }


def succeeded_metadata(receipt: Mapping[str, Any], stats: RemoteQueryRunStats, started_at: float) -> dict[str, Any]:
    return {
        'status': 'SUCCEEDED',
        'upload_receipt': dict(receipt),
        'stats': stats_metadata(stats, started_at),
    }


def stats_metadata(stats: RemoteQueryRunStats, started_at: float) -> dict[str, Any]:
    return {
        'rowsEmitted': stats.rows_emitted,
        'pagesEmitted': stats.pages_emitted,
        'bytesEmitted': stats.bytes_emitted,
        'elapsedMs': elapsed_ms(started_at),
    }


def failed_event(
    code: str,
    message: str,
    retryable: bool = False,
    stats: Mapping[str, Any] | None = None,
    elapsed_ms: int | None = None,
) -> RemoteQueryEvent:
    metadata: dict[str, Any] = {
        'status': 'FAILED',
        'error': {'code': code, 'message': message, 'retryable': retryable},
    }
    if stats is not None:
        metadata['stats'] = dict(stats)
    elif elapsed_ms is not None:
        metadata['stats'] = {'elapsedMs': elapsed_ms}
    return RemoteQueryEvent('error', metadata)


def emit_event(emit: RemoteQueryEmit, event: RemoteQueryEvent) -> None:
    emit(event.event_type, json.dumps(event.metadata, default=str), event.payload)


def elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def validation_message(error: ValidationError) -> str:
    details = []
    for item in error.errors(include_input=False):
        location = validation_location(item.get('loc', ()))
        message = item.get('msg', 'Invalid value')
        if location:
            details.append(f'{location}: {message}')
        else:
            details.append(message)
    return 'Invalid remote query request: {}'.format('; '.join(details))


def validation_location(location: tuple[Any, ...]) -> str:
    return '.'.join(str(part) for part in location)
