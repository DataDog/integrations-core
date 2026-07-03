# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

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

CopyStreamFormat = Literal['csv', 'binary']
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


class RemoteQueryCopyRequest(BaseModel):
    """Accept only explicit COPY byte-stream export requests."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['copy_stream'] = Field(alias='operation')
    target: RemoteQueryTarget
    query: StrictStr = Field(min_length=1)
    format: CopyStreamFormat = 'csv'
    limits: RemoteQueryCopyLimits = Field(default_factory=RemoteQueryCopyLimits)


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

    yield CopyStreamEvent(
        'metadata',
        {
            'status': 'STARTED',
            'format': request.format,
            'operation': request.operation,
            'chunkBytes': request.limits.chunk_bytes,
            'maxBytes': request.limits.max_bytes,
            'maxRowBytes': request.limits.max_row_bytes,
        },
    )

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

    yield CopyStreamEvent(
        'final',
        {'status': 'SUCCEEDED', 'stats': _copy_stream_stats(state, started_at, request.format)},
    )


def _copy_stream_data_events(
    check: 'PostgreSql',
    request: RemoteQueryCopyRequest,
    execution_dbname: str,
    state: _CopyStreamState,
    started_at: float,
) -> Iterator[tuple[CopyStreamEvent, _CopyStreamState]]:
    limits = request.limits
    deadline = started_at + (limits.timeout_ms / 1000)
    copy_sql = _copy_stdout_sql(request.query, request.format)
    pending = bytearray()

    with check.db_pool.get_connection(execution_dbname) as conn:
        with conn.cursor() as cursor:
            in_transaction = False
            try:
                cursor.execute('BEGIN READ ONLY')
                in_transaction = True
                cursor.execute('SET LOCAL statement_timeout = %s', (limits.timeout_ms,))
                with cursor.copy(copy_sql) as copy:
                    for block in copy:
                        _raise_if_timed_out(deadline)
                        block_view = memoryview(block)
                        if len(block_view) > limits.max_row_bytes:
                            raise _CopyStreamFailure(
                                'max_row_bytes_exceeded',
                                'COPY stream row exceeded maxRowBytes; psycopg exposes COPY data at row granularity.',
                            )

                        offset = 0
                        while offset < len(block_view):
                            _raise_if_timed_out(deadline)
                            remaining_allowed = limits.max_bytes - state.bytes_emitted - len(pending)
                            if remaining_allowed <= 0:
                                raise _CopyStreamFailure('max_bytes_exceeded', 'COPY stream exceeded maxBytes.')

                            remaining_chunk = limits.chunk_bytes - len(pending)
                            take = min(remaining_chunk, remaining_allowed, len(block_view) - offset)
                            pending.extend(block_view[offset : offset + take])
                            offset += take

                            if len(pending) >= limits.chunk_bytes:
                                event, state = _copy_data_event(pending, state)
                                pending.clear()
                                yield event, state

                            if offset < len(block_view) and state.bytes_emitted + len(pending) >= limits.max_bytes:
                                if pending:
                                    event, state = _copy_data_event(pending, state)
                                    pending.clear()
                                    yield event, state
                                raise _CopyStreamFailure('max_bytes_exceeded', 'COPY stream exceeded maxBytes.')

                    if pending:
                        event, state = _copy_data_event(pending, state)
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


def _copy_data_event(data: bytearray, state: _CopyStreamState) -> tuple[CopyStreamEvent, _CopyStreamState]:
    payload = bytes(data)
    event = CopyStreamEvent(
        'data',
        {
            'sequence': state.sequence,
            'offset': state.bytes_emitted,
            'bytes': len(payload),
        },
        payload,
    )
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
