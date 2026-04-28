# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

LOGGER = logging.getLogger(__name__)

_ALLOWED_QUERY = 'SELECT 1 AS value'
_REQUEST_FIELDS = frozenset({'target', 'query', 'limits'})
_TARGET_FIELDS = frozenset({'host', 'port', 'dbname'})
_LIMIT_FIELDS = frozenset({'maxRows', 'maxBytes', 'timeoutMs'})


@dataclass(frozen=True)
class RemoteQueryTarget:
    host: str
    port: int
    dbname: str


@dataclass(frozen=True)
class RemoteQueryLimits:
    max_rows: int = 10
    max_bytes: int = 1_048_576
    timeout_ms: int = 5_000


@dataclass(frozen=True)
class RemoteQueryRequest:
    target: RemoteQueryTarget
    limits: RemoteQueryLimits


@dataclass(frozen=True)
class StaticPostgresCheckRegistry:
    checks: Sequence['PostgreSql']

    def iter_postgres_checks(self) -> Iterable['PostgreSql']:
        return iter(self.checks)


class PostgresCheckRegistry(Protocol):
    def iter_postgres_checks(self) -> Iterable['PostgreSql']: ...


def execute_remote_query(request: Mapping[str, Any], registry: PostgresCheckRegistry) -> dict[str, Any]:
    request_or_error = _parse_request(request)
    if isinstance(request_or_error, dict):
        return request_or_error

    parsed_request = request_or_error
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
    host = target.get('host')
    if not isinstance(host, str) or not host.strip():
        raise ValueError('host must be a non-empty string')

    dbname = target.get('dbname')
    if not isinstance(dbname, str) or not dbname:
        raise ValueError('dbname must be a non-empty string')
    if dbname != dbname.strip():
        raise ValueError('dbname must not contain surrounding whitespace')

    return RemoteQueryTarget(
        host=_normalize_host(host), port=_int_in_range(target.get('port', 5432), 'port', maximum=65535), dbname=dbname
    )


def _parse_request(value: Any) -> RemoteQueryRequest | dict[str, Any]:
    if not isinstance(value, Mapping):
        return _error('invalid_request', 'Remote query request must be a mapping.')

    unknown_fields_error = _unknown_fields_error(value, _REQUEST_FIELDS, 'request')
    if unknown_fields_error is not None:
        return unknown_fields_error

    target_or_error = _parse_target(value.get('target'))
    if isinstance(target_or_error, dict):
        return target_or_error

    if not _is_allowed_query(value.get('query')):
        return _error('query_rejected', 'Only the canonical SELECT 1 proof query is allowed.')

    limits_or_error = _parse_limits(value.get('limits', {}))
    if isinstance(limits_or_error, dict):
        return limits_or_error

    return RemoteQueryRequest(target=target_or_error, limits=limits_or_error)


def _parse_target(value: Any) -> RemoteQueryTarget | dict[str, Any]:
    if not isinstance(value, Mapping):
        return _error('invalid_selector', 'Target selector must be a mapping.')

    unknown_fields_error = _unknown_fields_error(value, _TARGET_FIELDS, 'target')
    if unknown_fields_error is not None:
        return unknown_fields_error

    try:
        return normalize_target(value)
    except ValueError as e:
        return _error('invalid_selector', str(e))


def _parse_limits(value: Any) -> RemoteQueryLimits | dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        return _error('invalid_request', 'Limits must be a mapping.')

    unknown_fields_error = _unknown_fields_error(value, _LIMIT_FIELDS, 'limits')
    if unknown_fields_error is not None:
        return unknown_fields_error

    try:
        return RemoteQueryLimits(
            max_rows=_int_in_range(value.get('maxRows', 10), 'maxRows'),
            max_bytes=_int_in_range(value.get('maxBytes', 1_048_576), 'maxBytes'),
            timeout_ms=_int_in_range(value.get('timeoutMs', 5_000), 'timeoutMs'),
        )
    except ValueError as e:
        return _error('invalid_request', str(e))


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
                columns = [_column_name(column) for column in cursor.description]
                raw_rows = cursor.fetchmany(limits.max_rows + 1)
    except RuntimeError:
        return _error('target_unavailable', 'Matched Postgres check connection pool is unavailable.', retryable=False)
    except Exception:
        LOGGER.exception('Remote query execution failed')
        return _error('query_failed', 'Remote query execution failed.')

    truncated = len(raw_rows) > limits.max_rows
    rows = [_row_to_dict(columns, row) for row in raw_rows[: limits.max_rows]]
    response_columns = [{'name': name, 'type': _infer_type(rows, name)} for name in columns]
    bytes_returned = len(json.dumps({'columns': response_columns, 'rows': rows}, default=str).encode('utf-8'))

    return {
        'status': 'SUCCEEDED',
        'columns': response_columns,
        'rows': rows,
        'truncated': truncated,
        'stats': {'rowCount': len(rows), 'bytesReturned': bytes_returned},
    }


def _unknown_fields_error(
    value: Mapping[str, Any], allowed_fields: frozenset[str], label: str
) -> dict[str, Any] | None:
    unknown_fields = _unknown_field_names(value, allowed_fields)
    if unknown_fields:
        return _error('invalid_request', _unknown_fields_message(unknown_fields, label))
    return None


def _unknown_field_names(value: Mapping[str, Any], allowed_fields: frozenset[str]) -> list[str]:
    return sorted(str(field) for field in value if field not in allowed_fields)


def _unknown_fields_message(unknown_fields: list[str], label: str) -> str:
    field_label = 'field' if len(unknown_fields) == 1 else 'fields'
    return f"{label} contains unknown {field_label}: {', '.join(unknown_fields)}"


def _is_allowed_query(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().rstrip(';').strip() == _ALLOWED_QUERY


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


def _column_name(column: Any) -> str:
    name = getattr(column, 'name', None)
    if name is not None:
        return str(name)
    return str(column[0])


def _row_to_dict(columns: list[str], row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return {column: row[column] for column in columns}
    return dict(zip(columns, row))


def _infer_type(rows: list[dict[str, Any]], column: str) -> str:
    for row in rows:
        value = row.get(column)
        if isinstance(value, bool):
            return 'boolean'
        if isinstance(value, int):
            return 'integer'
        if isinstance(value, float):
            return 'number'
        if value is not None:
            return 'string'
    return 'unknown'


def _error(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {'status': 'FAILED', 'error': {'code': code, 'message': message, 'retryable': retryable}}
