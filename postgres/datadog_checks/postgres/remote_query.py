# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, ValidationError, field_validator

RemoteQuerySql = Literal[
    'SELECT 1 AS value',
    'SELECT city, country FROM cities ORDER BY city',
    "SELECT repeat('x', 1048576) AS payload",
    "SELECT repeat('x', 2097152) AS payload",
    "SELECT repeat('x', 4194304) AS payload",
    "SELECT repeat('x', 8388608) AS payload",
    "SELECT repeat('x', 16777216) AS payload",
    "SELECT repeat('x', 33554432) AS payload",
]

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

LOGGER = logging.getLogger(__name__)


class RemoteQueryTarget(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    host: StrictStr = Field(min_length=1)
    port: StrictInt = Field(default=5432, ge=1, le=65535)
    dbname: StrictStr = Field(min_length=1)

    @field_validator('host')
    @classmethod
    def normalize_host(cls, value: str) -> str:
        host = value.strip().lower()
        if host.endswith('.'):
            host = host[:-1]
        if not host:
            raise ValueError('host must be a non-empty string')
        return host

    @field_validator('dbname')
    @classmethod
    def validate_dbname(cls, value: str) -> str:
        if not value:
            raise ValueError('dbname must be a non-empty string')
        if value != value.strip():
            raise ValueError('dbname must not contain surrounding whitespace')
        return value


class RemoteQueryLimits(BaseModel):
    """Validate the future-facing limits contract for the initial safe query slice."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    max_rows: StrictInt = Field(default=10, alias='maxRows', ge=1)
    max_bytes: StrictInt = Field(default=1_048_576, alias='maxBytes', ge=1)
    timeout_ms: StrictInt = Field(default=5_000, alias='timeoutMs', ge=1)


class RemoteQueryRequest(BaseModel):
    """Accept only exact proof queries until broader SQL execution is implemented."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    target: RemoteQueryTarget
    query: RemoteQuerySql
    limits: RemoteQueryLimits = Field(default_factory=RemoteQueryLimits)


@dataclass(frozen=True)
class StaticPostgresCheckRegistry:
    checks: Sequence['PostgreSql']

    def iter_postgres_checks(self) -> Iterable['PostgreSql']:
        return iter(self.checks)


class PostgresCheckRegistry(Protocol):
    def iter_postgres_checks(self) -> Iterable['PostgreSql']: ...


def execute_agent_rpc_json(request_json: str | bytes | bytearray, check: 'PostgreSql') -> str:
    try:
        request = json.loads(request_json)
    except (TypeError, ValueError):
        response = _error('invalid_request', 'Invalid remote query request: request_json must be a valid JSON object.')
    else:
        if not isinstance(request, Mapping):
            response = _error('invalid_request', 'Invalid remote query request: request_json must be a JSON object.')
        else:
            response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    return json.dumps(response, default=str)


def execute_remote_query(request: Any, registry: PostgresCheckRegistry) -> dict[str, Any]:
    try:
        parsed_request = RemoteQueryRequest.model_validate(request)
    except ValidationError as e:
        return _validation_error(e)

    target = parsed_request.target
    limits = parsed_request.limits
    query = parsed_request.query

    matches = _resolve_matches(target, registry.iter_postgres_checks())
    LOGGER.debug('Remote query target match count: %d', len(matches))
    if not matches:
        return _error('target_not_found', 'No loaded Postgres integration instance matched target selector.')
    if len(matches) > 1:
        return _error('target_ambiguous', 'More than one loaded Postgres integration instance matched target selector.')

    return _execute_safe_query(matches[0], target, query, limits)


def normalize_target(target: Mapping[str, Any]) -> RemoteQueryTarget:
    try:
        return RemoteQueryTarget.model_validate(target)
    except ValidationError as e:
        raise ValueError(_validation_message(e)) from e


def _resolve_matches(target: RemoteQueryTarget, checks: Iterable['PostgreSql']) -> list['PostgreSql']:
    return [check for check in checks if _target_from_check(check) == target]


def _target_from_check(check: 'PostgreSql') -> RemoteQueryTarget | None:
    config = getattr(check, '_config', None)
    if config is None:
        return None

    try:
        return RemoteQueryTarget(host=config.host, port=config.port, dbname=config.dbname)
    except (AttributeError, ValidationError):
        return None


def _execute_safe_query(
    check: 'PostgreSql', target: RemoteQueryTarget, query: RemoteQuerySql, limits: RemoteQueryLimits
) -> dict[str, Any]:
    db_pool = getattr(check, 'db_pool', None)
    if db_pool is None:
        return _error('credentials_unavailable', 'Matched Postgres check does not expose a connection pool.')
    if getattr(db_pool, 'is_closed', lambda: False)():
        return _error('target_unavailable', 'Matched Postgres check connection pool is closed.', retryable=False)

    try:
        with db_pool.get_connection(target.dbname) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                description = cursor.description
                if description is None:
                    return _error('query_failed', 'Query did not return a result set.')
                raw_rows = cursor.fetchmany(limits.max_rows + 1)
    except RuntimeError:
        return _error('target_unavailable', 'Matched Postgres check connection pool is unavailable.', retryable=False)
    except Exception:
        LOGGER.exception('Remote query execution failed')
        return _error('query_failed', 'Remote query execution failed.')

    # max_bytes and timeout_ms are validated for the API contract but enforced in a follow-up slice.
    truncated = len(raw_rows) > limits.max_rows
    response_columns = _response_columns(description, raw_rows)
    rows = [_response_row(response_columns, row) for row in raw_rows[: limits.max_rows]]
    bytes_returned = len(json.dumps({'columns': response_columns, 'rows': rows}, default=str).encode('utf-8'))

    return {
        'status': 'SUCCEEDED',
        'columns': response_columns,
        'rows': rows,
        'truncated': truncated,
        'stats': {'rowCount': len(rows), 'bytesReturned': bytes_returned},
    }


def _response_columns(description: Sequence[Any], rows: Sequence[Sequence[Any]]) -> list[dict[str, str]]:
    return [
        {'name': _column_name(column), 'type': _column_type(index, rows)} for index, column in enumerate(description)
    ]


def _column_name(column: Any) -> str:
    name = getattr(column, 'name', None)
    if name is not None:
        return str(name)
    return str(column[0])


def _column_type(index: int, rows: Sequence[Sequence[Any]]) -> str:
    for row in rows:
        if row[index] is not None:
            return _value_type(row[index])
    return 'unknown'


def _value_type(value: Any) -> str:
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, int):
        return 'integer'
    if isinstance(value, float):
        return 'number'
    if isinstance(value, str):
        return 'string'
    return type(value).__name__


def _response_row(columns: Sequence[Mapping[str, str]], row: Sequence[Any]) -> dict[str, Any]:
    return {column['name']: row[index] for index, column in enumerate(columns)}


def _validation_error(error: ValidationError) -> dict[str, Any]:
    return _error('invalid_request', _validation_message(error))


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


def _error(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {'status': 'FAILED', 'error': {'code': code, 'message': message, 'retryable': retryable}}
