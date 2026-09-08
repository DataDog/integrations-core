# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Remote query JSON page producer for the ClickHouse integration.

Executes one validated read-only query through a dedicated ``clickhouse-connect`` client,
streams the server-rendered rows with bounded memory, normalizes ClickHouse values into
the pinned cross-language JSON contract, splits the rows into byte-bounded JSON page files,
and uploads each complete page to its-agent-intake as one direct HTTP request. The shared
page writer retains one bounded page in memory through byte-identical retries.
Bulk page bytes never traverse the native emit bridge, AgentSecure, PAR, or AP action
output; the emit callback carries only ``metadata``/``final``/``error`` events, and the
final event carries only the compact run receipt.

The request, event, receipt, page-artifact, and intake-upload contracts mirror the Postgres
executor so the Agent bridge (``datadog_checks.clickhouse.remote_query`` ->
``execute_agent_rpc_stream_copy``) and its-agent-intake treat both integrations uniformly.
The integration-specific parts are the internal source format, the read-only posture, and
the value normalization documented below. The public result contract is unchanged: ITS and
its consumers see the same v1 JSON page artifact and events as Postgres.

Wire format (internal to the check<->server hop, not a public result format): ``FORMAT
JSONCompactEachRowWithNamesAndTypes``. The stream carries the column names, the ClickHouse
type strings (schema for ``includeSchema``, no second metadata query, so the user query
executes exactly once), and one JSON array per row line. Rows are read line-by-line, so
nothing materializes. Values arrive server-rendered: any exact-text CSV/TSV format would
force a custom incremental CSV state machine plus a ClickHouse array/tuple/map literal
parser for composite types, which is the largest correctness risk in the conversion. One
consequence: queries with ``WITH TOTALS`` fail closed, because the totals arrive as extra
rows after a blank separator line, which is not a row line; merging totals into ``data``
would misrepresent them.

Value contract (pinned, cross-language):

  ClickHouse family          JSON representation
  NULL (Nullable)           null
  Bool                       JSON boolean (``0``/``1`` spellings normalized by type)
  integer types              JSON number with the exact database text (quoted spellings
                            on servers that quote 64-bit+ integers are normalized back to
                            exact numbers)
  Float/Decimal              JSON number with the exact database text (rows are parsed with
                            ``parse_float=Decimal``, quoted decimals are normalized by type)
  non-finite floats          ClickHouse JSON formats render them as ``null`` by default;
                            the ``output_format_json_quote_denormals`` setting cannot be
                            requested for read-only-profile users, so the null rendering is
                            accepted rather than rendered inconsistently across users
  String/FixedString         JSON string (server-rendered; result data must be valid UTF-8,
                            otherwise the run fails closed)
  Date/DateTime/UUID/Enum/IP documented ISO-8601/plain strings (exact server text)
  JSON type                  nested JSON value
  Array/Map/Tuple            JSON array/object/array with recursive server rendering
  unknown families           fail closed on values that cannot be converted deliberately

Read-only posture, defense in depth:

1. Statement gate: the query must be a single statement whose operative keyword is in a
   read-only set (``SELECT``/``SHOW``/``DESCRIBE``/``EXISTS``/``EXPLAIN``, or ``WITH``
   followed by CTE definitions and then ``SELECT``), verified before any server access.
2. Server-side settings: ``readonly=1`` and ``max_execution_time`` are injected per request
   when the connected user's server-reported ``readonly`` level is 0. Users with a
   read-only profile (level >= 1) cannot change settings at all, so injecting would fail
   their queries; their own profile enforces the posture.
3. At-most-once execution: the dedicated client disables query retries, and the user query
   is never wrapped, probed, or re-executed.

Cancellation: the HTTP response is always closed when a run finishes, fails, or is
abandoned; closing (never draining) the socket lets the server cancel the query when
``readonly > 0`` and ``cancel_http_readonly_queries_on_client_close`` is in effect
(clickhouse-connect requests that setting by default when the user's profile allows it).
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Protocol

import clickhouse_connect.driver.exceptions as clickhouse_errors
import urllib3.exceptions
from pydantic import ValidationError

from datadog_checks.base.utils import remote_queries as rq

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
# purpose: they need harness-created tables (Postgres ``cities``/``remote_query_identity``);
# hostName()/currentUser()/version() prove the matched server without any fixture.
REMOTE_QUERY_SEED_QUERY = 'SELECT 1 AS value'
REMOTE_QUERY_IDENTITY_QUERY = 'SELECT hostName() AS host, currentUser() AS user, version() AS version'
# Binary-sensitive but valid-UTF-8 payload: a NUL byte followed by ASCII text. Real servers
# render the NUL as ``\u0000`` in the stream format, so the row is valid JSON, the pinned
# value contract accepts it, and the page preserves the payload exactly. A non-UTF-8 payload
# (such as ``unhex('00ff80')``) is rejected by the value contract by design, so it cannot
# appear on the allowlist.
REMOTE_QUERY_BINARY_QUERY = "SELECT unhex('006162') AS payload"
# The pinned proof payload sizes in bytes: 1, 2, 4, 8, 16, and 32 MiB.
REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES = (1048576, 2097152, 4194304, 8388608, 16777216, 33554432)


def _proof_payload_query(size_bytes: int) -> str:
    """Build the single-row proof query producing exactly ``size_bytes`` payload bytes.

    Every repeat() count must stay within the server's hard 1,000,000 cap (see
    REMOTE_QUERY_REPEAT_CAP), so a payload of ``size_bytes`` is the concatenation of
    ``size_bytes // 1,000,000`` million-byte parts and one remainder part when the size is
    not a multiple of the cap. The construction is a pure function of ``size_bytes``, so the
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
    """One described result field: its column name, ClickHouse type string, and type family."""

    name: str
    vendor_data_type: str
    family: str


@dataclass(frozen=True)
class StaticClickhouseCheckRegistry:
    checks: Sequence['ClickhouseCheck']

    def iter_clickhouse_checks(self) -> Iterable['ClickhouseCheck']:
        return iter(self.checks)


class ClickhouseCheckRegistry(Protocol):
    def iter_clickhouse_checks(self) -> Iterable['ClickhouseCheck']: ...


class ClickhouseClient(Protocol):
    """The dedicated per-run client. Only the surface the producer uses is typed."""

    server_settings: Mapping[str, Any]

    def raw_stream(
        self, query: str, settings: Mapping[str, Any] | None = None, fmt: str | None = None
    ) -> StreamSource: ...

    def close(self) -> None: ...


class StreamSource(Protocol):
    """A readable, closeable byte stream (urllib3 HTTPResponse from ``raw_stream``)."""

    def read(self, amount: int) -> bytes: ...

    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# Statement gate: one read-only statement, verified client-side before any server access
# ---------------------------------------------------------------------------

REMOTE_QUERY_READ_ONLY_STATEMENTS = frozenset(('select', 'show', 'describe', 'desc', 'exists', 'explain'))


class StatementScanner:
    """Comment/string-aware scanner over one ClickHouse statement.

    Skips whitespace, ``--`` line comments, and (nested) ``/* */`` block comments, and treats
    single-quoted strings (backslash escapes and doubled quotes), double-quoted strings, and
    backtick identifiers as single tokens. An unterminated string or comment leaves
    ``terminated`` false so the caller can fail closed.
    """

    def __init__(self, text: str):
        self._text = text
        self._position = 0
        self.terminated = True

    def _skip_trivia(self) -> None:
        """Advance past whitespace and comments so the scanner sits on the next token."""
        text, length = self._text, len(self._text)
        while self._position < length:
            char = text[self._position]
            if char.isspace():
                self._position += 1
            elif char == '-' and text.startswith('--', self._position):
                newline = text.find('\n', self._position)
                self._position = length if newline < 0 else newline + 1
            elif char == '/' and text.startswith('/*', self._position):
                self._position = self._skip_block_comment(self._position)
            else:
                return

    def _skip_block_comment(self, start: int) -> int:
        """Return the position just past a block comment, handling nesting.

        ClickHouse nests block comments one level deep (its parser's own limit).
        """
        text = self._text
        position = start + 2
        while position < len(text):
            if text.startswith('*/', position):
                return position + 2
            if text.startswith('/*', position):
                end = self._skip_block_comment(position)
                if end == position:
                    break
                position = end
                continue
            position += 1
        self.terminated = False
        return len(text)

    def _skip_quoted(self) -> None:
        """Skip a quoted token at the scanner position: ``'...'``, ``"..."``, or ```...```."""
        text = self._text
        quote = text[self._position]
        position = self._position + 1
        while position < len(text):
            char = text[position]
            if char == '\\' and quote != '`':
                position += 2
                continue
            if char == quote:
                # A doubled quote inside the token is an escape, not the terminator.
                if position + 1 < len(text) and text[position + 1] == quote:
                    position += 2
                    continue
                self._position = position + 1
                return
            position += 1
        self.terminated = False
        self._position = len(text)

    def at_end(self) -> bool:
        self._skip_trivia()
        return self._position >= len(self._text)

    def peek(self) -> str | None:
        self._skip_trivia()
        if self._position >= len(self._text):
            return None
        return self._text[self._position]

    def consume(self) -> None:
        """Consume one raw character at the scanner position (after trivia)."""
        self._skip_trivia()
        if self._position < len(self._text):
            self._position += 1

    def keyword(self) -> str | None:
        """Read an identifier/keyword at the scanner position, or None if none starts here."""
        self._skip_trivia()
        text = self._text
        position = self._position
        if position >= len(text):
            return None
        if not (text[position].isalpha() or text[position] == '_'):
            return None
        end = position + 1
        while end < len(text) and (text[end].isalnum() or text[end] == '_'):
            end += 1
        self._position = end
        return text[position:end]

    def quoted(self) -> bool:
        """Skip a quoted token if one starts here, leaving the scanner just past it."""
        if self.peek() in ('\'', '"', '`'):
            self._skip_quoted()
            return self.terminated
        return False

    def balanced_group(self) -> bool:
        """Skip a balanced parenthesis group starting at the current ``(`` position."""
        if self.peek() != '(':
            return False
        text = self._text
        depth = 0
        while self._position < len(text):
            char = text[self._position]
            if char == '(':
                depth += 1
                self._position += 1
            elif char == ')':
                depth -= 1
                self._position += 1
                if depth == 0:
                    return True
            elif char in '\'"`':
                self._skip_quoted()
                if not self.terminated:
                    return False
            elif char == '/' and text.startswith('/*', self._position):
                self._position = self._skip_block_comment(self._position)
            elif char == '-' and text.startswith('--', self._position):
                newline = text.find('\n', self._position)
                self._position = len(text) if newline < 0 else newline + 1
            else:
                self._position += 1
        self.terminated = False
        return False

    def expression_until_keyword(self, keyword: str) -> bool:
        """Scan an expression up to (and consuming) a top-level ``keyword``.

        Anything that is not an identifier/keyword token (numbers, operators) is consumed
        one character at a time; parentheses, strings, and comments are skipped whole, so
        the keyword only matches at the top level of the expression.
        """
        target = keyword.lower()
        while True:
            if self.peek() is None:
                return False
            if self.peek() == '(':
                if not self.balanced_group():
                    return False
                continue
            if self.peek() in ('\'', '"', '`'):
                if not self.quoted():
                    return False
                continue
            token = self.keyword()
            if token is not None:
                if token.lower() == target:
                    return True
                continue
            # A non-identifier character: number, operator, punctuation. Consume it and
            # keep scanning; no trivia or nesting hides inside a single such character.
            self.consume()

    def scan_statements(self) -> bool:
        """True when the text holds exactly one statement (no non-trailing semicolon)."""
        self._position = 0
        while self._position < len(self._text):
            char = self._text[self._position]
            if char in '\'"`':
                self._skip_quoted()
            elif char == '/' and self._text.startswith('/*', self._position):
                self._position = self._skip_block_comment(self._position)
            elif char == '-' and self._text.startswith('--', self._position):
                newline = self._text.find('\n', self._position)
                self._position = len(self._text) if newline < 0 else newline + 1
            elif char == ';':
                self._position += 1
                if not self.at_end():
                    return False
            else:
                self._position += 1
        return True

    def rewind(self) -> None:
        self._position = 0
        self.terminated = True


def validate_read_only_statement(query: str) -> None:
    """Fail closed unless the query is a single statement with a read-only operative keyword.

    ClickHouse HTTP executes one statement per request, so the server already rejects a
    second statement; this gate rejects mutations before any server access. ``WITH`` is
    allowed only when its CTE definitions are followed by ``SELECT`` because ClickHouse
    also accepts ``WITH ... INSERT INTO ... SELECT``.
    """
    scanner = StatementScanner(query)
    if not scanner.scan_statements() or not scanner.terminated:
        raise rq.RemoteQueryFailure(
            'invalid_request', 'Invalid remote query request: query must be a single read-only statement.'
        )
    scanner.rewind()
    keyword = (scanner.keyword() or '').lower()
    if keyword == 'with':
        # ``WITH`` itself is not read-only (ClickHouse also accepts WITH ... INSERT); the
        # CTE definitions must resolve to an operative SELECT.
        keyword = 'select' if _validate_with_select(scanner) else ''
    if keyword not in REMOTE_QUERY_READ_ONLY_STATEMENTS:
        raise rq.RemoteQueryFailure(
            'invalid_request', 'Invalid remote query request: query is not a read-only statement.'
        )


def _validate_with_select(scanner: StatementScanner) -> bool:
    """True when a leading ``WITH`` clause is followed by an operative ``SELECT``.

    Each definition is ``<name-or-expression> AS (<query>)``, optionally with a
    ``(<columns>)`` list after the name, or a bare alias after a scalar expression;
    definitions are separated by commas. The scanner stays shallow on purpose: anything
    unexpected makes the gate reject rather than guess.
    """
    while True:
        if not scanner.expression_until_keyword('as'):
            return False
        if scanner.peek() == '(':
            # Named CTE form: ``name (columns) AS (query)`` or ``name AS (query)``.
            if not scanner.balanced_group():
                return False
        else:
            # Scalar CTE form: ``WITH <expression> AS <alias>``.
            if scanner.keyword() is None:
                return False
        if scanner.peek() != ',':
            break
        # Consume the comma separator and continue with the next CTE definition.
        scanner.consume()
    return (scanner.keyword() or '').lower() == 'select'


# ---------------------------------------------------------------------------
# ClickHouse value contract (pinned, cross-language)
#
# Rows arrive server-rendered as JSON arrays, so string quoting, NULLs, booleans, and
# composite types (Array/Map/Tuple/JSON) are already valid JSON; the encoder below only
# re-serializes values into the row object and keeps exact numeric text. Rows are parsed
# with ``parse_float=Decimal`` so float/decimal text never round-trips through a binary
# float. Servers that quote 64-bit+ integers or decimals (ClickHouse JSON output settings)
# deliver them as JSON strings; the declared column type normalizes those back to exact
# JSON numbers.

# A JSON number per RFC 8259: no leading zeros, optional fraction and exponent. Server
# numeric text must already satisfy this; anything else fails closed.

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


def normalize_typed_value(family: str, value: Any) -> Any:
    """Normalize server value spellings that depend on server JSON output settings.

    Only type-known numeric/bool families are touched, so a String column holding digits
    stays a JSON string. Anything unexpected is left for the encoder to fail closed on.
    """
    if family == 'integer' and isinstance(value, str):
        if re.fullmatch(r'[+-]?[0-9]+', value):
            return int(value)
        return value
    if family in ('decimal', 'float') and isinstance(value, str):
        if rq.JSON_NUMBER_PATTERN.match(value):
            return Decimal(value)
        return value
    if family == 'bool':
        if isinstance(value, int) and not isinstance(value, bool):
            if value in (0, 1):
                return bool(value)
            return value
        if isinstance(value, str) and value in ('true', 'false'):
            return value == 'true'
        return value
    return value


def _encode_json_value(out: bytearray, value: Any) -> None:
    """Encode one normalized ClickHouse value into ``out`` as JSON bytes.

    Values come from ``json.loads`` on a server-rendered row line, so only JSON-native types
    plus ``Decimal`` (via ``parse_float``) appear; anything unrecognized fails closed.
    """
    if value is None:
        out += b'null'
    elif isinstance(value, bool):
        out += b'true' if value else b'false'
    elif isinstance(value, int):
        rq.encode_raw_number_text(out, str(value))
    elif isinstance(value, Decimal):
        rq.encode_decimal(out, value)
    elif isinstance(value, float):
        rq.encode_float(out, value)
    elif isinstance(value, str):
        out += json.dumps(value).encode('utf-8')
    elif isinstance(value, (list, tuple)):
        out += b'['
        for index, item in enumerate(value):
            if index:
                out += b','
            _encode_json_value(out, item)
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
            _encode_json_value(out, item)
        out += b'}'
    else:
        raise rq.RemoteQueryFailure(
            'unsupported_value',
            'ClickHouse value of type {} has no conversion in the JSON contract.'.format(type(value).__name__),
        )


def encode_row(values: Sequence[Any], columns: Sequence[ResultColumn], out: bytearray) -> None:
    """Encode one result row as a JSON object keyed by result-column name."""
    if len(values) != len(columns):
        raise rq.RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
    out += b'{'
    for index, (column, value) in enumerate(zip(columns, values)):
        if index:
            out += b','
        out += json.dumps(column.name).encode('utf-8')
        out += b':'
        _encode_json_value(out, normalize_typed_value(column.family, value))
    out += b'}'


# ---------------------------------------------------------------------------
# Result header and schema
# ---------------------------------------------------------------------------


def _parse_json_line(line: bytes) -> Any:
    try:
        # parse_float=Decimal keeps float/decimal text exact: no binary-float round-trip.
        return json.loads(line, parse_float=Decimal)
    except (UnicodeDecodeError, ValueError):
        # Result data must be valid UTF-8 JSON; never echo the offending line.
        raise rq.RemoteQueryFailure('query_failed', 'The result stream carried a row that is not valid JSON.') from None


def _parse_header_row(line: bytes, expected: str) -> list[str]:
    parsed = _parse_json_line(line)
    if not isinstance(parsed, list) or not parsed or not all(isinstance(entry, str) and entry for entry in parsed):
        raise rq.RemoteQueryFailure(
            'query_failed', 'The result stream did not carry usable {} in its header row.'.format(expected)
        )
    return parsed


def build_columns(names: Sequence[str], types: Sequence[str]) -> list[ResultColumn]:
    if len(names) != len(types):
        raise rq.RemoteQueryFailure('query_failed', 'The result stream header rows do not agree on column count.')
    return [
        ResultColumn(name=name, vendor_data_type=vendor_data_type, family=type_family(vendor_data_type))
        for name, vendor_data_type in zip(names, types)
    ]


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


def build_schema_json(
    columns: Sequence[ResultColumn], delivery: rq.RemoteQueryResultDelivery, agent_hostname: str
) -> bytes:
    """Build the ordered schema entries, rejecting oversize schemas.

    The encoded schema repeats in every page, so it must fit both ``maxSchemaBytes`` and the
    smallest valid page frame; both are enforced before any row data is written.
    """
    entries = [{'column_name': column.name, 'vendor_data_type': column.vendor_data_type} for column in columns]
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
            batch_index=0,
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


# Slack for header-row buffering: the header lines carry names and type strings whose
# byte accounting differs slightly from the schema/row budgets that justify the bound.
REMOTE_QUERY_HEADER_LINE_SLACK = 1024


def row_line_ceiling(columns: Sequence[ResultColumn], max_row_bytes: int) -> int:
    """A line-length bound past which the encoded row cannot fit ``max_row_bytes``.

    The encoded row is the server line plus the column-name overhead, minus at most a few
    bytes per column when a quoted numeric spelling is normalized back to a number. The
    exact ``maxRowBytes`` check still runs on the encoded row; this ceiling is the buffer
    bound, so a row line larger than any compliant row fails the run during the read
    instead of being buffered whole.
    """
    name_overhead = sum(len(json.dumps(column.name)) + 1 for column in columns) + 2
    ceiling = max_row_bytes - name_overhead + 4 * len(columns) + 8
    return max(64, ceiling)


class LineBoundTracker:
    """The maximum buffered line size for each line of the result stream.

    Line 0 is the column-name header row, line 1 the column-type header row, and lines 2+
    are data rows. The bound is enforced while bytes accumulate (a row line may exceed a
    normal read chunk), so a single unterminated or oversized line fails the run
    deterministically instead of growing the buffer without limit; nothing is ever
    truncated silently.

    Header rows are bounded by the larger of the two byte budgets: with ``includeSchema``
    the encoded schema (names plus types) must fit ``maxSchemaBytes`` anyway, and without it
    the column names must repeat inside every ``maxRowBytes``-bounded row. An exotic
    oversized type string on a schema-less run fails closed here rather than buffering it.
    Request validation caps both budgets at ``maxFileBytes``, so the header bound stays
    within the platform page ceiling plus the fixed header slack.
    """

    def __init__(self, limits: rq.RemoteQueryUploadLimits):
        self._header_bound = max(limits.max_schema_bytes, limits.max_row_bytes) + REMOTE_QUERY_HEADER_LINE_SLACK
        self._row_bound = self._header_bound
        self._max_row_bytes = limits.max_row_bytes

    def for_index(self, index: int) -> int:
        return self._header_bound if index < 2 else self._row_bound

    def bind_columns(self, columns: Sequence[ResultColumn]) -> None:
        """Tighten the data-row bound once the column names are known."""
        self._row_bound = row_line_ceiling(columns, self._max_row_bytes)

    def too_large_failure(self, index: int, buffered: int) -> rq.RemoteQueryFailure:
        if index < 2:
            return rq.RemoteQueryFailure('query_failed', 'The result stream header row exceeded the allowed size.')
        return rq.RemoteQueryFailure(
            'row_too_large',
            'A single row exceeds maxRowBytes ({} buffered bytes; the limit is {} bytes).'.format(
                buffered, self._max_row_bytes
            ),
        )


# ---------------------------------------------------------------------------
# Producer: one validated read-only query execution through a dedicated streaming client
# ---------------------------------------------------------------------------


def resolve_readonly_settings(client: ClickhouseClient, timeout_ms: int) -> dict[str, Any]:
    """Per-request settings enforcing the read-only posture and a server-side timeout.

    ClickHouse ``readonly`` levels: 0 no restrictions, 1 read-only with settings frozen,
    2 read-only with settings changes allowed (except ``readonly`` itself). The client's
    server-settings discovery reports the connected user's current level:

    - level 0: inject ``readonly=1`` (which also activates cancel-on-close, see the module
      docstring) and a server-side ``max_execution_time`` kill for runaway execution;
    - level >= 1: settings cannot be changed for that user, so injecting would fail their
      queries; the profile's own read-only posture already applies.
    - unknown (no discovery data): inject nothing; the statement gate and, for modern
      servers, the profile remain the posture. The client would also refuse to send an
      unknown setting (its validation fails closed), so injecting is not an option.
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
    request: rq.RemoteQueryRequest,
    clickhouse_client: ClickhouseClient,
    creds: rq.UploadCredentials,
    client: rq.UploadClient,
    agent_hostname: str,
    guard: Callable[[], None],
    stats: rq.RemoteQueryRunStats,
) -> dict[str, Any]:
    """Stream the query result into bounded JSON pages and return the run receipt."""
    delivery = request.result_delivery
    limits = delivery.limits
    settings = resolve_readonly_settings(clickhouse_client, limits.timeout_ms)
    # The user query is passed verbatim; the client appends the FORMAT clause.
    stream = clickhouse_client.raw_stream(request.query, settings=settings, fmt=REMOTE_QUERY_STREAM_FORMAT)
    try:
        bounds = LineBoundTracker(limits)
        lines = iter_stream_lines(stream, guard, bounds)
        try:
            names_line = next(lines)
            types_line = next(lines)
        except StopIteration:
            raise rq.RemoteQueryFailure(
                'query_failed', 'The result stream did not carry the column name and type header rows.'
            ) from None
        columns = build_columns(
            _parse_header_row(names_line, 'column names'), _parse_header_row(types_line, 'column types')
        )
        validate_columns(columns, limits.max_columns)
        # Now that the column names are known, data-row lines are bounded by the row budget.
        bounds.bind_columns(columns)
        schema_json = None
        if request.include_schema:
            schema_json = build_schema_json(columns, delivery, agent_hostname)

        # The executing check's Agent-reported hostname: the stamp must match the
        # agent node identity Fleet reports, never socket.gethostname().
        writer = rq.PageWriter(delivery, creds, client, agent_hostname, schema_json, guard, stats)
        try:
            guard()
            for line in lines:
                guard()
                values = _parse_json_line(line)
                if not isinstance(values, list):
                    raise rq.RemoteQueryFailure('query_failed', 'A result row was not a JSON array.')
                row_buffer = bytearray()
                encode_row(values, columns, row_buffer)
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
            # Release the page even if the response stream or row conversion fails.
            writer.discard()
    finally:
        # Always close (never drain) the response: closing the socket is what lets the server
        # cancel an abandoned read-only query (see the module docstring).
        try:
            stream.close()
        except Exception:
            LOGGER.debug('Unable to close the remote query response stream', exc_info=True)


def produce_remote_query(
    request: rq.RemoteQueryRequest,
    check: 'ClickhouseCheck',
    creds: rq.UploadCredentials,
    client: rq.UploadClient,
    started_at: float,
    stats: rq.RemoteQueryRunStats,
    clickhouse_client_factory: Callable[['ClickhouseCheck', rq.RemoteQueryUploadLimits], ClickhouseClient]
    | None = None,
) -> dict[str, Any]:
    """Execute the validated query once and return the compact run receipt.

    The query runs exactly once, through a dedicated client whose query retries are
    disabled; it is never wrapped in a probe and never executed twice. Row lines are read
    from the streamed response incrementally and encoded one row at a time.
    """
    delivery = request.result_delivery
    limits = delivery.limits
    deadline = started_at + limits.timeout_ms / 1000

    def guard() -> None:
        rq.raise_if_timed_out(deadline)
        rq.raise_if_cancelled(check)

    clickhouse_client = None
    try:
        factory = clickhouse_client_factory if clickhouse_client_factory is not None else _default_client_factory
        try:
            clickhouse_client = factory(check, limits)
        except rq.RemoteQueryFailure:
            raise
        except Exception:
            # A connection-level failure: the matched instance could not be reached or refused
            # the request. Never echo the underlying text (it can quote identifiers or
            # credentials embedded in connection error strings).
            LOGGER.debug('Remote query client creation failed', exc_info=True)
            raise rq.RemoteQueryFailure(
                'target_unavailable', 'The matched ClickHouse instance is not reachable for remote queries.'
            ) from None
        try:
            receipt = _run_streamed_query(request, clickhouse_client, creds, client, check.hostname, guard, stats)
        except rq.RemoteQueryFailure:
            raise
        except clickhouse_errors.OperationalError:
            # A transport-level failure: the request never got a usable server response.
            LOGGER.debug('Remote query transport failed', exc_info=True)
            raise rq.RemoteQueryFailure(
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
            LOGGER.debug('Remote query stream failed mid-stream', exc_info=True)
            raise rq.RemoteQueryFailure(
                'timeout',
                'The remote query stream was interrupted (server cancellation or connection failure).',
                True,
            ) from None
        except clickhouse_errors.DatabaseError:
            # The server answered with an error (bad SQL, missing table, permissions), or
            # the client refused a request-level setting. The instance is reachable, the
            # run is not. Never echo the underlying message: it can quote query text.
            LOGGER.debug('Remote query rejected by the server', exc_info=True)
            raise rq.RemoteQueryFailure('query_failed', 'Remote query execution failed.') from None
        except Exception:
            LOGGER.exception('Remote query execution failed')
            raise rq.RemoteQueryFailure('query_failed', 'Remote query execution failed.') from None
        return receipt
    finally:
        # The streamed response is owned and closed by _run_streamed_query; the client owns
        # no pool of its own, so closing it is a no-op for the shared connection pool.
        if clickhouse_client is not None:
            try:
                clickhouse_client.close()
            except Exception:
                LOGGER.debug('Unable to close the remote query client', exc_info=True)


def _default_client_factory(check: 'ClickhouseCheck', limits: rq.RemoteQueryUploadLimits) -> ClickhouseClient:
    """Create the per-run client from the matched check.

    The read timeout bounds a single silent read, so it is derived from the run deadline
    rather than the check's own (short) ``read_timeout``; the client-side deadline guard
    remains the authoritative cumulative bound.
    """
    factory = getattr(check, 'create_remote_query_client', None)
    if factory is None:
        raise rq.RemoteQueryFailure(
            'target_unavailable', 'The matched ClickHouse check cannot create a remote query client.'
        )
    return factory(send_receive_timeout=max(1, math.ceil(limits.timeout_ms / 1000)))


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def _resolve_matches(target: rq.RemoteQueryTarget, checks: Iterable['ClickhouseCheck']) -> list['ClickhouseCheck']:
    if target.database_instance is not None:
        return [check for check in checks if getattr(check, 'database_identifier', None) == target.database_instance]
    return [check for check in checks if _target_from_check(check) == target]


def _target_from_check(check: 'ClickhouseCheck') -> rq.RemoteQueryTarget | None:
    config = getattr(check, '_config', None)
    if config is None:
        return None

    try:
        # The wire contract is {host, port, dbname}; the ClickHouse instance config spells
        # them {server, port, db}.
        return rq.RemoteQueryTarget(host=config.server, port=config.port, dbname=config.db)
    except (AttributeError, ValidationError):
        return None


# ---------------------------------------------------------------------------
# Query allowlist
# ---------------------------------------------------------------------------


def _is_query_allowed(query: str) -> bool:
    return not rq.is_query_allowlist_enabled() or query in REMOTE_QUERY_QUERY_ALLOWLIST


# ---------------------------------------------------------------------------
# Event entry points
# ---------------------------------------------------------------------------


def execute_agent_rpc_stream_copy(
    request_json: str | bytes | bytearray, check: 'ClickhouseCheck', emit: rq.RemoteQueryEmit
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
    check: 'ClickhouseCheck',
    emit: rq.RemoteQueryEmit,
    http_client: rq.UploadClient | None = None,
    clickhouse_client_factory: Callable[['ClickhouseCheck', rq.RemoteQueryUploadLimits], ClickhouseClient]
    | None = None,
) -> None:
    """Drive the producer with the default (or injected) upload client and emit its events."""
    events = iter_agent_rpc_stream_events(
        request, StaticClickhouseCheckRegistry([check]), http_client, clickhouse_client_factory
    )
    try:
        for event in events:
            rq.emit_event(emit, event)
    except BaseException:
        events.close()
        raise


def iter_agent_rpc_stream_events(
    request: Any,
    registry: ClickhouseCheckRegistry,
    http_client: rq.UploadClient | None = None,
    clickhouse_client_factory: Callable[['ClickhouseCheck', rq.RemoteQueryUploadLimits], ClickhouseClient]
    | None = None,
) -> Iterator[rq.RemoteQueryEvent]:
    """Yield producer events for unit tests and callback adaptation."""
    started_at = time.monotonic()
    try:
        parsed_request = rq.RemoteQueryRequest.model_validate(request)
    except ValidationError as e:
        yield rq.failed_event('invalid_request', rq.validation_message(e), elapsed_ms=rq.elapsed_ms(started_at))
        return

    try:
        validate_read_only_statement(parsed_request.query)
    except rq.RemoteQueryFailure as e:
        yield rq.failed_event(e.code, e.message, elapsed_ms=rq.elapsed_ms(started_at))
        return

    if not _is_query_allowed(parsed_request.query):
        yield rq.failed_event(
            'invalid_request',
            'Invalid remote query request: query is not allowlisted.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    target = parsed_request.target
    matches = _resolve_matches(target, registry.iter_clickhouse_checks())
    LOGGER.debug('Remote query target match count: %d', len(matches))
    if not matches:
        yield rq.failed_event(
            'target_not_found',
            'No loaded ClickHouse integration instance matched target selector.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return
    if len(matches) > 1:
        yield rq.failed_event(
            'target_ambiguous',
            'More than one loaded ClickHouse integration instance matched target selector.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    check = matches[0]
    creds = rq.resolve_upload_credentials(parsed_request.result_delivery)
    if not creds.api_key or not creds.app_key:
        yield rq.failed_event(
            'credentials_unavailable',
            'Remote query upload requires api_key and app_key to be configured on the Agent.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    if getattr(check, '_pool_manager', None) is None:
        yield rq.failed_event(
            'target_unavailable',
            'Matched ClickHouse check HTTP connection pool is unavailable.',
            elapsed_ms=rq.elapsed_ms(started_at),
        )
        return

    client = http_client if http_client is not None else rq.RequestsUploadClient()
    stats = rq.RemoteQueryRunStats()
    yield rq.RemoteQueryEvent('metadata', rq.started_metadata(parsed_request))

    try:
        receipt = produce_remote_query(
            parsed_request,
            check,
            creds,
            client,
            started_at,
            stats,
            clickhouse_client_factory=clickhouse_client_factory,
        )
    except rq.RemoteQueryFailure as e:
        rq.safe_abort(client, creds)
        yield rq.failed_event(e.code, e.message, retryable=e.retryable, stats=rq.stats_metadata(stats, started_at))
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
