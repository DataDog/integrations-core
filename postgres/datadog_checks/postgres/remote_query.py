# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.config import is_affirmative

REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY = 'remote_queries.execute.enable_query_allowlist'
REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES = frozenset(('false', 'no', '0', 'n', 'off'))
REMOTE_QUERY_COPY_SQL_ALLOWLIST = frozenset(
    (
        'SELECT 1 AS value',
        'SELECT city, country FROM cities ORDER BY city',
        'SELECT current_database() AS current_db, expected_agent_hostname, expected_postgres_host, '
        'expected_postgres_port, expected_dbname, marker FROM remote_query_identity',
        "SELECT decode('00ff80', 'hex') AS payload",
        "SELECT repeat('x', 1048576) AS payload",
        "SELECT repeat('x', 2097152) AS payload",
        "SELECT repeat('x', 4194304) AS payload",
        "SELECT repeat('x', 8388608) AS payload",
        "SELECT repeat('x', 16777216) AS payload",
        "SELECT repeat('x', 33554432) AS payload",
        "SELECT i, repeat('x', 1000) AS payload FROM generate_series(1, 3000) AS i",
    )
)

# Server-owned maximums for the POC multipart upload path. The backend selects/clamps these,
# not the caller. The multipart part size is independent of the COPY read chunk size
# (limits.chunkBytes); it may be up to 128 MiB. maxBytes must not exceed the caller/backend COPY
# safety cap (limits.maxBytes).
REMOTE_QUERY_UPLOAD_MAX_PART_BYTES = 128 * 1024 * 1024
REMOTE_QUERY_UPLOAD_MAX_TOTAL_BYTES = 10 * 1024 * 1024 * 1024

CopyStreamFormat = Literal['csv', 'binary']
ResultDeliveryMode = Literal['POC_PUBLIC_MULTIPART_UPLOAD']
ResultDeliveryFormat = Literal['csv']
ResultDeliveryCompression = Literal['none']
CopyStreamEmit = Callable[[str, str, bytes], None]

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

LOGGER = logging.getLogger(__name__)


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
            field
            for field in ('host', 'port', 'dbname', 'database_instance')
            if field in self.model_fields_set and getattr(self, field) is None
        ]
        if null_fields:
            raise ValueError('{} must not be null'.format(', '.join(null_fields)))

        host_fields = self.model_fields_set & {'host', 'port', 'dbname'}
        if self.database_instance is not None:
            if host_fields:
                raise ValueError('target must use exactly one selector mode: database_instance or host/port/dbname')
            return self

        if self.host is None or self.port is None or self.dbname is None:
            raise ValueError('host/port/dbname target requires host, port, and dbname')
        return self


class RemoteQueryCopyLimits(BaseModel):
    """Validate byte-streaming limits for COPY export mode."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    chunk_bytes: StrictInt = Field(default=1_048_576, alias='chunkBytes', ge=1)
    max_bytes: StrictInt = Field(default=64 * 1_048_576, alias='maxBytes', ge=1)
    max_row_bytes: StrictInt = Field(default=8 * 1_048_576, alias='maxRowBytes', ge=1)
    timeout_ms: StrictInt = Field(default=30_000, alias='timeoutMs', ge=1)


class RemoteQueryResultDelivery(BaseModel):
    """Validate optional result-delivery upload instructions for direct upload to its-agent-intake.

    When present, the integration uploads bounded COPY bytes directly to its-agent-intake over
    HTTP. The Agent forwards the intake base URL and scoped upload token here; the integration
    reads the org API key and POC application key from Agent config via ``datadog_agent.get_config``
    and attaches them to its own HTTP upload requests. The integration performs the HTTP upload
    itself; bulk part bytes never traverse the native emit bridge, AgentSecure, PAR, or AP action
    output. Omitting ``resultDelivery`` keeps the existing inline streaming behavior unchanged.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    mode: ResultDeliveryMode
    upload_id: StrictStr = Field(alias='uploadId', min_length=1)
    base_url: StrictStr = Field(alias='baseUrl', min_length=1)
    token: StrictStr = Field(alias='token', min_length=1)
    part_bytes: StrictInt = Field(alias='partBytes', ge=1, le=REMOTE_QUERY_UPLOAD_MAX_PART_BYTES)
    max_bytes: StrictInt = Field(alias='maxBytes', ge=1, le=REMOTE_QUERY_UPLOAD_MAX_TOTAL_BYTES)
    format: ResultDeliveryFormat = 'csv'
    compression: ResultDeliveryCompression = 'none'

    @model_validator(mode='after')
    def validate_part_within_max(self) -> 'RemoteQueryResultDelivery':
        if self.part_bytes > self.max_bytes:
            raise ValueError('partBytes must not exceed maxBytes')
        return self


class RemoteQueryCopyRequest(BaseModel):
    """Accept only explicit COPY byte-stream export requests."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['copy_stream'] = Field(alias='operation')
    target: RemoteQueryTarget
    query: StrictStr = Field(min_length=1)
    format: CopyStreamFormat = 'csv'
    limits: RemoteQueryCopyLimits = Field(default_factory=RemoteQueryCopyLimits)
    result_delivery: RemoteQueryResultDelivery | None = Field(default=None, alias='resultDelivery')

    @model_validator(mode='after')
    def validate_format_consistency(self) -> 'RemoteQueryCopyRequest':
        # When resultDelivery is present, the COPY stream format must match the upload format so the
        # emitted bytes and the finalized object agree. The current contract allows only ``csv`` for
        # upload, so upload mode is CSV-only; a ``binary`` COPY stream with a ``csv`` upload is rejected.
        if self.result_delivery is not None and self.format != self.result_delivery.format:
            raise ValueError('format must match resultDelivery.format when resultDelivery is present')
        return self

    @model_validator(mode='after')
    def validate_max_within_limits(self) -> 'RemoteQueryCopyRequest':
        # The upload byte cap must not widen the caller/backend COPY safety cap. Fail closed so a
        # backend-injected resultDelivery cannot raise the integration's configured byte ceiling;
        # an equal or smaller upload maxBytes is accepted. ``partBytes`` (the multipart part size)
        # and ``limits.chunkBytes`` (the COPY streaming chunk size) are distinct concepts, so
        # partBytes may exceed chunkBytes: the COPY stream emits chunkBytes-sized events that the
        # upload client aggregates into partBytes-sized parts.
        if self.result_delivery is not None:
            if self.result_delivery.max_bytes > self.limits.max_bytes:
                raise ValueError('resultDelivery.maxBytes must not exceed limits.maxBytes')
        return self


@dataclass(frozen=True)
class StaticPostgresCheckRegistry:
    checks: Sequence['PostgreSql']

    def iter_postgres_checks(self) -> Iterable['PostgreSql']:
        return iter(self.checks)


@dataclass(frozen=True)
class _CopyStreamState:
    sequence: int = 0
    chunks_emitted: int = 0
    bytes_emitted: int = 0


@dataclass(frozen=True)
class CopyStreamEvent:
    event_type: str
    metadata: Mapping[str, Any]
    payload: bytes = b''


class _CopyStreamFailure(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class PostgresCheckRegistry(Protocol):
    def iter_postgres_checks(self) -> Iterable['PostgreSql']: ...


def execute_agent_rpc_stream_copy(
    request_json: str | bytes | bytearray, check: 'PostgreSql', emit: CopyStreamEmit
) -> None:
    """Execute an explicit COPY byte-stream request and emit chunk events."""
    try:
        request = json.loads(request_json)
    except (TypeError, ValueError):
        _emit_copy_event(
            emit,
            _stream_failed_event(
                'invalid_request', 'Invalid remote query request: request_json must be a valid JSON object.'
            ),
        )
        return

    if not isinstance(request, Mapping):
        _emit_copy_event(
            emit,
            _stream_failed_event(
                'invalid_request', 'Invalid remote query request: request_json must be a JSON object.'
            ),
        )
        return

    if _is_upload_request(request):
        _execute_upload_stream(request, check, emit)
        return

    events = iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check]))
    try:
        for event in events:
            _emit_copy_event(emit, event)
    except BaseException:
        events.close()
        raise


def iter_agent_rpc_stream_copy_events(request: Any, registry: PostgresCheckRegistry) -> Iterator[CopyStreamEvent]:
    """Yield COPY byte-stream events for unit tests and callback adaptation."""
    started_at = time.monotonic()
    try:
        parsed_request = RemoteQueryCopyRequest.model_validate(request)
    except ValidationError as e:
        yield _stream_failed_event('invalid_request', _validation_message(e), elapsed_ms=_elapsed_ms(started_at))
        return

    if not _is_query_allowed(parsed_request.query):
        yield _stream_failed_event(
            'invalid_request',
            'Invalid remote query request: query is not allowlisted.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    target = parsed_request.target
    matches = _resolve_matches(target, registry.iter_postgres_checks())
    LOGGER.debug('Remote query COPY stream target match count: %d', len(matches))
    if not matches:
        yield _stream_failed_event(
            'target_not_found',
            'No loaded Postgres integration instance matched target selector.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return
    if len(matches) > 1:
        yield _stream_failed_event(
            'target_ambiguous',
            'More than one loaded Postgres integration instance matched target selector.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    execution_dbname = _dbname_from_check(matches[0])
    if execution_dbname is None:
        yield _stream_failed_event(
            'target_unavailable',
            'Matched Postgres check does not expose a configured database name.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    yield from _iter_copy_stream_events(matches[0], parsed_request, execution_dbname, started_at)


def normalize_target(target: Mapping[str, Any]) -> RemoteQueryTarget:
    try:
        return RemoteQueryTarget.model_validate(target)
    except ValidationError as e:
        raise ValueError(_validation_message(e)) from e


def _resolve_matches(target: RemoteQueryTarget, checks: Iterable['PostgreSql']) -> list['PostgreSql']:
    if target.database_instance is not None:
        return [check for check in checks if getattr(check, 'database_identifier', None) == target.database_instance]
    return [check for check in checks if _target_from_check(check) == target]


def _target_from_check(check: 'PostgreSql') -> RemoteQueryTarget | None:
    config = getattr(check, '_config', None)
    if config is None:
        return None

    try:
        return RemoteQueryTarget(host=config.host, port=config.port, dbname=config.dbname)
    except (AttributeError, ValidationError):
        return None


def _dbname_from_check(check: 'PostgreSql') -> str | None:
    config = getattr(check, '_config', None)
    return getattr(config, 'dbname', None)


def _started_metadata(request: RemoteQueryCopyRequest) -> dict[str, Any]:
    result_delivery = request.result_delivery
    max_bytes = result_delivery.max_bytes if result_delivery is not None else request.limits.max_bytes
    metadata: dict[str, Any] = {
        'status': 'STARTED',
        'format': request.format,
        'operation': request.operation,
        'chunkBytes': request.limits.chunk_bytes,
        'maxBytes': max_bytes,
        'maxRowBytes': request.limits.max_row_bytes,
    }
    if result_delivery is not None:
        metadata['resultDelivery'] = {
            'mode': result_delivery.mode,
            'uploadId': result_delivery.upload_id,
            'partBytes': result_delivery.part_bytes,
            'maxBytes': result_delivery.max_bytes,
            'format': result_delivery.format,
            'compression': result_delivery.compression,
        }
    return metadata


def _succeeded_metadata(state: _CopyStreamState, started_at: float, request: RemoteQueryCopyRequest) -> dict[str, Any]:
    metadata: dict[str, Any] = {'status': 'SUCCEEDED', 'stats': _copy_stream_stats(state, started_at, request.format)}
    result_delivery = request.result_delivery
    if result_delivery is not None:
        # Provisional receipt aligned to the Agent-owned uploadReceipt shape
        # {mode, uploadId, bucketName, objectPath, totalBytes, totalRows, partCount, sha256}.
        # Python owns only the fields it can compute from the byte stream; the Agent Go side
        # enriches it with bucketName, objectPath, totalRows, and the aggregate sha256 after
        # it finalizes the upload session.
        metadata['uploadReceipt'] = {
            'mode': result_delivery.mode,
            'uploadId': result_delivery.upload_id,
            'totalBytes': state.bytes_emitted,
            'partCount': _multipart_part_count(state.bytes_emitted, result_delivery.part_bytes),
        }
    return metadata


def _iter_copy_stream_events(
    check: 'PostgreSql', request: RemoteQueryCopyRequest, execution_dbname: str, started_at: float
) -> Iterator[CopyStreamEvent]:
    db_pool = getattr(check, 'db_pool', None)
    if db_pool is None:
        yield _stream_failed_event(
            'credentials_unavailable',
            'Matched Postgres check does not expose a connection pool.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return
    if getattr(db_pool, 'is_closed', lambda: False)():
        yield _stream_failed_event(
            'target_unavailable',
            'Matched Postgres check connection pool is closed.',
            retryable=False,
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    yield CopyStreamEvent('metadata', _started_metadata(request))

    state = _CopyStreamState()
    error: _CopyStreamFailure | None = None
    try:
        for event, next_state in _copy_stream_data_events(check, request, execution_dbname, state, started_at):
            state = next_state
            yield event
    except _CopyStreamFailure as e:
        error = e
    except RuntimeError:
        error = _CopyStreamFailure(
            'target_unavailable', 'Matched Postgres check connection pool is unavailable.', retryable=False
        )
    except Exception:
        LOGGER.exception('Remote query COPY stream execution failed')
        error = _CopyStreamFailure('query_failed', 'Remote query COPY stream execution failed.')

    if error is not None:
        yield _stream_failed_event(
            error.code,
            error.message,
            retryable=error.retryable,
            stats=_copy_stream_stats(state, started_at, request.format),
        )
        return

    yield CopyStreamEvent('final', _succeeded_metadata(state, started_at, request))


def _copy_stream_data_events(
    check: 'PostgreSql',
    request: RemoteQueryCopyRequest,
    execution_dbname: str,
    state: _CopyStreamState,
    started_at: float,
) -> Iterator[tuple[CopyStreamEvent, _CopyStreamState]]:
    limits = request.limits
    result_delivery = request.result_delivery
    chunk_bytes = limits.chunk_bytes
    max_bytes = result_delivery.max_bytes if result_delivery is not None else limits.max_bytes
    max_row_bytes = limits.max_row_bytes
    timeout_ms = limits.timeout_ms
    deadline = started_at + (timeout_ms / 1000)
    copy_sql = _copy_stdout_sql(request.query, request.format)
    pending = bytearray()

    with check.db_pool.get_connection(execution_dbname) as conn:
        with conn.cursor() as cursor:
            in_transaction = False
            try:
                cursor.execute('BEGIN READ ONLY')
                in_transaction = True
                cursor.execute('SET LOCAL statement_timeout = %s', (timeout_ms,))
                with cursor.copy(copy_sql) as copy:
                    for block in copy:
                        _raise_if_timed_out(deadline)
                        block_view = memoryview(block)
                        if len(block_view) > max_row_bytes:
                            raise _CopyStreamFailure(
                                'max_row_bytes_exceeded',
                                'COPY stream row exceeded maxRowBytes; psycopg exposes COPY data at row granularity.',
                            )

                        offset = 0
                        while offset < len(block_view):
                            _raise_if_timed_out(deadline)
                            remaining_allowed = max_bytes - state.bytes_emitted - len(pending)
                            if remaining_allowed <= 0:
                                raise _CopyStreamFailure('max_bytes_exceeded', 'COPY stream exceeded maxBytes.')

                            remaining_chunk = chunk_bytes - len(pending)
                            take = min(remaining_chunk, remaining_allowed, len(block_view) - offset)
                            pending.extend(block_view[offset : offset + take])
                            offset += take

                            if len(pending) >= chunk_bytes:
                                event, state = _copy_data_event(pending, state, result_delivery)
                                pending.clear()
                                yield event, state

                            if offset < len(block_view) and state.bytes_emitted + len(pending) >= max_bytes:
                                if pending:
                                    event, state = _copy_data_event(pending, state, result_delivery)
                                    pending.clear()
                                    yield event, state
                                raise _CopyStreamFailure('max_bytes_exceeded', 'COPY stream exceeded maxBytes.')

                    if pending:
                        event, state = _copy_data_event(pending, state, result_delivery)
                        pending.clear()
                        yield event, state
            finally:
                if in_transaction:
                    try:
                        cursor.execute('ROLLBACK')
                    except Exception:
                        LOGGER.debug('Unable to roll back remote query read-only transaction', exc_info=True)


def _copy_stdout_sql(query: str, stream_format: CopyStreamFormat) -> str:
    if stream_format == 'csv':
        return f'COPY ({query}) TO STDOUT WITH (FORMAT CSV)'
    if stream_format == 'binary':
        return f'COPY ({query}) TO STDOUT WITH (FORMAT BINARY)'
    raise _CopyStreamFailure('invalid_request', 'Unsupported COPY stream format.')


def _is_query_allowed(query: str) -> bool:
    return not _is_query_allowlist_enabled() or query in REMOTE_QUERY_COPY_SQL_ALLOWLIST


def _is_query_allowlist_enabled() -> bool:
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


def _raise_if_timed_out(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise _CopyStreamFailure('timeout', 'COPY stream exceeded timeoutMs.', retryable=True)


def _copy_data_event(
    data: bytearray, state: _CopyStreamState, result_delivery: RemoteQueryResultDelivery | None = None
) -> tuple[CopyStreamEvent, _CopyStreamState]:
    payload = bytes(data)
    metadata: dict[str, Any] = {
        'sequence': state.sequence,
        'offset': state.bytes_emitted,
        'bytes': len(payload),
    }
    if result_delivery is not None:
        metadata['sha256'] = hashlib.sha256(payload).hexdigest()
    event = CopyStreamEvent('data', metadata, payload)
    next_state = _CopyStreamState(
        sequence=state.sequence + 1,
        chunks_emitted=state.chunks_emitted + 1,
        bytes_emitted=state.bytes_emitted + len(payload),
    )
    return event, next_state


def _copy_stream_stats(state: _CopyStreamState, started_at: float, stream_format: CopyStreamFormat) -> dict[str, Any]:
    return {
        'format': stream_format,
        'bytesEmitted': state.bytes_emitted,
        'chunksEmitted': state.chunks_emitted,
        'elapsedMs': _elapsed_ms(started_at),
    }


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def _stream_failed_event(
    code: str,
    message: str,
    retryable: bool = False,
    stats: Mapping[str, Any] | None = None,
    elapsed_ms: int | None = None,
) -> CopyStreamEvent:
    metadata = {
        'status': 'FAILED',
        'error': {'code': code, 'message': message, 'retryable': retryable},
    }
    if stats is not None:
        metadata['stats'] = dict(stats)
    elif elapsed_ms is not None:
        metadata['stats'] = {'elapsedMs': elapsed_ms}
    return CopyStreamEvent('error', metadata)


def _emit_copy_event(emit: CopyStreamEmit, event: CopyStreamEvent) -> None:
    emit(event.event_type, json.dumps(event.metadata, default=str), event.payload)


def _validation_message(error: ValidationError) -> str:
    details = []
    for item in error.errors(include_input=False):
        location = _validation_location(item.get('loc', ()))
        message = item.get('msg', 'Invalid value')
        if location:
            details.append(f'{location}: {message}')
        else:
            details.append(message)
    return 'Invalid remote query request: {}'.format('; '.join(details))


def _validation_location(location: tuple[Any, ...]) -> str:
    return '.'.join(str(part) for part in location)


# ---------------------------------------------------------------------------
# Direct multipart upload to its-agent-intake (POC_PUBLIC_MULTIPART_UPLOAD)
#
# When resultDelivery is present, the integration uploads bounded COPY parts
# directly to its-agent-intake over HTTP. The Agent forwards the intake base
# URL and scoped upload token in resultDelivery, and the integration reads the
# org API key and POC application key from Agent config via datadog_agent.get_config.
# Bulk part bytes never traverse the native emit bridge, AgentSecure, PAR, or
# AP action output; only the compact final receipt is emitted back.

REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER = 'test-drive-its-agent-intake-poc'
REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY = 'remote_queries.execute.intake_test_drive_selector'
REMOTE_QUERY_UPLOAD_MAX_RETRIES = 4
REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS = 0.1
REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS = 5.0
# Per-upload HTTP timeout as an explicit (connect, read) tuple: a short connect timeout and a
# 5-minute read timeout so a slow part upload (e.g. a large part over a constrained link) is
# not cut short, while a stuck connect fails fast. Retry count and backoff stay bounded above.
REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS = 10
REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS = 300
REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT = (
    REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS,
    REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class _UploadCredentials:
    base_url: str
    upload_id: str
    api_key: str
    app_key: str
    token: str
    test_drive_selector: str | None


class _UploadClient(Protocol):
    def put_part(
        self, creds: _UploadCredentials, part_number: int, payload: bytes, sha256_hex: str, rows: int
    ) -> None: ...

    def finalize(self, creds: _UploadCredentials) -> Mapping[str, Any]: ...

    def abort(self, creds: _UploadCredentials) -> None: ...


class _RequestsUploadClient:
    """HTTP upload client for its-agent-intake. Imports requests lazily."""

    def __init__(self, timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT) -> None:
        self._timeout = timeout

    def _headers(self, creds: _UploadCredentials, content_type: str | None = None) -> dict[str, str]:
        headers = {
            'dd-api-key': creds.api_key,
            'dd-application-key': creds.app_key,
            'Authorization': 'Bearer ' + creds.token,
        }
        if content_type is not None:
            headers['Content-Type'] = content_type
        if creds.test_drive_selector:
            headers[REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER] = creds.test_drive_selector
        return headers

    def put_part(self, creds: _UploadCredentials, part_number: int, payload: bytes, sha256_hex: str, rows: int) -> None:
        headers = self._headers(creds, 'application/octet-stream')
        headers['X-DD-Part-SHA256'] = sha256_hex
        headers['X-DD-Part-Bytes'] = str(len(payload))
        headers['X-DD-Part-Rows'] = str(rows)
        url = '{}/uploads/{}/parts/{}'.format(creds.base_url.rstrip('/'), creds.upload_id, part_number)
        _upload_with_retry('PUT', url, headers, payload, self._timeout)

    def finalize(self, creds: _UploadCredentials) -> Mapping[str, Any]:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id)
        _status, body = _upload_with_retry('POST', url, headers, b'{}', self._timeout)
        return json.loads(body.decode('utf-8'))

    def abort(self, creds: _UploadCredentials) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/abort'.format(creds.base_url.rstrip('/'), creds.upload_id)
        try:
            _upload_with_retry('POST', url, headers, b'{}', self._timeout)
        except _CopyStreamFailure:
            LOGGER.debug('Remote query upload abort failed (best-effort)', exc_info=True)


def _is_transient_upload_status(status: int) -> bool:
    return status == 408 or status == 429 or status >= 500


def _upload_with_retry(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT,
) -> tuple[int, bytes]:
    import requests  # lazy: only the POC upload path needs it

    backoff = REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS
    last_err: Any = None
    for attempt in range(REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, headers=dict(headers), data=body, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_err = e
        else:
            if 200 <= resp.status_code < 300:
                return resp.status_code, resp.content
            if not _is_transient_upload_status(resp.status_code):
                raise _CopyStreamFailure(
                    'upload_failed', 'upload to its-agent-intake rejected with status {}'.format(resp.status_code)
                )
            last_err = 'status {}'.format(resp.status_code)
        if attempt == REMOTE_QUERY_UPLOAD_MAX_RETRIES:
            break
        time.sleep(backoff)
        backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)
    raise _CopyStreamFailure(
        'upload_failed',
        'upload to its-agent-intake failed after {} attempts: {}'.format(REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, last_err),
        retryable=True,
    )


def _is_upload_request(request: Mapping[str, Any]) -> bool:
    delivery = request.get('resultDelivery')
    return isinstance(delivery, Mapping) and delivery.get('mode') == 'POC_PUBLIC_MULTIPART_UPLOAD'


def _get_agent_config(key: str) -> str:
    try:
        value = datadog_agent.get_config(key)
    except Exception:
        LOGGER.debug('Unable to read agent config %s', key, exc_info=True)
        return ''
    if value is None:
        return ''
    return str(value)


def _resolve_upload_credentials(request: Mapping[str, Any]) -> _UploadCredentials:
    delivery = request.get('resultDelivery') or {}
    selector = _get_agent_config(REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY)
    return _UploadCredentials(
        base_url=str(delivery.get('baseUrl') or ''),
        upload_id=str(delivery.get('uploadId') or ''),
        api_key=_get_agent_config('api_key'),
        app_key=_get_agent_config('app_key'),
        token=str(delivery.get('token') or ''),
        test_drive_selector=selector or None,
    )


def _default_upload_client() -> _UploadClient:
    return _RequestsUploadClient()


def _count_newlines(payload: bytes) -> int:
    return payload.count(b'\n')


def _multipart_part_count(total_bytes: int, part_bytes: int) -> int:
    # Number of multipart parts for ``total_bytes`` aggregated at ``part_bytes``: full parts of
    # exactly partBytes plus a final short part, or zero parts for an empty result.
    if total_bytes <= 0:
        return 0
    return (total_bytes + part_bytes - 1) // part_bytes


def _intake_receipt_to_camel(resp: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'mode': resp.get('mode', 'POC_PUBLIC_MULTIPART_UPLOAD'),
        'uploadId': resp.get('upload_id', ''),
        'bucketName': resp.get('bucket_name', ''),
        'objectPath': resp.get('object_key', ''),
        'totalBytes': resp.get('total_bytes', 0),
        'totalRows': resp.get('total_rows', 0),
        'partCount': resp.get('part_count', 0),
        'sha256': resp.get('sha256', ''),
    }


def _safe_abort(client: _UploadClient, creds: _UploadCredentials) -> None:
    if not creds.base_url or not creds.upload_id or not creds.token:
        return
    try:
        client.abort(creds)
    except Exception:
        LOGGER.debug('Remote query upload abort failed (best-effort)', exc_info=True)


@dataclass(frozen=True)
class _MultipartPart:
    part_number: int
    payload: bytes


class _MultipartBuffer:
    """Aggregate COPY chunk bytes into server-clamped multipart parts.

    The COPY stream emits ``limits.chunkBytes``-sized chunks; this buffer accumulates them into
    ``partBytes``-sized parts (the multipart part size), which may exceed the COPY chunk size.
    At most one part is buffered at a time. Part numbers are contiguous and 1-based to match
    provider multipart conventions.
    """

    def __init__(self, part_bytes: int) -> None:
        self._part_bytes = part_bytes
        self._pending = bytearray()
        self._next_part_number = 1

    def extend(self, data: bytes) -> None:
        self._pending.extend(data)

    def _take(self) -> _MultipartPart:
        payload = bytes(self._pending[: self._part_bytes])
        del self._pending[: self._part_bytes]
        part = _MultipartPart(self._next_part_number, payload)
        self._next_part_number += 1
        return part

    def full_parts(self) -> Iterator[_MultipartPart]:
        while len(self._pending) >= self._part_bytes:
            yield self._take()

    def flush_final(self) -> _MultipartPart | None:
        if not self._pending:
            return None
        return self._take()


def _upload_one_part(client: _UploadClient, creds: _UploadCredentials, part: _MultipartPart) -> None:
    # The part SHA-256 is over the aggregated part body (all chunks combined), not the
    # individual COPY chunks, so the intake can verify the part it receives.
    client.put_part(
        creds, part.part_number, part.payload, hashlib.sha256(part.payload).hexdigest(), _count_newlines(part.payload)
    )


def _finalize_upload(
    client: _UploadClient, creds: _UploadCredentials, event: CopyStreamEvent, emit: CopyStreamEmit
) -> None:
    receipt = _intake_receipt_to_camel(client.finalize(creds))
    metadata = dict(event.metadata)
    # The iterator's provisional receipt uses the camelCase key; replace it with the
    # server-expected snake_case outer key carrying the Agent-shaped camelCase receipt.
    metadata.pop('uploadReceipt', None)
    metadata['upload_receipt'] = receipt
    _emit_copy_event(emit, CopyStreamEvent('final', metadata))


def _execute_upload_stream(
    request: Mapping[str, Any],
    check: 'PostgreSql',
    emit: CopyStreamEmit,
    http_client: _UploadClient | None = None,
) -> None:
    """Upload COPY parts directly to its-agent-intake; emit only metadata/final/error events."""
    creds = _resolve_upload_credentials(request)
    if not creds.api_key or not creds.app_key:
        _emit_copy_event(
            emit,
            _stream_failed_event(
                'credentials_unavailable',
                'Remote query upload requires api_key and app_key to be configured on the Agent.',
            ),
        )
        return
    client = http_client if http_client is not None else _default_upload_client()
    events = iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check]))
    buffer: _MultipartBuffer | None = None
    try:
        for event in events:
            if event.event_type == 'metadata':
                # The STARTED metadata carries the backend-validated partBytes; the COPY stream
                # emits chunkBytes-sized events that this client aggregates into partBytes parts.
                delivery_meta = event.metadata.get('resultDelivery') or {}
                buffer = _MultipartBuffer(int(delivery_meta.get('partBytes') or 0))
                _emit_copy_event(emit, event)
            elif event.event_type == 'data':
                if buffer is not None:
                    buffer.extend(event.payload)
                    for part in buffer.full_parts():
                        _upload_one_part(client, creds, part)
            elif event.event_type == 'final':
                if buffer is not None:
                    final_part = buffer.flush_final()
                    if final_part is not None:
                        _upload_one_part(client, creds, final_part)
                _finalize_upload(client, creds, event, emit)
            elif event.event_type == 'error':
                _safe_abort(client, creds)
                _emit_copy_event(emit, event)
            else:
                _emit_copy_event(emit, event)
    except _CopyStreamFailure as e:
        _safe_abort(client, creds)
        _emit_copy_event(emit, _stream_failed_event(e.code, e.message, retryable=e.retryable))
        events.close()
    except BaseException:
        _safe_abort(client, creds)
        events.close()
        raise
