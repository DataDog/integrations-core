# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Remote query JSON page producer for the Postgres integration.

Executes one validated query through a named (server-side) cursor, normalizes PostgreSQL
values into the pinned cross-language JSON contract, splits the rows into byte-bounded JSON
page files, and uploads each complete page to its-agent-intake as one direct HTTP request.
The shared page writer retains one bounded page in memory through byte-identical retries.
Bulk page bytes never traverse the native emit bridge, AgentSecure, PAR, or AP
action output; the emit callback carries only ``metadata``/``final``/``error`` events, and
the final event carries only the compact run receipt.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from datetime import time as dt_time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Protocol

import psycopg.errors as psycopg_errors
import psycopg.types.json as psycopg_json
from psycopg.types.string import TextLoader
from pydantic import ValidationError

from datadog_checks.base.utils import remote_queries as rq

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

LOGGER = logging.getLogger(__name__)

REMOTE_QUERY_QUERY_ALLOWLIST = frozenset(
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
        'SELECT i, repeat(\'x\', 1000) AS payload FROM generate_series(1, 3000) AS i',
    )
)

# Rows fetched per bounded batch from the server-side cursor. A producer detail, not a
# server-owned limit.
REMOTE_QUERY_FETCH_BATCH_ROWS = 500


@dataclass(frozen=True)
class ResultColumn:
    """One described result field: its column name, type OID, and type modifier."""

    name: str
    type_oid: int
    type_modifier: int | None


@dataclass(frozen=True)
class StaticPostgresCheckRegistry:
    checks: Sequence['PostgreSql']

    def iter_postgres_checks(self) -> Iterable['PostgreSql']:
        return iter(self.checks)


class PostgresCheckRegistry(Protocol):
    def iter_postgres_checks(self) -> Iterable['PostgreSql']: ...


# ---------------------------------------------------------------------------
# PostgreSQL value contract (pinned, cross-language)
#
#   PostgreSQL family        JSON representation
#   NULL                    null
#   boolean                 JSON boolean
#   integral numerics       JSON number with the exact database text
#   finite numeric/float4/8  JSON number with the exact database text
#   non-finite numerics     string: "NaN", "Infinity", or "-Infinity"
#   text/enum/UUID/inet     JSON string (inet/cidr keep their exact server text)
#   date/time/timestamp     documented ISO-8601 strings; timestamptz in UTC with a "Z" suffix
#   interval                documented PostgreSQL interval string (exact server text)
#   json / jsonb            nested JSON value (arbitrary-precision numbers preserved)
#   arrays                  JSON array with recursive element conversion
#   bytea                   base64 string (schema identifies bytea)
#   ranges/extensions       documented string form (unknown types arrive as their text)
#
# Fail closed on anything that cannot be converted deliberately: never silently stringify
# via a driver default.


class RawJsonNumber(str):
    """A PostgreSQL numeric whose exact server text is emitted as a JSON number token.

    Subclasses ``str`` so any generic serialization path still yields the value as a string
    rather than corrupting it; the page encoder recognizes the type and emits the text
    verbatim (rejecting the non-finite spellings, which must be JSON strings).
    """


class RawJsonNumberLoader(TextLoader):
    """Load float4/float8 as their exact server text instead of a parsed float.

    PostgreSQL float output is already a shortest-roundtrip decimal text, so keeping it raw
    preserves the exact database representation without any float round-trip.
    """

    def load(self, data: Any) -> Any:
        value = super().load(data)
        if not isinstance(value, str):
            # SQL_ASCII databases yield bytes from the text loader; numeric text is ASCII.
            value = bytes(value).decode('utf-8')
        return RawJsonNumber(value)


class RawTextLoader(TextLoader):
    """Load interval/inet/cidr/ranges as their exact server text (the documented string forms).

    psycopg's object loaders are lossy or non-contractual for these families: interval would
    collapse into a timedelta (losing year/month components), inet would grow a
    psycopg-added prefix length, and ranges would become psycopg Range objects instead of
    the documented string form. The contract keeps the server's own string spelling.
    """

    def load(self, data: Any) -> Any:
        value = super().load(data)
        if not isinstance(value, str):
            value = bytes(value).decode('utf-8')
        return value


def _json_loads_exact(data: Any) -> Any:
    # parse_float=Decimal keeps arbitrary-precision numbers inside json/jsonb as their exact
    # text instead of rounding through a float.
    return json.loads(data, parse_float=Decimal)


class ExactJsonLoader(psycopg_json.JsonLoader):
    _loads = staticmethod(_json_loads_exact)


class ExactJsonbLoader(psycopg_json.JsonbLoader):
    _loads = staticmethod(_json_loads_exact)


# Range and multirange type names known to psycopg's builtin registry; older psycopg or
# PostgreSQL builds may not know every one, and missing names are simply skipped.
RANGE_TYPE_NAMES = (
    'int4range',
    'int8range',
    'numrange',
    'daterange',
    'tsrange',
    'tstzrange',
    'int4multirange',
    'int8multirange',
    'nummultirange',
    'datemultirange',
    'tsmultirange',
    'tstzmultirange',
)


def register_exact_loaders(cursor: Any) -> None:
    """Register cursor-scoped loaders that keep exact server text for lossy families.

    Registration is scoped to the named query cursor only, so the shared pooled connection's
    behavior for the rest of the check is untouched. Arrays of these types load their
    elements through the same cursor adapters, so array elements keep exact text too.
    """
    adapters = cursor.adapters
    adapters.register_loader('float4', RawJsonNumberLoader)
    adapters.register_loader('float8', RawJsonNumberLoader)
    adapters.register_loader('interval', RawTextLoader)
    adapters.register_loader('inet', RawTextLoader)
    adapters.register_loader('cidr', RawTextLoader)
    for range_type_name in RANGE_TYPE_NAMES:
        try:
            adapters.register_loader(range_type_name, RawTextLoader)
        except KeyError:
            LOGGER.debug('psycopg type registry does not know %s', range_type_name)
    adapters.register_loader('json', ExactJsonLoader)
    adapters.register_loader('jsonb', ExactJsonbLoader)


BYTEA_OID = 17

# A JSON number per RFC 8259: no leading zeros, optional fraction and exponent. Server
# numeric text must already satisfy this; anything else fails closed.


def _encode_datetime_text(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat()
    # Timestamptz is canonicalized to UTC so the page does not depend on the session
    # TimeZone, and the zero offset is spelled "Z" per the v1 contract example.
    utc_value = value.astimezone(timezone.utc)
    text = utc_value.isoformat()
    if text.endswith('+00:00'):
        text = text[:-6] + 'Z'
    return text


def _encode_bytea(out: bytearray, value: bytes) -> None:
    out += b'"'
    out += base64.b64encode(value)
    out += b'"'


def _encode_json_value(out: bytearray, value: Any, *, top_type_oid: int | None, in_array: bool) -> None:
    """Encode one normalized PostgreSQL value into ``out`` as JSON bytes.

    ``top_type_oid`` is the described column OID for row fields (used to accept bytea
    precisely); inside arrays and json values binary buffers can only come from bytea, so
    ``in_array`` licenses them there. Everything unrecognized fails closed.
    """
    if value is None:
        out += b'null'
    elif isinstance(value, bool):
        out += b'true' if value else b'false'
    elif isinstance(value, RawJsonNumber):
        text = str(value)
        if text in rq.NON_FINITE_NUMERIC_TEXT:
            rq.encode_non_finite_text(out, text)
        else:
            rq.encode_raw_number_text(out, text)
    elif isinstance(value, int):
        rq.encode_raw_number_text(out, str(value))
    elif isinstance(value, Decimal):
        rq.encode_decimal(out, value)
    elif isinstance(value, float):
        rq.encode_float(out, value)
    elif isinstance(value, str):
        out += json.dumps(value).encode('utf-8')
    elif isinstance(value, (bytes, bytearray, memoryview)):
        if top_type_oid == BYTEA_OID or in_array:
            _encode_bytea(out, bytes(value))
        else:
            raise rq.RemoteQueryFailure(
                'unsupported_value',
                'Binary value from a non-bytea column (type oid {}) cannot be converted.'.format(top_type_oid),
            )
    elif isinstance(value, datetime):
        out += json.dumps(_encode_datetime_text(value)).encode('utf-8')
    elif isinstance(value, date):
        out += json.dumps(value.isoformat()).encode('utf-8')
    elif isinstance(value, dt_time):
        out += json.dumps(value.isoformat()).encode('utf-8')
    elif isinstance(value, uuid.UUID):
        out += json.dumps(str(value)).encode('utf-8')
    elif isinstance(value, (list, tuple)):
        out += b'['
        for index, item in enumerate(value):
            if index:
                out += b','
            _encode_json_value(out, item, top_type_oid=None, in_array=True)
        out += b']'
    elif isinstance(value, dict):
        out += b'{'
        first = True
        for key, item in value.items():
            if not isinstance(key, str):
                raise rq.RemoteQueryFailure('unsupported_value', 'JSON object keys must be strings.')
            if not first:
                out += b','
            first = False
            out += json.dumps(key).encode('utf-8')
            out += b':'
            _encode_json_value(out, item, top_type_oid=None, in_array=True)
        out += b'}'
    else:
        raise rq.RemoteQueryFailure(
            'unsupported_value',
            'PostgreSQL value of type {} has no conversion in the JSON contract.'.format(type(value).__name__),
        )


def encode_row(row: Sequence[Any], columns: Sequence[ResultColumn], out: bytearray) -> None:
    """Encode one result row as a JSON object keyed by result-column name."""
    if len(row) != len(columns):
        raise rq.RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
    out += b'{'
    for index, (column, value) in enumerate(zip(columns, row)):
        if index:
            out += b','
        out += json.dumps(column.name).encode('utf-8')
        out += b':'
        _encode_json_value(out, value, top_type_oid=column.type_oid, in_array=False)
    out += b'}'


# ---------------------------------------------------------------------------
# Result description and schema
# ---------------------------------------------------------------------------

VENDOR_TYPE_QUERY = (
    'SELECT t.type_oid::oid, t.type_mod::int4, '
    'pg_catalog.format_type(t.type_oid::oid, t.type_mod::int4) AS vendor_data_type '
    'FROM unnest(%s::text[], %s::text[]) AS t(type_oid, type_mod)'
)


def described_columns(cursor: Any) -> list[ResultColumn]:
    """Read the ordered result column names, type OIDs, and type modifiers.

    A named cursor's description is available immediately after the DECLARE, including for
    zero-row results, so a schema-bearing empty page can still be produced. psycopg keeps
    the raw RowDescription type modifier on the ``Column`` object (``_fmod``); it is the
    exact value ``pg_catalog.format_type`` expects.
    """
    description = getattr(cursor, 'description', None)
    if not description:
        raise rq.RemoteQueryFailure('query_failed', 'Query returned no result description.')

    columns = []
    for described in description:
        name = described.name
        if not isinstance(name, str) or not name:
            raise rq.RemoteQueryFailure('schema_unavailable', 'Result description carried an empty column name.')
        type_oid = described.type_code
        if not isinstance(type_oid, int):
            raise rq.RemoteQueryFailure('schema_unavailable', 'Result description carried a non-integer type oid.')
        columns.append(ResultColumn(name=name, type_oid=type_oid, type_modifier=getattr(described, '_fmod', None)))
    return columns


def validate_columns(columns: Sequence[ResultColumn], max_columns: int) -> None:
    if len(columns) > max_columns:
        raise rq.RemoteQueryFailure(
            'max_columns_exceeded',
            'Query described {} result columns; the limit is {}.'.format(len(columns), max_columns),
        )
    seen = set()
    for column in columns:
        if column.name in seen:
            raise rq.RemoteQueryFailure(
                'duplicate_columns',
                'Duplicate result-column name {!r} cannot key a JSON row object.'.format(column.name),
            )
        seen.add(column.name)


def resolve_vendor_types(control_cursor: Any, columns: Sequence[ResultColumn]) -> dict[tuple[int, int], str]:
    """Resolve every DISTINCT (type_oid, type_modifier) pair with one parameterized lookup.

    The catalog query runs in the same read-only transaction and statement timeout scope as
    the user query. Types are passed as text arrays and cast element-wise (text -> oid and
    text -> int4 both cast via I/O), which is version-stable and avoids psycopg's
    element-width-dependent int array dump OIDs.
    """
    distinct_pairs = sorted({(column.type_oid, column.type_modifier) for column in columns})
    if any(pair[1] is None for pair in distinct_pairs):
        raise rq.RemoteQueryFailure(
            'schema_unavailable', 'Result description did not expose type modifiers for every column.'
        )

    oids = [str(pair[0]) for pair in distinct_pairs]
    type_modifiers = [str(pair[1]) for pair in distinct_pairs]
    control_cursor.execute(VENDOR_TYPE_QUERY, (oids, type_modifiers))
    rows = control_cursor.fetchall()

    type_map: dict[tuple[int, int], str] = {}
    for row in rows:
        oid, type_modifier, vendor_data_type = row[0], row[1], row[2]
        if not isinstance(vendor_data_type, str) or not vendor_data_type:
            raise rq.RemoteQueryFailure('schema_unavailable', 'pg_catalog.format_type returned an unusable type name.')
        type_map[(oid, type_modifier)] = vendor_data_type

    missing = [pair for pair in distinct_pairs if pair not in type_map]
    if missing:
        raise rq.RemoteQueryFailure(
            'schema_unavailable',
            'pg_catalog.format_type lookup did not resolve {} requested type(s).'.format(len(missing)),
        )
    return type_map


def build_schema_json(
    control_cursor: Any,
    columns: Sequence[ResultColumn],
    delivery: rq.RemoteQueryResultDelivery,
    agent_hostname: str,
) -> bytes:
    """Build the ordered schema entries, rejecting incomplete metadata and oversize schemas.

    The encoded schema repeats in every page, so it must fit both ``maxSchemaBytes`` and the
    smallest valid page frame; both are enforced before any row data is written.
    """
    type_map = resolve_vendor_types(control_cursor, columns)
    entries = [
        {'column_name': column.name, 'vendor_data_type': type_map[(column.type_oid, column.type_modifier)]}
        for column in columns
    ]
    schema_json = json.dumps(entries, separators=(',', ':')).encode('utf-8')
    limits = delivery.limits
    if len(schema_json) > limits.max_schema_bytes:
        raise rq.RemoteQueryFailure(
            'max_schema_bytes_exceeded',
            'Encoded schema is {} bytes; the limit is {}.'.format(len(schema_json), limits.max_schema_bytes),
        )
    prefix_len = len(
        rq.page_prefix(
            run_id=delivery.run_id,
            task_id=delivery.task_id,
            record_offset=0,
            agent_hostname=agent_hostname,
            schema_json=schema_json,
        )
    )
    if prefix_len + len(rq.PAGE_SUFFIX) > limits.max_file_bytes:
        raise rq.RemoteQueryFailure(
            'max_file_bytes_exceeded',
            'The repeated schema plus the minimal page envelope exceeds maxFileBytes.',
        )
    return schema_json


# ---------------------------------------------------------------------------
# Producer: one validated query execution through a named server-side cursor
# ---------------------------------------------------------------------------


def produce_remote_query(
    request: rq.RemoteQueryRequest,
    check: 'PostgreSql',
    creds: rq.UploadCredentials,
    client: rq.UploadClient,
    execution_dbname: str,
    started_at: float,
    stats: rq.RemoteQueryRunStats,
) -> dict[str, Any]:
    """Execute the validated query once and return the compact run receipt.

    The query runs exactly once, through a named server-side cursor declared inside the
    existing read-only transaction with the effective statement timeout applied — the
    smaller of the instance-configured ``remote_queries.timeout_ms`` and the remaining
    run-wide wall, where the wall is the delivered ``limits.timeout_ms`` that no instance
    setting may lengthen; it is never wrapped in a probe and never executed twice. Bounded
    row batches are fetched from the same cursor and encoded one row at a time.
    """
    delivery = request.result_delivery
    limits = delivery.limits
    # The delivered timeout is the run-wide monotonic hard wall; the instance-configured
    # remote_queries.timeout_ms may shorten the statement timeout below it but never
    # replace or lengthen the wall.
    deadline = started_at + limits.timeout_ms / 1000
    statement_timeout_ms = _resolve_statement_timeout_ms(check, deadline)
    # Keep a batch of permitted-size rows within a page-sized encoded budget.
    # Driver allocations still need headroom; row size is checked after decoding.
    fetch_rows = max(1, min(REMOTE_QUERY_FETCH_BATCH_ROWS, limits.max_file_bytes // limits.max_row_bytes))

    def guard() -> None:
        rq.raise_if_timed_out(deadline)
        rq.raise_if_cancelled(check)

    cursor_name = 'remote_query_{}'.format(uuid.uuid4().hex)
    with check.db_pool.get_connection(execution_dbname) as conn:
        with conn.cursor() as control:
            in_transaction = False
            try:
                control.execute('BEGIN READ ONLY')
                in_transaction = True
                # SET statements do not accept bind parameters, so the timeout is inlined; it
                # is a validated positive int resolved from the instance override and the
                # remaining wall, never raw text.
                control.execute('SET LOCAL statement_timeout = {}'.format(statement_timeout_ms))
                with conn.cursor(name=cursor_name) as server_cursor:
                    register_exact_loaders(server_cursor)
                    server_cursor.execute(request.query)
                    columns = described_columns(server_cursor)
                    validate_columns(columns, limits.max_columns)
                    schema_json = None
                    if request.include_schema:
                        schema_json = build_schema_json(control, columns, delivery, check.hostname)

                    # The executing check's Agent-reported hostname: the stamp must match the
                    # agent node identity Fleet reports, never socket.gethostname().
                    writer = rq.PageWriter(delivery, creds, client, check.hostname, schema_json, guard, stats)
                    guard()
                    try:
                        while True:
                            rows = server_cursor.fetchmany(fetch_rows)
                            if not rows:
                                break
                            for row in rows:
                                guard()
                                row_buffer = bytearray()
                                encode_row(row, columns, row_buffer)
                                if len(row_buffer) > limits.max_row_bytes:
                                    raise rq.RemoteQueryFailure(
                                        'row_too_large',
                                        'A single row exceeds maxRowBytes ({} > {} bytes).'.format(
                                            len(row_buffer), limits.max_row_bytes
                                        ),
                                    )
                                writer.add_row(bytes(row_buffer))
                        return writer.finish()
                    finally:
                        # Release the page even if encoding or cursor iteration fails.
                        writer.discard()
            finally:
                if in_transaction:
                    try:
                        control.execute('ROLLBACK')
                    except Exception:
                        LOGGER.debug('Unable to roll back remote query read-only transaction', exc_info=True)


def _resolve_statement_timeout_ms(check: 'PostgreSql', deadline: float) -> int:
    """Resolve the statement timeout that protects the customer database for this run.

    ``deadline`` is the run-wide hard wall derived from the delivered ``limits.timeout_ms``:
    it covers target resolution, query execution, page construction, upload, and retries,
    and instance configuration can never lengthen it. The instance config
    ``remote_queries.timeout_ms`` stays a customer-database protection with per-instance
    granularity (a warehouse instance can allow minutes while an OLTP instance allows
    seconds), but it may only shorten the run: the effective statement timeout is the smaller
    of the positive instance value and the remaining wall, and the wall's remainder applies
    when the instance does not configure one. The value is resolved locally per run; the
    delivery limits object is never mutated.
    """
    config = getattr(check, '_config', None)
    instance_timeout_ms = getattr(getattr(config, 'remote_queries', None), 'timeout_ms', None)
    remaining_ms = rq.remaining_wall_ms(deadline)
    if isinstance(instance_timeout_ms, int) and instance_timeout_ms > 0:
        return min(instance_timeout_ms, remaining_ms)
    return remaining_ms


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def _resolve_matches(target: rq.RemoteQueryTarget, checks: Iterable['PostgreSql']) -> list['PostgreSql']:
    """Resolve the loaded checks a target selects, fail-closed: zero, one, or many matches.

    A database_instance selector matches one loaded check by its rendered identifier. A tuple
    selector matches only a check whose normalized configured endpoint equals the request and
    whose effective monitoring scope includes the requested database.
    """
    if target.database_instance is not None:
        return [check for check in checks if getattr(check, 'database_identifier', None) == target.database_instance]
    return [check for check in checks if _target_matches_scope(check, target)]


def _target_matches_scope(check: 'PostgreSql', target: rq.RemoteQueryTarget) -> bool:
    """A tuple target matches only inside one check's effective monitoring scope.

    The requested dbname is part of match identity, never an execution parameter resolved after
    selection: a different database on the same reachable server is not a match, and neither an
    out-of-scope database nor a nonexistent one is probed to distinguish them.
    """
    return _endpoint_from_check(check) == (target.host, target.port) and database_in_monitoring_scope(
        check, target.dbname
    )


def _endpoint_from_check(check: 'PostgreSql') -> tuple[str, int] | None:
    """The check's endpoint identity: normalized configured host and effective port.

    A check whose configuration does not expose a usable endpoint (missing config, non-string
    host, non-integer port) has no endpoint identity and matches no tuple target.
    """
    config = getattr(check, '_config', None)
    host = getattr(config, 'host', None)
    port = getattr(config, 'port', None)
    if not isinstance(host, str) or not isinstance(port, int) or isinstance(port, bool):
        return None
    try:
        return rq.normalize_host(host), port
    except ValueError:
        return None


def _dbname_from_check(check: 'PostgreSql') -> str | None:
    config = getattr(check, '_config', None)
    return getattr(config, 'dbname', None)


def database_in_monitoring_scope(check: 'PostgreSql', dbname: str) -> bool:
    """Answer whether one database lies inside a loaded check's effective monitoring scope.

    Single integration-owned source of truth for Remote Query database targeting, consumed by
    target matching and execution alike. The scope is the check's materialized ``config.dbname``
    — an explicit ``dbname``, else the ``postgres`` default, else
    ``database_autodiscovery.global_view_db``, exactly as the integration's own ``build_config``
    materialized it — plus, when database autodiscovery is enabled, the current database set
    admitted by the check's own autodiscovery implementation with its existing include/exclude
    filters, refresh cycle, and ``max_databases`` bound. Defaulting and filtering stay
    integration-owned: this helper never reimplements them and never probes the requested
    database, so a database that exists but is out of scope and a database that does not exist
    are indistinguishable by design.

    Raises RemoteQueryFailure(target_unavailable, retryable) when the admitted discovery set
    cannot be determined: an unknown scope fails closed and visible, never as a silent
    no-match.
    """
    configured_dbname = _dbname_from_check(check)
    if configured_dbname is not None and dbname == configured_dbname:
        return True
    autodiscovery = getattr(check, 'autodiscovery', None)
    if autodiscovery is None:
        return False
    try:
        return dbname in autodiscovery.get_items()
    except Exception as e:
        raise rq.RemoteQueryFailure(
            'target_unavailable',
            "Unable to determine the matched check's autodiscovered database scope: {}".format(e),
            retryable=True,
        ) from e


# ---------------------------------------------------------------------------
# Query allowlist
# ---------------------------------------------------------------------------


def _is_query_allowed(query: str) -> bool:
    return not rq.is_query_allowlist_enabled() or query in REMOTE_QUERY_QUERY_ALLOWLIST


# ---------------------------------------------------------------------------
# Event entry points
# ---------------------------------------------------------------------------


def execute_agent_rpc_stream_copy(
    request_json: str | bytes | bytearray, check: 'PostgreSql', emit: rq.RemoteQueryEmit
) -> None:
    """Execute a remote query request and emit page producer events.

    The entry point name is kept for the Agent's rtloader bridge, which resolves this
    function by name. Emits ``metadata`` (STARTED), then one ``final`` (SUCCEEDED with the
    compact receipt) or ``error`` (FAILED) event; bulk page bytes never cross the callback.
    """
    try:
        request = json.loads(request_json)
    except (TypeError, ValueError):
        rq.emit_event(
            emit,
            rq.failed_event(
                'invalid_request', 'Invalid remote query request: request_json must be a valid JSON object.'
            ),
        )
        return

    if not isinstance(request, Mapping):
        rq.emit_event(
            emit,
            rq.failed_event('invalid_request', 'Invalid remote query request: request_json must be a JSON object.'),
        )
        return

    _execute_upload_stream(request, check, emit)


def _execute_upload_stream(
    request: Mapping[str, Any],
    check: 'PostgreSql',
    emit: rq.RemoteQueryEmit,
    http_client: rq.UploadClient | None = None,
) -> None:
    """Drive the producer with the default (or injected) upload client and emit its events."""
    events = iter_agent_rpc_stream_events(request, StaticPostgresCheckRegistry([check]), http_client)
    try:
        for event in events:
            rq.emit_event(emit, event)
    except BaseException:
        events.close()
        raise


def iter_agent_rpc_stream_events(
    request: Any, registry: PostgresCheckRegistry, http_client: rq.UploadClient | None = None
) -> Iterator[rq.RemoteQueryEvent]:
    """Yield producer events for unit tests and callback adaptation."""
    started_at = time.monotonic()
    try:
        parsed_request = rq.RemoteQueryRequest.model_validate(request)
    except ValidationError as e:
        yield rq.failed_event('invalid_request', rq.validation_message(e), elapsed_ms=rq.elapsed_ms(started_at))
        return

    if not _is_query_allowed(parsed_request.query):
        yield rq.failed_event(
            'invalid_request',
            'Invalid remote query request: query is not allowlisted.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    target = parsed_request.target
    try:
        matches = _resolve_matches(target, registry.iter_postgres_checks())
    except rq.RemoteQueryFailure as e:
        yield rq.failed_event(e.code, e.message, retryable=e.retryable, elapsed_ms=rq.elapsed_ms(started_at))
        return
    LOGGER.debug('Remote query target match count: %d', len(matches))
    if not matches:
        yield rq.failed_event(
            'target_not_found',
            'No loaded Postgres integration instance matched target selector.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return
    if len(matches) > 1:
        yield rq.failed_event(
            'target_ambiguous',
            'More than one loaded Postgres integration instance matched target selector.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    check = matches[0]
    if target.database_instance is not None:
        # A database_instance selector identifies one loaded check; execution runs on that
        # check's materialized configured database, never a request-named other database.
        execution_dbname = _dbname_from_check(check)
        if execution_dbname is None:
            yield rq.failed_event(
                'target_unavailable',
                'Matched Postgres check does not expose a configured database name.',
                elapsed_ms=rq.elapsed_ms(started_at),
            )
            return
    else:
        # A tuple target's dbname is part of match identity: it matched the selected check's
        # effective monitoring scope, and execution runs exactly on that database.
        execution_dbname = target.dbname

    creds = rq.resolve_upload_credentials(parsed_request.result_delivery, started_at)
    if not creds.api_key or not creds.app_key:
        yield rq.failed_event(
            'credentials_unavailable',
            'Remote query upload requires api_key and app_key to be configured on the Agent.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    db_pool = getattr(check, 'db_pool', None)
    if db_pool is None:
        yield rq.failed_event(
            'credentials_unavailable',
            'Matched Postgres check does not expose a connection pool.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return
    if getattr(db_pool, 'is_closed', lambda: False)():
        yield rq.failed_event(
            'target_unavailable',
            'Matched Postgres check connection pool is closed.',
            retryable=False,
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    client = http_client if http_client is not None else rq.RequestsUploadClient()
    stats = rq.RemoteQueryRunStats()
    yield rq.RemoteQueryEvent('metadata', rq.started_metadata(parsed_request))

    try:
        receipt = produce_remote_query(parsed_request, check, creds, client, execution_dbname, started_at, stats)
    except rq.RemoteQueryFailure as e:
        rq.safe_abort(client, creds)
        yield rq.failed_event(e.code, e.message, retryable=e.retryable, stats=rq.stats_metadata(stats, started_at))
        return
    except psycopg_errors.QueryCanceled:
        # SQLSTATE class 57014: the server canceled the statement (statement timeout or an
        # explicit cancel); both are retryable query timeouts for the run.
        rq.safe_abort(client, creds)
        yield rq.failed_event(
            'timeout',
            'Remote query was canceled by the server (statement timeout or cancellation).',
            retryable=True,
            stats=rq.stats_metadata(stats, started_at),
        )
        return
    except RuntimeError:
        rq.safe_abort(client, creds)
        yield rq.failed_event(
            'target_unavailable',
            'Matched Postgres check connection pool is unavailable.',
            retryable=False,
            stats=rq.stats_metadata(stats, started_at),
        )
        return
    except BaseException as e:
        rq.safe_abort(client, creds)
        if not isinstance(e, Exception):
            raise
        LOGGER.exception('Remote query execution failed')
        yield rq.failed_event(
            'query_failed', 'Remote query execution failed.', stats=rq.stats_metadata(stats, started_at)
        )
        return

    yield rq.RemoteQueryEvent('final', rq.succeeded_metadata(receipt, stats, started_at))
