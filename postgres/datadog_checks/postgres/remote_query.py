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

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

LOGGER = logging.getLogger(__name__)

_ALLOWED_QUERY = 'SELECT 1 AS value'


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
    model_config = ConfigDict(extra='forbid', frozen=True)

    max_rows: StrictInt = Field(default=10, alias='maxRows', ge=1)
    max_bytes: StrictInt = Field(default=1_048_576, alias='maxBytes', ge=1)
    timeout_ms: StrictInt = Field(default=5_000, alias='timeoutMs', ge=1)


class RemoteQueryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    target: RemoteQueryTarget
    query: Literal['SELECT 1 AS value']
    limits: RemoteQueryLimits = Field(default_factory=RemoteQueryLimits)


@dataclass(frozen=True)
class StaticPostgresCheckRegistry:
    checks: Sequence['PostgreSql']

    def iter_postgres_checks(self) -> Iterable['PostgreSql']:
        return iter(self.checks)


class PostgresCheckRegistry(Protocol):
    def iter_postgres_checks(self) -> Iterable['PostgreSql']: ...


def execute_remote_query(request: Any, registry: PostgresCheckRegistry) -> dict[str, Any]:
    try:
        parsed_request = RemoteQueryRequest.model_validate(request)
    except ValidationError as e:
        return _validation_error(e)

    target = parsed_request.target
    limits = parsed_request.limits

    matches = _resolve_matches(target, registry.iter_postgres_checks())
    LOGGER.debug('Remote query target match count: %d', len(matches))
    if not matches:
        return _error('target_not_found', 'No loaded Postgres integration instance matched target selector.')
    if len(matches) > 1:
        return _error('target_ambiguous', 'More than one loaded Postgres integration instance matched target selector.')

    return _execute_select_1(matches[0], target, limits)


def normalize_target(target: Mapping[str, Any]) -> RemoteQueryTarget:
    try:
        return RemoteQueryTarget.model_validate(target)
    except ValidationError as e:
        raise ValueError(_validation_message(e)) from e


def _resolve_matches(target: RemoteQueryTarget, checks: Iterable['PostgreSql']) -> list['PostgreSql']:
    matches = []
    for check in checks:
        config = getattr(check, '_config', None)
        if config is None:
            continue
        try:
            candidate = RemoteQueryTarget(
                host=_normalize_host(config.host),
                port=_int_in_range(config.port, 'port', maximum=65535),
                dbname=config.dbname,
            )
        except (AttributeError, ValueError):
            continue
        if candidate == target:
            matches.append(check)
    return matches


def _execute_select_1(check: 'PostgreSql', target: RemoteQueryTarget, limits: RemoteQueryLimits) -> dict[str, Any]:
    db_pool = getattr(check, 'db_pool', None)
    if db_pool is None:
        return _error('credentials_unavailable', 'Matched Postgres check does not expose a connection pool.')
    if getattr(db_pool, 'is_closed', lambda: False)():
        return _error('target_unavailable', 'Matched Postgres check connection pool is closed.', retryable=False)

    try:
        with db_pool.get_connection(target.dbname) as conn:
            with conn.cursor() as cursor:
                cursor.execute(_ALLOWED_QUERY)
                if cursor.description is None:
                    return _error('query_failed', 'Query did not return a result set.')
                raw_rows = cursor.fetchmany(limits.max_rows + 1)
    except RuntimeError:
        return _error('target_unavailable', 'Matched Postgres check connection pool is unavailable.', retryable=False)
    except Exception:
        LOGGER.exception('Remote query execution failed')
        return _error('query_failed', 'Remote query execution failed.')

    truncated = len(raw_rows) > limits.max_rows
    rows = [{'value': row[0]} for row in raw_rows[: limits.max_rows]]
    response_columns = [{'name': 'value', 'type': 'integer'}]
    bytes_returned = len(json.dumps({'columns': response_columns, 'rows': rows}, default=str).encode('utf-8'))

    return {
        'status': 'SUCCEEDED',
        'columns': response_columns,
        'rows': rows,
        'truncated': truncated,
        'stats': {'rowCount': len(rows), 'bytesReturned': bytes_returned},
    }


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


def _normalize_host(value: str) -> str:
    host = value.strip().lower()
    if host.endswith('.'):
        host = host[:-1]
    if not host:
        raise ValueError('host must be a non-empty string')
    return host


def _int_in_range(value: Any, field: str, *, minimum: int = 1, maximum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f'{field} must be an integer')
    if value < minimum or (maximum is not None and value > maximum):
        if maximum is None:
            raise ValueError(f'{field} must be greater than or equal to {minimum}')
        raise ValueError(f'{field} must be between {minimum} and {maximum}')
    return value


def _error(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {'status': 'FAILED', 'error': {'code': code, 'message': message, 'retryable': retryable}}
