# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Remote query JSON page producer for the Postgres integration.

Executes one validated query through a named (server-side) cursor, normalizes PostgreSQL
values into the pinned cross-language JSON contract, splits the rows into byte-bounded JSON
page files, and streams each page's bytes as multipart parts directly to its-agent-intake
over HTTP. Bulk page bytes never traverse the native emit bridge, AgentSecure, PAR, or AP
action output; the emit callback carries only ``metadata``/``final``/``error`` events, and
the final event carries only the compact run receipt.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import re
import time
import uuid
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from datetime import time as dt_time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, Protocol

import psycopg.errors as psycopg_errors
import psycopg.types.json as psycopg_json
from psycopg.types.string import TextLoader
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

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

LOGGER = logging.getLogger(__name__)

REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY = 'remote_queries.execute.enable_query_allowlist'
REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES = frozenset(('false', 'no', '0', 'n', 'off'))
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

# Server-owned maximums. The backend selects/clamps every injected limit; the integration only
# fails closed when an injected instruction exceeds a known platform ceiling, which would
# indicate a backend/integration contract version mismatch.
REMOTE_QUERY_UPLOAD_MAX_PART_BYTES = 128 * 1024 * 1024
REMOTE_QUERY_UPLOAD_MAX_FILE_BYTES = 128 * 1024 * 1024
REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES = 10 * 1024 * 1024 * 1024
REMOTE_QUERY_DEFAULT_TIMEOUT_MS = 30_000
# Rows fetched per bounded batch from the server-side cursor. A producer detail, not a
# server-owned limit.
REMOTE_QUERY_FETCH_BATCH_ROWS = 500

# Page artifact contract (version 1). One complete UTF-8 JSON document per page:
#
#   {"version":1,"run_id":"...","task_id":"...","batch_index":0,"record_offset":0,
#    "schema":[{"column_name":"...","vendor_data_type":"..."}],
#    "data":{"items":[{...row...},...]}}
#
# ``schema`` repeats identically in every page when includeSchema is enabled and is omitted
# entirely (never ``null``/``[]``) when disabled. There is no ``total_records`` field.
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

        host_fields = self.model_fields_set & {'host', 'port', 'dbname'}
        if self.database_instance is not None:
            if host_fields:
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
    max_pages: StrictInt = Field(alias='maxPages', ge=1)
    timeout_ms: StrictInt = Field(default=REMOTE_QUERY_DEFAULT_TIMEOUT_MS, alias='timeoutMs', ge=1)

    @model_validator(mode='after')
    def validate_limit_relations(self) -> 'RemoteQueryUploadLimits':
        if self.max_row_bytes > self.max_file_bytes:
            raise ValueError('maxRowBytes must not exceed maxFileBytes: a row must fit inside one page')
        if self.max_file_bytes > self.max_result_bytes:
            raise ValueError('maxFileBytes must not exceed maxResultBytes')
        return self


class RemoteQueryResultDelivery(BaseModel):
    """Backend-injected upload instructions and artifact contract metadata.

    The Agent forwards the run-scoped intake session instructions (``uploadId``, ``baseUrl``,
    ``token``, ``partBytes``), the effective server-owned limits, the artifact contract
    version, and the authoritative run/task identity used in every page envelope. Every field
    is server-owned: the integration validates what it receives and never invents values.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    run_id: StrictStr = Field(alias='runId', min_length=1)
    task_id: StrictStr = Field(alias='taskId', min_length=1)
    artifact_version: Literal[REMOTE_QUERY_ARTIFACT_VERSION] = Field(alias='artifactVersion')
    upload_id: StrictStr = Field(alias='uploadId', min_length=1)
    base_url: StrictStr = Field(alias='baseUrl', min_length=1)
    token: StrictStr = Field(alias='token', min_length=1)
    part_bytes: StrictInt = Field(alias='partBytes', ge=1, le=REMOTE_QUERY_UPLOAD_MAX_PART_BYTES)
    limits: RemoteQueryUploadLimits

    @model_validator(mode='after')
    def validate_part_within_page(self) -> 'RemoteQueryResultDelivery':
        # Parts are fragments of a page, so the injected part size must not exceed the page cap.
        if self.part_bytes > self.limits.max_file_bytes:
            raise ValueError('partBytes must not exceed limits.maxFileBytes')
        return self


class RemoteQueryRequest(BaseModel):
    """A single remote query execution producing bounded JSON result pages."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['produce_json_pages'] = Field(alias='operation')
    target: RemoteQueryTarget
    query: StrictStr = Field(min_length=1)
    include_schema: StrictBool = Field(default=False, alias='includeSchema')
    result_delivery: RemoteQueryResultDelivery = Field(alias='resultDelivery')


@dataclass(frozen=True)
class ResultColumn:
    """One described result field: its column name, type OID, and type modifier."""

    name: str
    type_oid: int
    type_modifier: int | None


@dataclass
class RemoteQueryRunStats:
    """Mutable run accounting shared with the page writer so failures can report partials."""

    rows_emitted: int = 0
    pages_emitted: int = 0
    parts_emitted: int = 0
    bytes_emitted: int = 0


@dataclass(frozen=True)
class StaticPostgresCheckRegistry:
    checks: Sequence['PostgreSql']

    def iter_postgres_checks(self) -> Iterable['PostgreSql']:
        return iter(self.checks)


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
_JSON_NUMBER_PATTERN = re.compile(r'\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\Z')
_NON_FINITE_NUMERIC_TEXT = frozenset(('NaN', 'Infinity', '-Infinity'))


def _encode_non_finite_text(out: bytearray, text: str) -> None:
    out += json.dumps(text).encode('utf-8')


def _encode_raw_number_text(out: bytearray, text: str) -> None:
    if not _JSON_NUMBER_PATTERN.match(text):
        raise RemoteQueryFailure(
            'unsupported_value', 'PostgreSQL sent numeric text {!r} that is not a JSON number.'.format(text)
        )
    out += text.encode('utf-8')


def _encode_decimal(out: bytearray, value: Decimal) -> None:
    if value.is_finite():
        _encode_raw_number_text(out, str(value))
        return
    if value.is_nan():
        _encode_non_finite_text(out, 'NaN')
    elif value > 0:
        _encode_non_finite_text(out, 'Infinity')
    else:
        _encode_non_finite_text(out, '-Infinity')


def _encode_float(out: bytearray, value: float) -> None:
    if math.isfinite(value):
        # Python repr is the shortest string that round-trips the float.
        _encode_raw_number_text(out, repr(value))
    elif math.isnan(value):
        _encode_non_finite_text(out, 'NaN')
    elif value > 0:
        _encode_non_finite_text(out, 'Infinity')
    else:
        _encode_non_finite_text(out, '-Infinity')


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
        if text in _NON_FINITE_NUMERIC_TEXT:
            _encode_non_finite_text(out, text)
        else:
            _encode_raw_number_text(out, text)
    elif isinstance(value, int):
        _encode_raw_number_text(out, str(value))
    elif isinstance(value, Decimal):
        _encode_decimal(out, value)
    elif isinstance(value, float):
        _encode_float(out, value)
    elif isinstance(value, str):
        out += json.dumps(value).encode('utf-8')
    elif isinstance(value, (bytes, bytearray, memoryview)):
        if top_type_oid == BYTEA_OID or in_array:
            _encode_bytea(out, bytes(value))
        else:
            raise RemoteQueryFailure(
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
                raise RemoteQueryFailure('unsupported_value', 'JSON object keys must be strings.')
            if not first:
                out += b','
            first = False
            out += json.dumps(key).encode('utf-8')
            out += b':'
            _encode_json_value(out, item, top_type_oid=None, in_array=True)
        out += b'}'
    else:
        raise RemoteQueryFailure(
            'unsupported_value',
            'PostgreSQL value of type {} has no conversion in the JSON contract.'.format(type(value).__name__),
        )


def encode_row(row: Sequence[Any], columns: Sequence[ResultColumn], out: bytearray) -> None:
    """Encode one result row as a JSON object keyed by result-column name."""
    if len(row) != len(columns):
        raise RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
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
        raise RemoteQueryFailure('query_failed', 'Query returned no result description.')

    columns = []
    for described in description:
        name = described.name
        if not isinstance(name, str) or not name:
            raise RemoteQueryFailure('schema_unavailable', 'Result description carried an empty column name.')
        type_oid = described.type_code
        if not isinstance(type_oid, int):
            raise RemoteQueryFailure('schema_unavailable', 'Result description carried a non-integer type oid.')
        columns.append(ResultColumn(name=name, type_oid=type_oid, type_modifier=getattr(described, '_fmod', None)))
    return columns


def validate_columns(columns: Sequence[ResultColumn], max_columns: int) -> None:
    if len(columns) > max_columns:
        raise RemoteQueryFailure(
            'max_columns_exceeded',
            'Query described {} result columns; the limit is {}.'.format(len(columns), max_columns),
        )
    seen = set()
    for column in columns:
        if column.name in seen:
            raise RemoteQueryFailure(
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
        raise RemoteQueryFailure(
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
            raise RemoteQueryFailure('schema_unavailable', 'pg_catalog.format_type returned an unusable type name.')
        type_map[(oid, type_modifier)] = vendor_data_type

    missing = [pair for pair in distinct_pairs if pair not in type_map]
    if missing:
        raise RemoteQueryFailure(
            'schema_unavailable',
            'pg_catalog.format_type lookup did not resolve {} requested type(s).'.format(len(missing)),
        )
    return type_map


def build_schema_json(
    control_cursor: Any, columns: Sequence[ResultColumn], delivery: RemoteQueryResultDelivery
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
        raise RemoteQueryFailure(
            'max_schema_bytes_exceeded',
            'Encoded schema is {} bytes; the limit is {}.'.format(len(schema_json), limits.max_schema_bytes),
        )
    prefix_len = len(
        page_prefix(
            run_id=delivery.run_id,
            task_id=delivery.task_id,
            batch_index=0,
            record_offset=0,
            schema_json=schema_json,
        )
    )
    if prefix_len + len(PAGE_SUFFIX) > limits.max_file_bytes:
        raise RemoteQueryFailure(
            'max_file_bytes_exceeded',
            'The repeated schema plus the minimal page envelope exceeds maxFileBytes.',
        )
    return schema_json


def page_prefix(*, run_id: str, task_id: str, batch_index: int, record_offset: int, schema_json: bytes | None) -> bytes:
    """The envelope bytes through the opening of ``data.items``, with no trailing space."""
    head = (
        '{"version":1,"run_id":%s,"task_id":%s,"batch_index":%d,"record_offset":%d,'
        % (json.dumps(run_id), json.dumps(task_id), batch_index, record_offset)
    ).encode('utf-8')
    parts = [head]
    if schema_json is not None:
        parts.append(b'"schema":')
        parts.append(schema_json)
        parts.append(b',')
    parts.append(b'"data":{"items":[')
    return b''.join(parts)


# ---------------------------------------------------------------------------
# Page writer: byte-bounded pages streamed into bounded multipart parts
# ---------------------------------------------------------------------------


class PageWriter:
    """Split encoded rows into byte-bounded JSON pages and stream page bytes to intake.

    At most one page and one part are active at a time. Page bytes stream into
    ``partBytes``-sized parts, so a part boundary may fall anywhere in the byte stream
    (including inside an encoded row or UTF-8 sequence); the object-store completion
    concatenates part bytes exactly, so only the completed page is JSON.

    Row completions are tracked explicitly with row-end offsets: a row belongs to the part
    that contains its final byte, and page row counts are never inferred by counting
    newlines. Before writing a row the writer accounts for the comma, the encoded row, and
    the required closing suffix; a row that cannot fit a fresh page's minimal envelope fails
    with ``row_too_large``.
    """

    def __init__(
        self,
        delivery: RemoteQueryResultDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        schema_json: bytes | None,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
    ):
        self._delivery = delivery
        self._creds = creds
        self._client = client
        self._schema_json = schema_json
        self._guard = guard
        self._stats = stats
        # Active page state. ``_page_bytes`` counts prefix + rows written so far; the
        # closing suffix is appended at close time.
        self._page_open = False
        self._pending = bytearray()
        self._page_bytes = 0
        self._page_rows = 0
        self._page_flushed_bytes = 0
        self._part_number = 1
        self._row_end_offsets: deque[int] = deque()

    def add_row(self, row_bytes: bytes) -> None:
        self._ensure_page()
        suffix_len = len(PAGE_SUFFIX)
        comma_len = 1 if self._page_rows else 0
        page_needed = self._page_bytes + comma_len + len(row_bytes) + suffix_len
        if (
            page_needed > self._delivery.limits.max_file_bytes
            or self._stats.bytes_emitted + page_needed > self._delivery.limits.max_result_bytes
        ):
            # The row does not fit the current page (or would push the run over the total
            # byte cap): close the current NON-EMPTY page and retry the row on a fresh
            # page. An empty page holds nothing but the envelope, so a row that still does
            # not fit cannot be split further and fails the run.
            if self._page_rows:
                self._close_page()
                self._begin_page()
                page_needed = self._page_bytes + len(row_bytes) + suffix_len
            if page_needed > self._delivery.limits.max_file_bytes:
                raise RemoteQueryFailure(
                    'row_too_large',
                    'A single row plus the minimal page envelope exceeds maxFileBytes ({} > {} bytes).'.format(
                        page_needed, self._delivery.limits.max_file_bytes
                    ),
                )
            if self._stats.bytes_emitted + page_needed > self._delivery.limits.max_result_bytes:
                raise RemoteQueryFailure(
                    'max_result_bytes_exceeded',
                    'A single row plus the minimal page envelope exceeds maxResultBytes ({} > {} bytes).'.format(
                        self._stats.bytes_emitted + page_needed, self._delivery.limits.max_result_bytes
                    ),
                )

        if self._page_rows:
            self._pending += b','
            self._page_bytes += 1
        self._pending += row_bytes
        self._page_bytes += len(row_bytes)
        self._row_end_offsets.append(self._page_bytes)
        self._page_rows += 1
        self._stats.rows_emitted += 1
        self._flush_full_parts()

    def finish(self) -> dict[str, Any]:
        """Close the active page, apply zero-row behavior, and finalize the run.

        Returns the compact run receipt: only ``uploadId``, ``pageCount``, ``totalRows``,
        ``totalBytes``. No schema and no bulk bytes ever appear in the receipt.
        """
        if self._page_open:
            self._close_page()
        elif self._schema_json is not None and self._stats.pages_emitted == 0:
            # Zero-row query with schema requested: one schema-bearing empty page so the
            # consumer can still discover the query's columns.
            self._begin_page()
            self._close_page()
        response = self._client.finalize_run(self._creds)
        verify_run_finalize_response(response, self._creds.upload_id)
        return {
            'uploadId': self._creds.upload_id,
            'pageCount': self._stats.pages_emitted,
            'totalRows': self._stats.rows_emitted,
            'totalBytes': self._stats.bytes_emitted,
        }

    def _ensure_page(self) -> None:
        if not self._page_open:
            self._begin_page()

    def _begin_page(self) -> None:
        if self._stats.pages_emitted >= self._delivery.limits.max_pages:
            raise RemoteQueryFailure(
                'max_pages_exceeded',
                'Page count reached the limit of {} pages.'.format(self._delivery.limits.max_pages),
            )
        prefix = page_prefix(
            run_id=self._delivery.run_id,
            task_id=self._delivery.task_id,
            batch_index=self._stats.pages_emitted,
            record_offset=self._stats.rows_emitted,
            schema_json=self._schema_json,
        )
        self._page_open = True
        self._pending += prefix
        self._page_bytes = len(prefix)
        self._page_rows = 0
        self._page_flushed_bytes = 0
        self._part_number = 1
        self._row_end_offsets.clear()

    def _close_page(self) -> None:
        self._guard()
        self._pending += PAGE_SUFFIX
        self._page_bytes += len(PAGE_SUFFIX)
        self._flush_full_parts()
        if self._pending:
            # The final part of a page may be shorter than partBytes; empty pages cannot
            # happen because the prefix plus suffix are always non-empty bytes.
            self._put_part(bytes(self._pending))
            self._pending.clear()
        self._client.finalize_page(self._creds, self._stats.pages_emitted)
        self._stats.pages_emitted += 1
        self._stats.bytes_emitted += self._page_bytes
        self._page_open = False

    def _flush_full_parts(self) -> None:
        part_bytes = self._delivery.part_bytes
        while len(self._pending) >= part_bytes:
            self._put_part(bytes(self._pending[:part_bytes]))
            del self._pending[:part_bytes]

    def _put_part(self, payload: bytes) -> None:
        self._guard()
        self._page_flushed_bytes += len(payload)
        # Row completions are tracked explicitly: a row belongs to the part containing its
        # final byte. Row-end offsets are absolute within the page and strictly increasing,
        # so each row is counted exactly once, in the part where it completes.
        rows_in_part = 0
        while self._row_end_offsets and self._row_end_offsets[0] <= self._page_flushed_bytes:
            rows_in_part += 1
            self._row_end_offsets.popleft()
        self._client.put_part(
            self._creds,
            batch_index=self._stats.pages_emitted,
            part_number=self._part_number,
            payload=payload,
            sha256_hex=hashlib.sha256(payload).hexdigest(),
            rows=rows_in_part,
        )
        self._part_number += 1
        self._stats.parts_emitted += 1


# ---------------------------------------------------------------------------
# Producer: one validated query execution through a named server-side cursor
# ---------------------------------------------------------------------------


def produce_remote_query(
    request: RemoteQueryRequest,
    check: 'PostgreSql',
    creds: UploadCredentials,
    client: UploadClient,
    execution_dbname: str,
    started_at: float,
    stats: RemoteQueryRunStats,
) -> dict[str, Any]:
    """Execute the validated query once and return the compact run receipt.

    The query runs exactly once, through a named server-side cursor declared inside the
    existing read-only transaction with the statement timeout applied; it is never wrapped in
    a probe and never executed twice. Bounded row batches are fetched from the same cursor
    and encoded one row at a time.
    """
    delivery = request.result_delivery
    limits = delivery.limits
    deadline = started_at + limits.timeout_ms / 1000

    def guard() -> None:
        _raise_if_timed_out(deadline)
        _raise_if_cancelled(check)

    cursor_name = 'remote_query_{}'.format(uuid.uuid4().hex)
    with check.db_pool.get_connection(execution_dbname) as conn:
        with conn.cursor() as control:
            in_transaction = False
            try:
                control.execute('BEGIN READ ONLY')
                in_transaction = True
                # SET statements do not accept bind parameters, so the timeout is inlined; it
                # is a validated positive int from the server-injected limits, never raw text.
                control.execute('SET LOCAL statement_timeout = {}'.format(limits.timeout_ms))
                with conn.cursor(name=cursor_name) as server_cursor:
                    register_exact_loaders(server_cursor)
                    server_cursor.execute(request.query)
                    columns = described_columns(server_cursor)
                    validate_columns(columns, limits.max_columns)
                    schema_json = None
                    if request.include_schema:
                        schema_json = build_schema_json(control, columns, delivery)

                    writer = PageWriter(delivery, creds, client, schema_json, guard, stats)
                    guard()
                    while True:
                        rows = server_cursor.fetchmany(REMOTE_QUERY_FETCH_BATCH_ROWS)
                        if not rows:
                            break
                        for row in rows:
                            guard()
                            row_buffer = bytearray()
                            encode_row(row, columns, row_buffer)
                            if len(row_buffer) > limits.max_row_bytes:
                                raise RemoteQueryFailure(
                                    'row_too_large',
                                    'A single row exceeds maxRowBytes ({} > {} bytes).'.format(
                                        len(row_buffer), limits.max_row_bytes
                                    ),
                                )
                            writer.add_row(bytes(row_buffer))
                    return writer.finish()
            finally:
                if in_transaction:
                    try:
                        control.execute('ROLLBACK')
                    except Exception:
                        LOGGER.debug('Unable to roll back remote query read-only transaction', exc_info=True)


def _raise_if_timed_out(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise RemoteQueryFailure('timeout', 'Remote query exceeded timeoutMs.', retryable=True)


def _raise_if_cancelled(check: 'PostgreSql') -> None:
    # The Agent runtime exposes ``is_cancelled`` as a plain bool attribute on the check
    # object, while other runtimes (and test doubles) may expose a callable hook; honor
    # both shapes. An absent attribute carries no cancellation signal.
    is_cancelled = getattr(check, 'is_cancelled', None)
    if is_cancelled is None:
        return
    cancelled = is_cancelled() if callable(is_cancelled) else is_cancelled
    if cancelled:
        raise RemoteQueryFailure('cancelled', 'Remote query run was cancelled.', retryable=True)


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Query allowlist
# ---------------------------------------------------------------------------


def _is_query_allowed(query: str) -> bool:
    return not _is_query_allowlist_enabled() or query in REMOTE_QUERY_QUERY_ALLOWLIST


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


# ---------------------------------------------------------------------------
# Direct multipart upload to its-agent-intake (page-aware)
#
# The integration uploads page parts directly to its-agent-intake over HTTP. The Agent
# forwards the intake base URL and scoped upload token in resultDelivery, and the
# integration reads the org API key and POC application key from Agent config via
# datadog_agent.get_config. Bulk part bytes never traverse the native emit bridge,
# AgentSecure, PAR, or AP action output; only the compact final receipt is emitted back.

#
# Test Drive routing is a narrow development knob, not a production request field: the
# Agent config value names a Test Drive, and the uploader emits the header
# ``test-drive-<validated-name>: 1``. The name never travels through resultDelivery or AP
# action input. When the config is absent or invalid, no Test Drive header is emitted, so
# the upload follows the permanent-service path.

REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY = 'remote_queries.execute.intake_test_drive'
# The header name is built from the validated Test Drive name as ``test-drive-<name>`` with
# the fixed value ``1``. The name is validated against REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN
# so it cannot inject arbitrary headers (no colons, spaces, CR/LF, or other control characters).
REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX = 'test-drive-'
REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE = '1'
REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH = 63
REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN = re.compile(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?')
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
class UploadCredentials:
    base_url: str
    upload_id: str
    api_key: str
    app_key: str
    token: str
    test_drive: str | None


class UploadClient(Protocol):
    def put_part(
        self, creds: UploadCredentials, batch_index: int, part_number: int, payload: bytes, sha256_hex: str, rows: int
    ) -> None: ...

    def finalize_page(self, creds: UploadCredentials, batch_index: int) -> None: ...

    def finalize_run(self, creds: UploadCredentials) -> Mapping[str, Any]: ...

    def abort(self, creds: UploadCredentials) -> None: ...


class RequestsUploadClient:
    """Page-aware HTTP upload client for its-agent-intake. Imports requests lazily."""

    def __init__(self, timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT) -> None:
        self._timeout = timeout

    def _headers(self, creds: UploadCredentials, content_type: str | None = None) -> dict[str, str]:
        headers = {
            'dd-api-key': creds.api_key,
            'dd-application-key': creds.app_key,
            'Authorization': 'Bearer ' + creds.token,
        }
        if content_type is not None:
            headers['Content-Type'] = content_type
        if creds.test_drive:
            test_drive_header = REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX + creds.test_drive
            headers[test_drive_header] = REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE
        return headers

    def put_part(
        self, creds: UploadCredentials, batch_index: int, part_number: int, payload: bytes, sha256_hex: str, rows: int
    ) -> None:
        headers = self._headers(creds, 'application/octet-stream')
        headers['X-DD-Part-SHA256'] = sha256_hex
        headers['X-DD-Part-Bytes'] = str(len(payload))
        headers['X-DD-Part-Rows'] = str(rows)
        url = '{}/uploads/{}/pages/{}/parts/{}'.format(
            creds.base_url.rstrip('/'), creds.upload_id, batch_index, part_number
        )
        _upload_with_retry('PUT', url, headers, payload, self._timeout)

    def finalize_page(self, creds: UploadCredentials, batch_index: int) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/pages/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id, batch_index)
        _upload_with_retry('POST', url, headers, b'{}', self._timeout)

    def finalize_run(self, creds: UploadCredentials) -> Mapping[str, Any]:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id)
        _status, body = _upload_with_retry('POST', url, headers, b'{}', self._timeout)
        return parse_finalize_run_body(body)

    def abort(self, creds: UploadCredentials) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/abort'.format(creds.base_url.rstrip('/'), creds.upload_id)
        try:
            _upload_with_retry('POST', url, headers, b'{}', self._timeout)
        except RemoteQueryFailure:
            LOGGER.debug('Remote query upload abort failed (best-effort)', exc_info=True)


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
                raise RemoteQueryFailure(
                    'upload_failed', 'upload to its-agent-intake rejected with status {}'.format(resp.status_code)
                )
            last_err = 'status {}'.format(resp.status_code)
        if attempt == REMOTE_QUERY_UPLOAD_MAX_RETRIES:
            break
        time.sleep(backoff)
        backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)
    raise RemoteQueryFailure(
        'upload_failed',
        'upload to its-agent-intake failed after {} attempts: {}'.format(REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, last_err),
        retryable=True,
    )


def _get_agent_config(key: str) -> str:
    try:
        value = datadog_agent.get_config(key)
    except Exception:
        LOGGER.debug('Unable to read agent config %s', key, exc_info=True)
        return ''
    if value is None:
        return ''
    return str(value)


def _validate_test_drive_name(value: str | None) -> str | None:
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


def _resolve_upload_credentials(delivery: RemoteQueryResultDelivery) -> UploadCredentials:
    test_drive = _validate_test_drive_name(_get_agent_config(REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY))
    return UploadCredentials(
        base_url=delivery.base_url,
        upload_id=delivery.upload_id,
        api_key=_get_agent_config('api_key'),
        app_key=_get_agent_config('app_key'),
        token=delivery.token,
        test_drive=test_drive,
    )


def _default_upload_client() -> UploadClient:
    return RequestsUploadClient()


def _safe_abort(client: UploadClient, creds: UploadCredentials) -> None:
    if not creds.base_url or not creds.upload_id or not creds.token:
        return
    try:
        client.abort(creds)
    except Exception:
        LOGGER.debug('Remote query upload abort failed (best-effort)', exc_info=True)


# ---------------------------------------------------------------------------
# Event entry points
# ---------------------------------------------------------------------------


def execute_agent_rpc_stream_copy(
    request_json: str | bytes | bytearray, check: 'PostgreSql', emit: RemoteQueryEmit
) -> None:
    """Execute a remote query request and emit page producer events.

    The entry point name is kept for the Agent's rtloader bridge, which resolves this
    function by name. Emits ``metadata`` (STARTED), then one ``final`` (SUCCEEDED with the
    compact receipt) or ``error`` (FAILED) event; bulk page bytes never cross the callback.
    """
    try:
        request = json.loads(request_json)
    except (TypeError, ValueError):
        _emit_event(
            emit,
            _failed_event('invalid_request', 'Invalid remote query request: request_json must be a valid JSON object.'),
        )
        return

    if not isinstance(request, Mapping):
        _emit_event(
            emit,
            _failed_event('invalid_request', 'Invalid remote query request: request_json must be a JSON object.'),
        )
        return

    _execute_upload_stream(request, check, emit)


def _execute_upload_stream(
    request: Mapping[str, Any], check: 'PostgreSql', emit: RemoteQueryEmit, http_client: UploadClient | None = None
) -> None:
    """Drive the producer with the default (or injected) upload client and emit its events."""
    events = iter_agent_rpc_stream_events(request, StaticPostgresCheckRegistry([check]), http_client)
    try:
        for event in events:
            _emit_event(emit, event)
    except BaseException:
        events.close()
        raise


def iter_agent_rpc_stream_events(
    request: Any, registry: PostgresCheckRegistry, http_client: UploadClient | None = None
) -> Iterator[RemoteQueryEvent]:
    """Yield producer events for unit tests and callback adaptation."""
    started_at = time.monotonic()
    try:
        parsed_request = RemoteQueryRequest.model_validate(request)
    except ValidationError as e:
        yield _failed_event('invalid_request', _validation_message(e), elapsed_ms=_elapsed_ms(started_at))
        return

    if not _is_query_allowed(parsed_request.query):
        yield _failed_event(
            'invalid_request',
            'Invalid remote query request: query is not allowlisted.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    target = parsed_request.target
    matches = _resolve_matches(target, registry.iter_postgres_checks())
    LOGGER.debug('Remote query target match count: %d', len(matches))
    if not matches:
        yield _failed_event(
            'target_not_found',
            'No loaded Postgres integration instance matched target selector.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return
    if len(matches) > 1:
        yield _failed_event(
            'target_ambiguous',
            'More than one loaded Postgres integration instance matched target selector.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    check = matches[0]
    execution_dbname = _dbname_from_check(check)
    if execution_dbname is None:
        yield _failed_event(
            'target_unavailable',
            'Matched Postgres check does not expose a configured database name.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    creds = _resolve_upload_credentials(parsed_request.result_delivery)
    if not creds.api_key or not creds.app_key:
        yield _failed_event(
            'credentials_unavailable',
            'Remote query upload requires api_key and app_key to be configured on the Agent.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    db_pool = getattr(check, 'db_pool', None)
    if db_pool is None:
        yield _failed_event(
            'credentials_unavailable',
            'Matched Postgres check does not expose a connection pool.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return
    if getattr(db_pool, 'is_closed', lambda: False)():
        yield _failed_event(
            'target_unavailable',
            'Matched Postgres check connection pool is closed.',
            retryable=False,
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    client = http_client if http_client is not None else _default_upload_client()
    stats = RemoteQueryRunStats()
    yield RemoteQueryEvent('metadata', _started_metadata(parsed_request))

    try:
        receipt = produce_remote_query(parsed_request, check, creds, client, execution_dbname, started_at, stats)
    except RemoteQueryFailure as e:
        _safe_abort(client, creds)
        yield _failed_event(e.code, e.message, retryable=e.retryable, stats=_stats_metadata(stats, started_at))
        return
    except psycopg_errors.QueryCanceled:
        # SQLSTATE class 57014: the server canceled the statement (statement timeout or an
        # explicit cancel); both are retryable query timeouts for the run.
        _safe_abort(client, creds)
        yield _failed_event(
            'timeout',
            'Remote query was canceled by the server (statement timeout or cancellation).',
            retryable=True,
            stats=_stats_metadata(stats, started_at),
        )
        return
    except RuntimeError:
        _safe_abort(client, creds)
        yield _failed_event(
            'target_unavailable',
            'Matched Postgres check connection pool is unavailable.',
            retryable=False,
            stats=_stats_metadata(stats, started_at),
        )
        return
    except BaseException as e:
        _safe_abort(client, creds)
        if not isinstance(e, Exception):
            raise
        LOGGER.exception('Remote query execution failed')
        yield _failed_event('query_failed', 'Remote query execution failed.', stats=_stats_metadata(stats, started_at))
        return

    yield RemoteQueryEvent('final', _succeeded_metadata(receipt, stats, started_at))


def _started_metadata(request: RemoteQueryRequest) -> dict[str, Any]:
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
            'artifactVersion': delivery.artifact_version,
            'partBytes': delivery.part_bytes,
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


def _succeeded_metadata(receipt: Mapping[str, Any], stats: RemoteQueryRunStats, started_at: float) -> dict[str, Any]:
    return {
        'status': 'SUCCEEDED',
        'upload_receipt': dict(receipt),
        'stats': _stats_metadata(stats, started_at),
    }


def _stats_metadata(stats: RemoteQueryRunStats, started_at: float) -> dict[str, Any]:
    return {
        'rowsEmitted': stats.rows_emitted,
        'pagesEmitted': stats.pages_emitted,
        'partsEmitted': stats.parts_emitted,
        'bytesEmitted': stats.bytes_emitted,
        'elapsedMs': _elapsed_ms(started_at),
    }


def _failed_event(
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


def _emit_event(emit: RemoteQueryEmit, event: RemoteQueryEvent) -> None:
    emit(event.event_type, json.dumps(event.metadata, default=str), event.payload)


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


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
