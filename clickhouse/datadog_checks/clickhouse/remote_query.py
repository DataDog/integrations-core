# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Remote query source-page producer for the ClickHouse integration.

Executes one validated query through a dedicated `clickhouse-connect` client,
streams the server-rendered rows with bounded memory, normalizes ClickHouse values into
the pinned cross-language JSON contract, and sends them as record-complete CSV source
pages to its-agent-intake. The stream's own header supplies the descriptor — column names,
ClickHouse type strings, logical types — registered once before any result row is read; the
shared source-page writer frames, bounds, and uploads each page. Intake decodes, redacts,
and writes the final JSON pages, so this module no longer constructs a final JSON envelope
and no longer claims source bytes are final artifact metadata. Bulk page bytes
never traverse the native emit bridge, AgentSecure, PAR, or AP action output; the emit
callback carries only `metadata`/`final`/`error` events, and the final event carries
only the compact run receipt.

The request, event, receipt, descriptor, and intake-upload contracts mirror the Postgres
executor so the Agent bridge (`datadog_checks.clickhouse.remote_query` ->
`execute_agent_rpc_stream_copy`) and its-agent-intake treat both integrations uniformly.
The integration-specific parts are the internal source format, the read-only posture, and
the value normalization documented below. The public result contract is unchanged: ITS and
its consumers see the same RFC-format JSON page artifact (labeled contract_version 1) and events
as Postgres, now produced by intake from the shared source wire.

Wire format (internal to the check<->server hop, not a public result format): `FORMAT
JSONCompactEachRowWithNamesAndTypes`. The stream carries the column names, the ClickHouse
type strings (schema for `includeSchema`, no second metadata query, so the user query
executes exactly once), and one JSON array per row line. Rows are read line-by-line, so
nothing materializes. Values arrive server-rendered: any exact-text CSV/TSV format would
force a custom incremental CSV state machine plus a ClickHouse array/tuple/map literal
parser for composite types, which is the largest correctness risk in the conversion. One
consequence: queries with `WITH TOTALS` fail closed, because the totals arrive as extra
rows after a blank separator line, which is not a row line; merging totals into `data`
would misrepresent them.

Value contract (pinned, cross-language):

  ClickHouse family          JSON representation
  NULL (Nullable)           null
  Bool                       JSON boolean (`0`/`1` spellings, quoted or not, are
                            normalized by type)
  integer types              JSON number with the exact database text (rows are parsed
                            with number hooks that keep every lexeme verbatim; quoted
                            spellings on servers that quote 64-bit+ integers are validated
                            against the JSON integer grammar and lose only their quotes)
  Float/Decimal              JSON number with the exact database text (the same lexeme
                            hooks; quoted decimals are validated against the JSON number
                            grammar and normalized by type)
  non-finite floats          ClickHouse JSON formats render them as `null` by default;
                            the `output_format_json_quote_denormals` setting cannot be
                            requested for read-only-profile users, so the null rendering is
                            accepted rather than rendered inconsistently across users
  String/FixedString         JSON string (server-rendered; result data must be valid UTF-8,
                            otherwise the run fails closed)
  Date/DateTime/UUID/Enum/IP documented ISO-8601/plain strings (exact server text)
  JSON type                  nested JSON value
  Array/Map/Tuple            JSON array/object/array with recursive server rendering
  unknown families           fail closed on values that cannot be converted deliberately

Read-only posture, defense in depth:

1. Server-side settings: `readonly=1` and `max_execution_time` are injected per request
   when the connected user's server-reported `readonly` level is 0. Users with a
   read-only profile (level >= 1) cannot change settings at all, so injecting would fail
   their queries; their own profile enforces the posture. When the server reports no
   usable `readonly` setting, no settings are injected — and that case does not prove
   database-side read-only enforcement.
2. At-most-once execution: the dedicated client disables query retries, and the user query
   is never wrapped, probed, or re-executed.

There is no integration-side SQL statement policy: query text reaches the driver's streaming
call verbatim — no rewriting, no preflight query — and the database alone rejects what it
does not admit. SQL syntax and statement-policy validation belong in the backend; their
ownership and behavior are to be specified in a future RFC update.

Cancellation: the HTTP response is always closed when a run finishes, fails, or is
abandoned; closing (never draining) the socket lets the server cancel the query when
`readonly > 0` and `cancel_http_readonly_queries_on_client_close` is in effect
(clickhouse-connect requests that setting by default when the user's profile allows it).
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

import clickhouse_connect.driver.exceptions as clickhouse_errors
import urllib3.exceptions
from pydantic import ValidationError

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import timing as rq_timing
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing
from datadog_checks.base.utils.remote_queries import upload as rq_upload

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

LOGGER = logging.getLogger(__name__)

# ClickHouse hard cap on repeat() counts: the server rejects anything above 1,000,000 with
# Code 131 (TOO_LARGE_STRING_SIZE), and no setting lifts it, verified on 22.7, 24.8, and
# 26.3. Proof payloads larger than the cap concatenate bounded repeat() parts instead.
REMOTE_QUERY_REPEAT_CAP = 1_000_000
# Exactly nine proof queries, mirrored one for one by the Agent-side allowlist: the seed,
# the identity/schema query, one binary-sensitive UTF-8 payload, and six single-row payload
# queries at the pinned power-of-two sizes. The fixture proof queries are absent on
# purpose: they need harness-created tables (Postgres `cities`/`remote_query_identity`);
# hostName()/currentUser()/version() prove the matched server without any fixture.
REMOTE_QUERY_SEED_QUERY = 'SELECT 1 AS value'
REMOTE_QUERY_IDENTITY_QUERY = 'SELECT hostName() AS host, currentUser() AS user, version() AS version'
# Binary-sensitive but valid-UTF-8 payload: a NUL byte followed by ASCII text. Real servers
# render the NUL as `\u0000` in the stream format, so the row is valid JSON, the pinned
# value contract accepts it, and the page preserves the payload exactly. A non-UTF-8 payload
# (such as `unhex('00ff80')`) is rejected by the value contract by design, so it cannot
# appear on the allowlist.
REMOTE_QUERY_BINARY_QUERY = "SELECT unhex('006162') AS payload"
# The pinned proof payload sizes in bytes: 1, 2, 4, 8, 16, and 32 MiB.
REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES = (1048576, 2097152, 4194304, 8388608, 16777216, 33554432)


def _proof_payload_query(size_bytes: int) -> str:
    """Build the single-row proof query producing exactly `size_bytes` payload bytes.

    Every repeat() count must stay within the server's hard 1,000,000 cap (see
    REMOTE_QUERY_REPEAT_CAP), so a payload of `size_bytes` is the concatenation of
    `size_bytes // 1,000,000` million-byte parts and one remainder part when the size is
    not a multiple of the cap. The construction is a pure function of `size_bytes`, so the
    Agent-side allowlist mirrors the resulting strings byte-for-byte by reproducing this
    algorithm; hand-maintained large SQL strings would drift instead.
    """
    if size_bytes <= 0:
        raise ValueError('Proof payload size must be a positive byte count.')
    whole, remainder = divmod(size_bytes, REMOTE_QUERY_REPEAT_CAP)
    parts = [REMOTE_QUERY_REPEAT_CAP] * whole
    if remainder:
        parts.append(remainder)
    return "SELECT concat({}) AS payload".format(', '.join("repeat('x', {})".format(part) for part in parts))


REMOTE_QUERY_QUERY_ALLOWLIST = frozenset(
    (REMOTE_QUERY_SEED_QUERY, REMOTE_QUERY_IDENTITY_QUERY, REMOTE_QUERY_BINARY_QUERY)
    + tuple(_proof_payload_query(size_bytes) for size_bytes in REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES)
)


# One-stream row format: the first line is the column names, the second the ClickHouse type
# strings, then one JSON array of server-rendered values per line. Line breaks only occur at
# row boundaries (string values are JSON-escaped by the server), so bounded line reads are
# unambiguous.
REMOTE_QUERY_STREAM_FORMAT = 'JSONCompactEachRowWithNamesAndTypes'
# Stream reads are bounded to this chunk size; nothing larger is buffered per read.
REMOTE_QUERY_STREAM_CHUNK_BYTES = 256 * 1024


@dataclass(frozen=True)
class ResultColumn:
    """One described result field: name, type string, normalization family, logical type."""

    name: str
    vendor_data_type: str
    family: str
    logical_type: str


class ClickhouseClient(Protocol):
    """The dedicated per-run client. Only the surface the producer uses is typed."""

    server_settings: Mapping[str, Any]

    def raw_stream(
        self, query: str, settings: Mapping[str, Any] | None = None, fmt: str | None = None
    ) -> StreamSource: ...

    def close(self) -> None: ...


class StreamSource(Protocol):
    """A readable, closeable byte stream (urllib3 HTTPResponse from `raw_stream`)."""

    def read(self, amount: int) -> bytes: ...

    def close(self) -> None: ...


class TimedStreamSource:
    """A `StreamSource` view that accounts each raw stream read as a database fetch.

    The wrapped stream's reads are this producer's only result-fetch calls, so every
    read — header or data — enters the fetch phase, suspending whatever phase encloses
    it (setup during the header rows, the encode loop during data rows). The tracing
    handle keeps one database-fetch region span open across those same reads.
    """

    def __init__(
        self,
        stream: StreamSource,
        timings: rq_timing.RemoteQueryProducerTimings,
        tracing: rq_tracing.RemoteQueryProducerTracing | None = None,
    ):
        self._stream = stream
        self._timings = timings
        self._tracing = tracing if tracing is not None else rq_tracing.NULL_PRODUCER_TRACING

    def read(self, amount: int) -> bytes:
        with self._timings.phase('database_fetch'):
            self._tracing.enter_fetch()
            return self._stream.read(amount)

    def close(self) -> None:
        self._stream.close()


# ---------------------------------------------------------------------------
# ClickHouse value contract (pinned, cross-language)
#
# Rows arrive server-rendered as JSON arrays, so string quoting, NULLs, booleans, and
# composite types (Array/Map/Tuple/JSON) are already valid JSON; the encoder below only
# re-serializes values into the row object. Numbers keep their exact server lexemes:
# rows are parsed with number hooks that carry each lexeme through verbatim, nested
# composite values included, so no int()/Decimal/repr round-trip can rewrite the text.
# Servers that quote 64-bit+ integers or decimals (ClickHouse JSON output settings)
# deliver them as JSON strings; the declared column type validates the text against its
# family's JSON number grammar and normalizes it back to the same raw lexeme, removing
# only the quotes.

# A JSON number per RFC 8259: no leading zeros, optional fraction and exponent. Server
# numeric text must already satisfy this; anything else fails closed. The shared
# `JSON_NUMBER_PATTERN` pins the grammar for quoted decimal/float spellings; quoted
# integer spellings accept the JSON integer form alone (no exponent, no plus sign, no
# leading zeros).
JSON_NUMBER_PATTERN = re.compile(r'\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\Z')

JSON_INTEGER_PATTERN = re.compile(r'\A-?(?:0|[1-9][0-9]*)\Z')


@dataclass(frozen=True)
class RawJsonNumber:
    """One server-rendered JSON number, carried as its exact lexeme.

    The row-line parse hooks and the quoted-spelling normalization both produce this
    instead of an `int` or `Decimal`, so the encoder emits the server's exact numeric
    text: no int()/Decimal/str round-trip can rewrite it (`0.000000001` stays itself,
    never `1E-9`; `1e-7` keeps its case and sign; `-0` survives). By construction
    the text satisfies the JSON number grammar — the parse hooks only see JSON lexemes,
    and quoted spellings are validated before their quotes are removed.
    """

    text: str


_INTEGER_TYPE_NAMES = frozenset(
    (
        'Int8',
        'Int16',
        'Int32',
        'Int64',
        'Int128',
        'Int256',
        'UInt8',
        'UInt16',
        'UInt32',
        'UInt64',
        'UInt128',
        'UInt256',
    )
)
_FLOAT_TYPE_NAMES = frozenset(('Float32', 'Float64', 'BFloat16'))
# Type wrappers that carry the base type as their argument.
_TYPE_WRAPPER_PREFIXES = ('Nullable(', 'LowCardinality(')
_AGGREGATE_FUNCTION_PREFIX = 'SimpleAggregateFunction('


def base_type_name(type_string: str) -> str:
    """Peel Nullable/LowCardinality/SimpleAggregateFunction wrappers to the base type name."""
    current = type_string
    while True:
        next_type = None
        for prefix in _TYPE_WRAPPER_PREFIXES:
            if current.startswith(prefix) and current.endswith(')'):
                next_type = current[len(prefix) : -1]
                break
        if next_type is None and current.startswith(_AGGREGATE_FUNCTION_PREFIX) and current.endswith(')'):
            # SimpleAggregateFunction(fn, T): the base type is the second argument.
            arguments = current[len(_AGGREGATE_FUNCTION_PREFIX) : -1].split(',', 1)
            next_type = arguments[1].strip() if len(arguments) == 2 else None
        if next_type is None:
            return current
        current = next_type


def type_family(type_string: str) -> str:
    """Classify a ClickHouse type string into a normalization family."""
    base = base_type_name(type_string)
    if base in _INTEGER_TYPE_NAMES:
        return 'integer'
    if base.startswith('Decimal'):
        # Decimal, Decimal32/64/128/256, and parameterized spellings Decimal(P, S).
        return 'decimal'
    if base in _FLOAT_TYPE_NAMES:
        return 'float'
    if base == 'Bool':
        return 'bool'
    return 'other'


def logical_type_for_type_string(type_string: str) -> str:
    """Map one ClickHouse type string to a closed descriptor logical type, deterministically.

    Wrappers (Nullable/LowCardinality/SimpleAggregateFunction) peel to the base type; the
    pinned families map to their stable cross-database families; array/map/tuple/nested
    families and the JSON type carry nested JSON values. Anything else — exotic or
    vendor-specific families whose values still must pass the fail-closed value contract —
    is `vendor`, never a stringify escape hatch.
    """
    base = base_type_name(type_string)
    if base in _INTEGER_TYPE_NAMES:
        return 'integer'
    if base.startswith('Decimal'):
        return 'decimal'
    if base in _FLOAT_TYPE_NAMES:
        return 'float'
    if base == 'Bool':
        return 'boolean'
    if base == 'String' or base.startswith('FixedString('):
        return 'string'
    if base in ('Date', 'Date32') or base.startswith('DateTime'):
        return 'temporal'
    if base == 'UUID' or base.startswith('Enum'):
        return 'string'
    if base in ('IPv4', 'IPv6'):
        return 'vendor'
    if base == 'JSON' or base.startswith(('Array(', 'Map(', 'Tuple(', 'Nested(')):
        return 'json'
    return 'vendor'


def normalize_typed_value(family: str, value: Any) -> Any:
    """Normalize server value spellings that depend on server JSON output settings.

    Only type-known numeric/bool families are touched, so a String column holding digits
    stays a JSON string. A quoted integer/decimal/float spelling is validated against its
    family's JSON number grammar and becomes the same raw-lexeme representation the parse
    hooks produce, losing only its two quotes; a spelling outside the grammar stays a
    string for the encoder to accept verbatim. Bool's legacy spellings — quoted or not —
    become JSON booleans. Anything unexpected is left for the encoder to fail closed on.
    """
    if family == 'integer' and isinstance(value, str):
        if JSON_INTEGER_PATTERN.match(value):
            return RawJsonNumber(value)
        return value
    if family in ('decimal', 'float') and isinstance(value, str):
        if JSON_NUMBER_PATTERN.match(value):
            return RawJsonNumber(value)
        return value
    if family == 'bool':
        if isinstance(value, str) and value in ('true', 'false', '0', '1'):
            return value in ('true', '1')
        if isinstance(value, RawJsonNumber) and value.text in ('0', '1'):
            return value.text == '1'
        return value
    return value


def _encode_cell_token(value: Any) -> tuple[bytes, int]:
    """Encode parsed server JSON, preserving numeric lexemes and redaction size bounds."""
    if value is None:
        return b'null', 4
    if isinstance(value, bool):
        token = b'true' if value else b'false'
        return token, len(token)
    if isinstance(value, RawJsonNumber):
        token = value.text.encode('ascii')
        return token, rq_pages.redactable_leaf_final_bound(token)
    if isinstance(value, str):
        return rq_pages.string_cell_token(value)
    if isinstance(value, list):
        parts: list[bytes] = [b'[']
        bound = 2
        for index, item in enumerate(value):
            if index:
                parts.append(b',')
                bound += 1
            token, item_bound = _encode_cell_token(item)
            parts.append(token)
            bound += item_bound
        parts.append(b']')
        return b''.join(parts), bound
    if isinstance(value, dict):
        parts = [b'{']
        bound = 2
        first = True
        for key, item in value.items():
            if not isinstance(key, str):
                raise rq_contract.RemoteQueryFailure('unsupported_value', 'JSON object keys must be strings.')
            if not first:
                parts.append(b',')
                bound += 1
            first = False
            key_token = rq_contract.canonical_json_bytes(key)
            parts.append(key_token)
            parts.append(b':')
            bound += rq_pages.redactable_leaf_final_bound(key_token) + 1
            token, item_bound = _encode_cell_token(item)
            parts.append(token)
            bound += item_bound
        parts.append(b'}')
        return b''.join(parts), bound
    raise rq_contract.RemoteQueryFailure(
        'unsupported_value',
        'ClickHouse value of type {} has no conversion in the JSON contract.'.format(type(value).__name__),
    )


def encode_row(values: Sequence[Any], columns: Sequence[ResultColumn]) -> list[rq_pages.EncodedCell]:
    """Encode one result row as one canonical cell token per described column.

    The row-object JSON document is never built: intake assembles the final rows from these
    cell tokens in descriptor order.
    """
    if len(values) != len(columns):
        raise rq_contract.RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
    return [
        rq_pages.EncodedCell(*_encode_cell_token(normalize_typed_value(column.family, value)))
        for column, value in zip(columns, values)
    ]


# ---------------------------------------------------------------------------
# Result header and schema
# ---------------------------------------------------------------------------


def _parse_json_line(line: bytes) -> Any:
    try:
        # Number hooks carry every numeric lexeme through verbatim — nested composite
        # values included — so no int()/Decimal/str round-trip can rewrite the text.
        return json.loads(line, parse_float=RawJsonNumber, parse_int=RawJsonNumber, parse_constant=str)
    except (UnicodeDecodeError, ValueError):
        # Result data must be valid UTF-8 JSON; never echo the offending line.
        raise rq_contract.RemoteQueryFailure(
            'query_failed', 'The result stream carried a row that is not valid JSON.'
        ) from None


def _parse_header_row(line: bytes, expected: str) -> list[str]:
    parsed = _parse_json_line(line)
    if not isinstance(parsed, list) or not parsed or not all(isinstance(entry, str) and entry for entry in parsed):
        raise rq_contract.RemoteQueryFailure(
            'query_failed', 'The result stream did not carry usable {} in its header row.'.format(expected)
        )
    return parsed


def build_columns(names: Sequence[str], types: Sequence[str]) -> list[ResultColumn]:
    if len(names) != len(types):
        raise rq_contract.RemoteQueryFailure(
            'query_failed', 'The result stream header rows do not agree on column count.'
        )
    return [
        ResultColumn(
            name=name,
            vendor_data_type=vendor_data_type,
            family=type_family(vendor_data_type),
            logical_type=logical_type_for_type_string(vendor_data_type),
        )
        for name, vendor_data_type in zip(names, types)
    ]


def validate_columns(columns: Sequence[ResultColumn], max_columns: int) -> None:
    if len(columns) > max_columns:
        raise rq_contract.RemoteQueryFailure(
            'max_columns_exceeded',
            'Query described {} result columns; the limit is {}.'.format(len(columns), max_columns),
        )
    seen = set()
    for column in columns:
        if column.name in seen:
            raise rq_contract.RemoteQueryFailure(
                'duplicate_columns',
                'Duplicate result-column name {!r} cannot key a JSON row object.'.format(column.name),
            )
        seen.add(column.name)


def build_upload_descriptor(
    request: rq_contract.RemoteQueryRequest, columns: Sequence[ResultColumn], agent_hostname: str
) -> rq_contract.RemoteQueryUploadDescriptor:
    """Build the immutable source-page descriptor from the streamed header's columns.

    The stream's type row is the schema source — no second metadata query — and the
    descriptor is registered once, before any result row is read; intake stamps the schema
    (when requested) into every final page from it.
    """
    return rq_contract.RemoteQueryUploadDescriptor(
        format_version=rq_contract.REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION,
        include_schema=request.include_schema,
        agent_hostname=agent_hostname,
        columns=[
            rq_contract.RemoteQueryDescriptorColumn(
                column_name=column.name,
                vendor_data_type=column.vendor_data_type,
                logical_type=column.logical_type,
            )
            for column in columns
        ],
    )


# Slack for header-row buffering: the header lines carry names and type strings whose
# byte accounting belongs to the schema/columns budgets, not the row budgets.
REMOTE_QUERY_HEADER_LINE_SLACK = 1024

# A few bytes of slack beyond the derived line bound, keeping the read-time ceiling safely
# above any line whose framed record still fits maxRowBytes.
REMOTE_QUERY_ROW_LINE_SLACK = 8

# The two quote bytes one column's value can lose to normalization: removing a type-known
# quoted spelling's quotes is the only normalization that shortens a cell below its
# server-rendered spelling — quoted 64-bit integer/decimal/float lexemes (ClickHouse JSON
# output settings) validate against the family's JSON number grammar and become raw
# numbers, quoted `true`/`false` become JSON booleans. Every other value keeps the
# server's exact bytes (strings verbatim, numbers with their exact lexemes, composites
# re-serialized from the same tokens) or grows the record (CSV quoting of tokens carrying
# separators, bool numeric spellings widened to true/false).
REMOTE_QUERY_ROW_COLUMN_QUOTE_RESERVE = 2


def row_line_ceiling(max_row_bytes: int, max_columns: int) -> int:
    """A line-length bound past which the framed record cannot fit `maxRowBytes`.

    A compliant framed record is never shorter than its server line minus one byte and
    minus two quote bytes per column: the line's brackets and commas are the record's
    fields and separators, the record adds one trailing newline, and the quote removal
    above is the only shrinking normalization, once per column. The delivered max column
    count bounds how many columns can lose their quotes, so a line longer than
    `maxRowBytes` plus that reserve plus the fixed slack cannot produce a compliant
    record. The ceiling bounds the read buffer, so an oversized line fails the run during
    the read instead of being buffered whole; the exact `maxRowBytes` check still runs
    on the framed record.
    """
    return max(64, max_row_bytes + REMOTE_QUERY_ROW_COLUMN_QUOTE_RESERVE * max_columns + REMOTE_QUERY_ROW_LINE_SLACK)


class LineBoundTracker:
    """The maximum buffered line size for each line of the result stream.

    Line 0 is the column-name header row, line 1 the column-type header row, and lines 2+
    are data rows. The bound is enforced while bytes accumulate (a row line may exceed a
    normal read chunk), so a single unterminated or oversized line fails the run
    deterministically instead of growing the buffer without limit; nothing is ever
    truncated silently.

    Header rows are bounded by the larger of the two byte budgets: with `includeSchema`
    the encoded schema (names plus types) must fit `maxSchemaBytes` anyway, and without it
    the column names must repeat inside every `maxRowBytes`-bounded row. An exotic
    oversized type string on a schema-less run fails closed here rather than buffering it.
    Request validation caps both budgets at `maxFileBytes`, so the header bound stays
    within the platform page ceiling plus the fixed header slack.
    """

    def __init__(self, limits: rq_contract.RemoteQueryUploadLimits):
        self._header_bound = max(limits.max_schema_bytes, limits.max_row_bytes) + REMOTE_QUERY_HEADER_LINE_SLACK
        self._row_bound = row_line_ceiling(limits.max_row_bytes, limits.max_columns)
        self._max_row_bytes = limits.max_row_bytes

    def for_index(self, index: int) -> int:
        return self._header_bound if index < 2 else self._row_bound

    def too_large_failure(self, index: int, buffered: int) -> rq_contract.RemoteQueryFailure:
        if index < 2:
            return rq_contract.RemoteQueryFailure(
                'query_failed', 'The result stream header row exceeded the allowed size.'
            )
        return rq_contract.RemoteQueryFailure(
            'row_too_large',
            'A single row exceeds maxRowBytes ({} buffered bytes; the limit is {} bytes).'.format(
                buffered, self._max_row_bytes
            ),
        )


# ---------------------------------------------------------------------------
# Producer: one validated query execution through a dedicated streaming client
# ---------------------------------------------------------------------------


def resolve_readonly_settings(client: ClickhouseClient, timeout_ms: int) -> dict[str, Any]:
    """Per-request settings enforcing the read-only posture and a server-side timeout.

    `timeout_ms` is the remaining run wall in milliseconds at the time the request is
    sent, so a stream opened late cannot overrun the run-wide deadline.

    ClickHouse `readonly` levels: 0 no restrictions, 1 read-only with settings frozen,
    2 read-only with settings changes allowed (except `readonly` itself). The client's
    server-settings discovery reports the connected user's current level:

    - level 0: inject `readonly=1` (which also activates cancel-on-close, see the module
      docstring) and a server-side `max_execution_time` kill for runaway execution;
    - level >= 1: settings cannot be changed for that user, so injecting would fail their
      queries; the profile's own read-only posture already applies.
    - unknown (no discovery data): inject nothing. A missing or unparseable `readonly`
      setting results in no injected settings, and that case does not prove database-side
      read-only enforcement. The client would also refuse to send an unknown setting (its
      validation fails closed), so injecting is not an option.
    """
    settings = getattr(client, 'server_settings', None)
    setting = settings.get('readonly') if settings is not None else None
    if setting is None:
        return {}
    try:
        current = int(str(getattr(setting, 'value', '')))
    except (TypeError, ValueError):
        return {}
    if current >= 1:
        return {}
    return {'readonly': 1, 'max_execution_time': timeout_ms / 1000}


def iter_stream_lines(stream: StreamSource, guard: Callable[[], None], bounds: LineBoundTracker) -> Iterator[bytes]:
    """Yield newline-terminated lines from the byte stream, reading bounded chunks.

    Row values are JSON-escaped by the server, so a raw newline in the stream only occurs
    at row boundaries. The guard runs after every chunk so a silent server still trips the
    deadline/cancellation checks between reads. Reads are sized to the line bound, so the
    buffer never grows past it; a line that reaches its bound without completing fails
    the run instead of being buffered whole.
    """
    buffer = bytearray()
    line_index = 0
    while True:
        bound = bounds.for_index(line_index)
        allowance = bound - len(buffer)
        if allowance <= 0:
            raise bounds.too_large_failure(line_index, len(buffer))
        chunk = stream.read(min(REMOTE_QUERY_STREAM_CHUNK_BYTES, allowance))
        if not chunk:
            break
        guard()
        buffer += chunk
        while True:
            index = buffer.find(b'\n')
            if index < 0:
                break
            if index > bound:
                raise bounds.too_large_failure(line_index, index)
            yield bytes(buffer[:index])
            line_index += 1
            del buffer[: index + 1]
        if len(buffer) > bounds.for_index(line_index):
            raise bounds.too_large_failure(line_index, len(buffer))
    if buffer:
        # The server writes a trailing newline after every row, so a non-empty remainder
        # can only be a truncated final line; it is yielded and rejected by the JSON parse.
        yield bytes(buffer)


def _run_streamed_query(
    request: rq_contract.RemoteQueryRequest,
    clickhouse_client: ClickhouseClient,
    creds: rq_upload.UploadCredentials,
    client: rq_upload.UploadClient,
    agent_hostname: str,
    guard: Callable[[], None],
    stats: rq_contract.RemoteQueryRunStats,
    deadline: float,
    timings: rq_timing.RemoteQueryProducerTimings | None = None,
    tracing: rq_tracing.RemoteQueryProducerTracing | None = None,
) -> dict[str, Any]:
    """Stream the query result into bounded JSON pages and return the run receipt."""
    timings = timings or rq_timing.RemoteQueryProducerTimings(time.monotonic())
    tracing = tracing if tracing is not None else rq_tracing.NULL_PRODUCER_TRACING
    delivery = request.result_delivery
    limits = delivery.limits
    stream = None
    try:
        with timings.phase('database_setup'), tracing.phase('database_setup'):
            # The second setup segment (client creation was the first, in the caller):
            # settings resolution, stream open, header/column building, and descriptor
            # registration. Every raw stream read inside — header or data — is the fetch phase.
            settings = resolve_readonly_settings(clickhouse_client, rq_events.remaining_wall_ms(deadline))
            # The user query is passed verbatim; the client appends the FORMAT clause.
            stream = TimedStreamSource(
                clickhouse_client.raw_stream(request.query, settings=settings, fmt=REMOTE_QUERY_STREAM_FORMAT),
                timings,
                tracing,
            )
            bounds = LineBoundTracker(limits)
            lines = iter_stream_lines(stream, guard, bounds)
            try:
                names_line = next(lines)
                types_line = next(lines)
            except StopIteration:
                raise rq_contract.RemoteQueryFailure(
                    'query_failed', 'The result stream did not carry the column name and type header rows.'
                ) from None
            columns = build_columns(
                _parse_header_row(names_line, 'column names'), _parse_header_row(types_line, 'column types')
            )
            validate_columns(columns, limits.max_columns)
            # The descriptor is registered once from the stream's own header before any result
            # row is read; the executing check's Agent-reported hostname travels in it so intake
            # stamps the envelope with the agent node identity Fleet reports, never
            # socket.gethostname().
            descriptor = build_upload_descriptor(request, columns, agent_hostname)
            writer = rq_pages.SourcePageWriter(delivery, creds, client, descriptor, guard, stats, timings, tracing)
        try:
            guard()
            with timings.phase('encode_and_page_build'), tracing.phase('encode_and_page_build'):
                for line in lines:
                    guard()
                    values = _parse_json_line(line)
                    if not isinstance(values, list):
                        raise rq_contract.RemoteQueryFailure('query_failed', 'A result row was not a JSON array.')
                    writer.add_row(encode_row(values, columns))
            return writer.finish()
        finally:
            # Release the page even if the response stream or row conversion fails.
            writer.discard()
    finally:
        # Always close (never drain) the response: closing the socket is what lets the server
        # cancel an abandoned read-only query (see the module docstring).
        if stream is not None:
            try:
                stream.close()
            except Exception:
                # Fixed text only: the transport's exception can quote the URL or request bytes.
                LOGGER.debug('Unable to close the remote query response stream')


def produce_remote_query(
    request: rq_contract.RemoteQueryRequest,
    check: 'ClickhouseCheck',
    creds: rq_upload.UploadCredentials,
    client: rq_upload.UploadClient,
    started_at: float,
    stats: rq_contract.RemoteQueryRunStats,
    clickhouse_client_factory: Callable[['ClickhouseCheck', int], ClickhouseClient] | None = None,
    timings: rq_timing.RemoteQueryProducerTimings | None = None,
    tracing: rq_tracing.RemoteQueryProducerTracing | None = None,
) -> dict[str, Any]:
    """Execute the validated query once and return the compact run receipt.

    The query runs exactly once, through a dedicated client whose query retries are
    disabled; it is never wrapped in a probe and never executed twice. Row lines are read
    from the streamed response incrementally and encoded one row at a time.

    Producer phases: client creation, stream open, header/column building, and descriptor
    registration are database setup; every raw stream read is a database fetch; the row loop
    is encode and page build (with any upload `add_row` triggers nested inside it); page
    uploads and finalize are accounted by the shared source-page writer. The native
    producer spans open at exactly these phase boundaries — `tracing` is fail-open and
    additive to the timing accumulator.
    """
    delivery = request.result_delivery
    limits = delivery.limits
    deadline = started_at + limits.timeout_ms / 1000
    timings = timings or rq_timing.RemoteQueryProducerTimings(time.monotonic())
    tracing = tracing if tracing is not None else rq_tracing.NULL_PRODUCER_TRACING

    def guard() -> None:
        rq_events.raise_if_timed_out(deadline)
        rq_events.raise_if_cancelled(check)

    clickhouse_client = None
    try:
        factory = clickhouse_client_factory if clickhouse_client_factory is not None else _default_client_factory
        try:
            # The first database-setup segment: client creation. The send/receive timeout
            # derives from the remaining wall, not the full delivered budget, so a client
            # created late cannot wait past the run-wide deadline.
            with timings.phase('database_setup'), tracing.phase('database_setup'):
                clickhouse_client = factory(check, max(1, math.ceil(deadline - time.monotonic())))
        except rq_contract.RemoteQueryFailure:
            raise
        except Exception:
            # A connection-level failure: the matched instance could not be reached or refused
            # the request. Never echo the underlying text or traceback (either can quote
            # identifiers or credentials embedded in connection error strings).
            LOGGER.debug('Remote query client creation failed')
            raise rq_contract.RemoteQueryFailure(
                'target_unavailable', 'The matched ClickHouse instance is not reachable for remote queries.'
            ) from None
        try:
            receipt = _run_streamed_query(
                request, clickhouse_client, creds, client, check.hostname, guard, stats, deadline, timings, tracing
            )
        except rq_contract.RemoteQueryFailure:
            raise
        except clickhouse_errors.OperationalError:
            # A transport-level failure: the request never got a usable server response.
            LOGGER.debug('Remote query transport failed')
            raise rq_contract.RemoteQueryFailure(
                'target_unavailable', 'The matched ClickHouse instance is not reachable for remote queries.'
            ) from None
        except (
            TimeoutError,
            ConnectionError,
            urllib3.exceptions.ReadTimeoutError,
            urllib3.exceptions.ProtocolError,
        ):
            # The stream died mid-read: server-side cancellation (max_execution_time or
            # cancel-on-close) or a dropped connection. Both are retryable for the run.
            LOGGER.debug('Remote query stream failed mid-stream')
            raise rq_contract.RemoteQueryFailure(
                'timeout',
                'The remote query stream was interrupted (server cancellation or connection failure).',
                True,
            ) from None
        except clickhouse_errors.DatabaseError:
            # The server answered with an error (bad SQL, missing table, permissions), or
            # the client refused a request-level setting. The instance is reachable, the
            # run is not. Never echo the underlying message: it can quote query text.
            LOGGER.debug('Remote query rejected by the server')
            raise rq_contract.RemoteQueryFailure('query_failed', 'Remote query execution failed.') from None
        except Exception:
            # Fixed text only: an unexpected exception can carry raw row fragments or query
            # text.
            LOGGER.error('Remote query execution failed')
            raise rq_contract.RemoteQueryFailure('query_failed', 'Remote query execution failed.') from None
        return receipt
    finally:
        # The streamed response is owned and closed by _run_streamed_query; the client owns
        # no pool of its own, so closing it is a no-op for the shared connection pool.
        if clickhouse_client is not None:
            try:
                clickhouse_client.close()
            except Exception:
                LOGGER.debug('Unable to close the remote query client')


def _default_client_factory(check: 'ClickhouseCheck', timeout_seconds: int) -> ClickhouseClient:
    """Create the per-run client from the matched check.

    `timeout_seconds` is the remaining run wall, so the send/receive timeout bounds a
    single silent socket read inside the run deadline rather than the check's own (short)
    `read_timeout`; the client-side deadline guard remains the authoritative cumulative
    bound.
    """
    factory = getattr(check, 'create_remote_query_client', None)
    if factory is None:
        raise rq_contract.RemoteQueryFailure(
            'target_unavailable', 'The matched ClickHouse check cannot create a remote query client.'
        )
    return factory(send_receive_timeout=timeout_seconds)


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def _check_matches_target(check: 'ClickhouseCheck', target: rq_contract.RemoteQueryTarget) -> bool:
    """Whether the supplied check admits the target.

    A database_instance selector matches by rendered identifier; a tuple selector matches
    the check's configured endpoint and database. Selecting zero, one, or many matching
    checks across the Agent's loaded checks is the Agent's own responsibility; this
    predicate answers for the one check the bridge supplied.
    """
    if target.database_instance is not None:
        return getattr(check, 'database_identifier', None) == target.database_instance
    return _target_from_check(check) == target


def _target_from_check(check: 'ClickhouseCheck') -> rq_contract.RemoteQueryTarget | None:
    config = getattr(check, '_config', None)
    if config is None:
        return None

    try:
        # The wire contract is {host, port, dbname}; the ClickHouse instance config spells
        # them {server, port, db}.
        return rq_contract.RemoteQueryTarget(host=config.server, port=config.port, dbname=config.db)
    except (AttributeError, ValidationError):
        return None


# ---------------------------------------------------------------------------
# Agent entry points
# ---------------------------------------------------------------------------


def execute_agent_rpc_stream_copy(
    request_json: str | bytes | bytearray, check: 'ClickhouseCheck', emit: rq_contract.RemoteQueryEmit
) -> None:
    """Execute a remote query request and emit page producer events.

    The entry point name is kept for the Agent's rtloader bridge, which resolves this
    function by name. Emits `metadata` (STARTED), then one `final` (SUCCEEDED with the
    compact receipt) or `error` (FAILED) event; bulk page bytes never cross the callback.
    Diagnostics collection starts before the request JSON is parsed, so even a malformed
    request reports its measured wall.
    """
    request, timings, failure = rq_events.parse_agent_rpc_request(request_json)
    if failure is not None:
        rq_events.emit_event(emit, failure)
        return

    rq_events.emit_agent_rpc_events(emit, iter_agent_rpc_stream_events(request, check, timings=timings))


def iter_agent_rpc_stream_events(
    request: Any,
    check: 'ClickhouseCheck',
    http_client: rq_upload.UploadClient | None = None,
    clickhouse_client_factory: Callable[['ClickhouseCheck', int], ClickhouseClient] | None = None,
    timings: rq_timing.RemoteQueryProducerTimings | None = None,
) -> Iterator[rq_contract.RemoteQueryEvent]:
    """Execute on the supplied check; emit only status and the intake receipt.

    The produce hook is `produce_remote_query` itself, its adapter-owned phase boundaries
    opening the native producer spans. Once the request is admitted — validation and the
    allowlist — the run opens its native producer spans fail-open through
    `open_remote_query_producer_tracing`: a root span on the request's trace context
    covering the admission failures below, the abort span around the failure tail's upload
    abort, and the terminal status; every span failure is swallowed without changing an
    event, a receipt, a retry, or an error.
    """
    timings = timings or rq_timing.RemoteQueryProducerTimings(time.monotonic())
    stats = None
    client = None
    creds = None
    tracing = rq_tracing.NULL_PRODUCER_TRACING
    try:
        try:
            parsed = rq_events.validate_request(request, REMOTE_QUERY_QUERY_ALLOWLIST)
            # Native producer spans cover every admitted run — the admission failures below
            # included — as a root span on the request's trace context, additive to the
            # timing accumulator and the event contract, fail-open through every boundary.
            tracing = rq_tracing.open_remote_query_producer_tracing(parsed.trace_context, 'clickhouse')
            tracing.open_root(parsed.result_delivery)
            if not _check_matches_target(check, parsed.target):
                raise rq_contract.RemoteQueryFailure(
                    'target_not_found', 'No loaded ClickHouse integration instance matched target selector.'
                )
            creds = rq_upload.resolve_upload_credentials(
                parsed.result_delivery, timings.started_at, parsed.trace_context
            )
            if not creds.api_key or not creds.app_key:
                raise rq_contract.RemoteQueryFailure(
                    'credentials_unavailable',
                    'Remote query upload requires api_key and app_key to be configured on the Agent.',
                )
            if getattr(check, '_pool_manager', None) is None:
                raise rq_contract.RemoteQueryFailure(
                    'target_unavailable', 'Matched ClickHouse check HTTP connection pool is unavailable.'
                )
            client = (
                http_client
                if http_client is not None
                else rq_upload.RequestsUploadClient(timings=timings, tracing=tracing)
            )
            stats = rq_contract.RemoteQueryRunStats()
            yield rq_contract.RemoteQueryEvent('metadata', rq_events.started_metadata(parsed))
            receipt = produce_remote_query(
                parsed,
                check,
                creds,
                client,
                timings.started_at,
                stats,
                clickhouse_client_factory=clickhouse_client_factory,
                timings=timings,
                tracing=tracing,
            )
        except BaseException as error:
            if client is not None:
                with tracing.abort_span():
                    rq_upload.safe_abort(client, creds)
            # The root span's counters mirror the stats the failure event carries; the
            # failure classification rides the same closed event error-code vocabulary, and
            # an admission failure before the run's stats exist carries all-zero counters.
            terminal_stats = stats if stats is not None else rq_contract.RemoteQueryRunStats()
            if not isinstance(error, Exception):
                # The stream was terminated mid-run (cancellation or an emit callback
                # failure): the root span closes with a fixed classification and the signal
                # re-raises, never swallowed into an ordinary query failure.
                tracing.fail('interrupted', terminal_stats)
                raise
            tracing.fail(
                error.code if isinstance(error, rq_contract.RemoteQueryFailure) else 'query_failed', terminal_stats
            )
            yield rq_events.query_failure_event(error, timings, stats)
            return
        tracing.succeed(stats)
        yield rq_contract.RemoteQueryEvent(
            'final', rq_events.succeeded_metadata(receipt, stats, timings.started_at, timings)
        )
    finally:
        # The run's only flush, best-effort: the root span finishes here at the latest and
        # the singleton is never shut down.
        tracing.close()
