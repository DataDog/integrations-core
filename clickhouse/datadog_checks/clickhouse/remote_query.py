# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Remote query JSON page producer for the ClickHouse integration.

Executes one validated read-only query through a dedicated ``clickhouse-connect`` client,
streams the server-rendered rows with bounded memory, normalizes ClickHouse values into
the pinned cross-language JSON contract, splits the rows into byte-bounded JSON page files,
and streams each page's bytes as multipart parts directly to its-agent-intake over HTTP.
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

import hashlib
import json
import logging
import math
import re
import time
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, Protocol

import clickhouse_connect.driver.exceptions as clickhouse_errors
import urllib3.exceptions
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
    from datadog_checks.clickhouse import ClickhouseCheck

LOGGER = logging.getLogger(__name__)

REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY = 'remote_queries.execute.enable_query_allowlist'
REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES = frozenset(('false', 'no', '0', 'n', 'off'))
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

# Server-owned maximums. The backend selects/clamps every injected limit; the integration only
# fails closed when an injected instruction exceeds a known platform ceiling, which would
# indicate a backend/integration contract version mismatch.
REMOTE_QUERY_UPLOAD_MAX_PART_BYTES = 128 * 1024 * 1024
REMOTE_QUERY_UPLOAD_MAX_FILE_BYTES = 128 * 1024 * 1024
REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES = 10 * 1024 * 1024 * 1024
REMOTE_QUERY_DEFAULT_TIMEOUT_MS = 30_000

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

# One-stream row format: the first line is the column names, the second the ClickHouse type
# strings, then one JSON array of server-rendered values per line. Line breaks only occur at
# row boundaries (string values are JSON-escaped by the server), so bounded line reads are
# unambiguous.
REMOTE_QUERY_STREAM_FORMAT = 'JSONCompactEachRowWithNamesAndTypes'
# Stream reads are bounded to this chunk size; nothing larger is buffered per read.
REMOTE_QUERY_STREAM_CHUNK_BYTES = 256 * 1024


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
        if self.max_schema_bytes > self.max_file_bytes:
            raise ValueError('maxSchemaBytes must not exceed maxFileBytes: the schema must fit inside one page')
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
    """One described result field: its column name, ClickHouse type string, and type family."""

    name: str
    vendor_data_type: str
    family: str


@dataclass
class RemoteQueryRunStats:
    """Mutable run accounting shared with the page writer so failures can report partials."""

    rows_emitted: int = 0
    pages_emitted: int = 0
    parts_emitted: int = 0
    bytes_emitted: int = 0


@dataclass(frozen=True)
class StaticClickhouseCheckRegistry:
    checks: Sequence['ClickhouseCheck']

    def iter_clickhouse_checks(self) -> Iterable['ClickhouseCheck']:
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
        raise RemoteQueryFailure(
            'invalid_request', 'Invalid remote query request: query must be a single read-only statement.'
        )
    scanner.rewind()
    keyword = (scanner.keyword() or '').lower()
    if keyword == 'with':
        # ``WITH`` itself is not read-only (ClickHouse also accepts WITH ... INSERT); the
        # CTE definitions must resolve to an operative SELECT.
        keyword = 'select' if _validate_with_select(scanner) else ''
    if keyword not in REMOTE_QUERY_READ_ONLY_STATEMENTS:
        raise RemoteQueryFailure('invalid_request', 'Invalid remote query request: query is not a read-only statement.')


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
_JSON_NUMBER_PATTERN = re.compile(r'\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\Z')
_NON_FINITE_NUMERIC_TEXT = frozenset(('NaN', 'Infinity', '-Infinity'))

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
        if _JSON_NUMBER_PATTERN.match(value):
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


def _encode_raw_number_text(out: bytearray, text: str) -> None:
    if not _JSON_NUMBER_PATTERN.match(text):
        raise RemoteQueryFailure(
            'unsupported_value', 'ClickHouse sent numeric text {!r} that is not a JSON number.'.format(text)
        )
    out += text.encode('utf-8')


def _encode_non_finite_text(out: bytearray, text: str) -> None:
    out += json.dumps(text).encode('utf-8')


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
        _encode_raw_number_text(out, str(value))
    elif isinstance(value, Decimal):
        _encode_decimal(out, value)
    elif isinstance(value, float):
        _encode_float(out, value)
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
                raise RemoteQueryFailure('unsupported_value', 'JSON object keys must be strings.')
            if not first:
                out += b','
            first = False
            out += json.dumps(key).encode('utf-8')
            out += b':'
            _encode_json_value(out, item)
        out += b'}'
    else:
        raise RemoteQueryFailure(
            'unsupported_value',
            'ClickHouse value of type {} has no conversion in the JSON contract.'.format(type(value).__name__),
        )


def encode_row(values: Sequence[Any], columns: Sequence[ResultColumn], out: bytearray) -> None:
    """Encode one result row as a JSON object keyed by result-column name."""
    if len(values) != len(columns):
        raise RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
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
        raise RemoteQueryFailure('query_failed', 'The result stream carried a row that is not valid JSON.') from None


def _parse_header_row(line: bytes, expected: str) -> list[str]:
    parsed = _parse_json_line(line)
    if not isinstance(parsed, list) or not parsed or not all(isinstance(entry, str) and entry for entry in parsed):
        raise RemoteQueryFailure(
            'query_failed', 'The result stream did not carry usable {} in its header row.'.format(expected)
        )
    return parsed


def build_columns(names: Sequence[str], types: Sequence[str]) -> list[ResultColumn]:
    if len(names) != len(types):
        raise RemoteQueryFailure('query_failed', 'The result stream header rows do not agree on column count.')
    return [
        ResultColumn(name=name, vendor_data_type=vendor_data_type, family=type_family(vendor_data_type))
        for name, vendor_data_type in zip(names, types)
    ]


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


def build_schema_json(columns: Sequence[ResultColumn], delivery: RemoteQueryResultDelivery) -> bytes:
    """Build the ordered schema entries, rejecting oversize schemas.

    The encoded schema repeats in every page, so it must fit both ``maxSchemaBytes`` and the
    smallest valid page frame; both are enforced before any row data is written.
    """
    entries = [{'column_name': column.name, 'vendor_data_type': column.vendor_data_type} for column in columns]
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

    def __init__(self, limits: RemoteQueryUploadLimits):
        self._header_bound = max(limits.max_schema_bytes, limits.max_row_bytes) + REMOTE_QUERY_HEADER_LINE_SLACK
        self._row_bound = self._header_bound
        self._max_row_bytes = limits.max_row_bytes

    def for_index(self, index: int) -> int:
        return self._header_bound if index < 2 else self._row_bound

    def bind_columns(self, columns: Sequence[ResultColumn]) -> None:
        """Tighten the data-row bound once the column names are known."""
        self._row_bound = row_line_ceiling(columns, self._max_row_bytes)

    def too_large_failure(self, index: int, buffered: int) -> RemoteQueryFailure:
        if index < 2:
            return RemoteQueryFailure('query_failed', 'The result stream header row exceeded the allowed size.')
        return RemoteQueryFailure(
            'row_too_large',
            'A single row exceeds maxRowBytes ({} buffered bytes; the limit is {} bytes).'.format(
                buffered, self._max_row_bytes
            ),
        )


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
    request: RemoteQueryRequest,
    clickhouse_client: ClickhouseClient,
    creds: UploadCredentials,
    client: UploadClient,
    guard: Callable[[], None],
    stats: RemoteQueryRunStats,
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
            raise RemoteQueryFailure(
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
            schema_json = build_schema_json(columns, delivery)

        writer = PageWriter(delivery, creds, client, schema_json, guard, stats)
        guard()
        for line in lines:
            guard()
            values = _parse_json_line(line)
            if not isinstance(values, list):
                raise RemoteQueryFailure('query_failed', 'A result row was not a JSON array.')
            row_buffer = bytearray()
            encode_row(values, columns, row_buffer)
            if len(row_buffer) > limits.max_row_bytes:
                raise RemoteQueryFailure(
                    'row_too_large',
                    'A single row exceeds maxRowBytes ({} > {} bytes).'.format(len(row_buffer), limits.max_row_bytes),
                )
            writer.add_row(bytes(row_buffer))
        return writer.finish()
    finally:
        # Always close (never drain) the response: closing the socket is what lets the server
        # cancel an abandoned read-only query (see the module docstring).
        try:
            stream.close()
        except Exception:
            LOGGER.debug('Unable to close the remote query response stream', exc_info=True)


def produce_remote_query(
    request: RemoteQueryRequest,
    check: 'ClickhouseCheck',
    creds: UploadCredentials,
    client: UploadClient,
    started_at: float,
    stats: RemoteQueryRunStats,
    clickhouse_client_factory: Callable[['ClickhouseCheck', RemoteQueryUploadLimits], ClickhouseClient] | None = None,
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
        _raise_if_timed_out(deadline)
        _raise_if_cancelled(check)

    clickhouse_client = None
    try:
        factory = clickhouse_client_factory if clickhouse_client_factory is not None else _default_client_factory
        try:
            clickhouse_client = factory(check, limits)
        except RemoteQueryFailure:
            raise
        except Exception:
            # A connection-level failure: the matched instance could not be reached or refused
            # the request. Never echo the underlying text (it can quote identifiers or
            # credentials embedded in connection error strings).
            LOGGER.debug('Remote query client creation failed', exc_info=True)
            raise RemoteQueryFailure(
                'target_unavailable', 'The matched ClickHouse instance is not reachable for remote queries.'
            ) from None
        try:
            receipt = _run_streamed_query(request, clickhouse_client, creds, client, guard, stats)
        except RemoteQueryFailure:
            raise
        except clickhouse_errors.OperationalError:
            # A transport-level failure: the request never got a usable server response.
            LOGGER.debug('Remote query transport failed', exc_info=True)
            raise RemoteQueryFailure(
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
            raise RemoteQueryFailure(
                'timeout',
                'The remote query stream was interrupted (server cancellation or connection failure).',
                True,
            ) from None
        except clickhouse_errors.DatabaseError:
            # The server answered with an error (bad SQL, missing table, permissions), or
            # the client refused a request-level setting. The instance is reachable, the
            # run is not. Never echo the underlying message: it can quote query text.
            LOGGER.debug('Remote query rejected by the server', exc_info=True)
            raise RemoteQueryFailure('query_failed', 'Remote query execution failed.') from None
        except Exception:
            LOGGER.exception('Remote query execution failed')
            raise RemoteQueryFailure('query_failed', 'Remote query execution failed.') from None
        return receipt
    finally:
        # The streamed response is owned and closed by _run_streamed_query; the client owns
        # no pool of its own, so closing it is a no-op for the shared connection pool.
        if clickhouse_client is not None:
            try:
                clickhouse_client.close()
            except Exception:
                LOGGER.debug('Unable to close the remote query client', exc_info=True)


def _default_client_factory(check: 'ClickhouseCheck', limits: RemoteQueryUploadLimits) -> ClickhouseClient:
    """Create the per-run client from the matched check.

    The read timeout bounds a single silent read, so it is derived from the run deadline
    rather than the check's own (short) ``read_timeout``; the client-side deadline guard
    remains the authoritative cumulative bound.
    """
    factory = getattr(check, 'create_remote_query_client', None)
    if factory is None:
        raise RemoteQueryFailure(
            'target_unavailable', 'The matched ClickHouse check cannot create a remote query client.'
        )
    return factory(send_receive_timeout=max(1, math.ceil(limits.timeout_ms / 1000)))


def _raise_if_timed_out(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise RemoteQueryFailure('timeout', 'Remote query exceeded timeoutMs.', retryable=True)


def _raise_if_cancelled(check: 'ClickhouseCheck') -> None:
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


def _resolve_matches(target: RemoteQueryTarget, checks: Iterable['ClickhouseCheck']) -> list['ClickhouseCheck']:
    if target.database_instance is not None:
        return [check for check in checks if getattr(check, 'database_identifier', None) == target.database_instance]
    return [check for check in checks if _target_from_check(check) == target]


def _target_from_check(check: 'ClickhouseCheck') -> RemoteQueryTarget | None:
    config = getattr(check, '_config', None)
    if config is None:
        return None

    try:
        # The wire contract is {host, port, dbname}; the ClickHouse instance config spells
        # them {server, port, db}.
        return RemoteQueryTarget(host=config.server, port=config.port, dbname=config.db)
    except (AttributeError, ValidationError):
        return None


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
    import requests  # lazy: only the upload path needs it

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
    request_json: str | bytes | bytearray, check: 'ClickhouseCheck', emit: RemoteQueryEmit
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
    request: Mapping[str, Any],
    check: 'ClickhouseCheck',
    emit: RemoteQueryEmit,
    http_client: UploadClient | None = None,
    clickhouse_client_factory: Callable[['ClickhouseCheck', RemoteQueryUploadLimits], ClickhouseClient] | None = None,
) -> None:
    """Drive the producer with the default (or injected) upload client and emit its events."""
    events = iter_agent_rpc_stream_events(
        request, StaticClickhouseCheckRegistry([check]), http_client, clickhouse_client_factory
    )
    try:
        for event in events:
            _emit_event(emit, event)
    except BaseException:
        events.close()
        raise


def iter_agent_rpc_stream_events(
    request: Any,
    registry: ClickhouseCheckRegistry,
    http_client: UploadClient | None = None,
    clickhouse_client_factory: Callable[['ClickhouseCheck', RemoteQueryUploadLimits], ClickhouseClient] | None = None,
) -> Iterator[RemoteQueryEvent]:
    """Yield producer events for unit tests and callback adaptation."""
    started_at = time.monotonic()
    try:
        parsed_request = RemoteQueryRequest.model_validate(request)
    except ValidationError as e:
        yield _failed_event('invalid_request', _validation_message(e), elapsed_ms=_elapsed_ms(started_at))
        return

    try:
        validate_read_only_statement(parsed_request.query)
    except RemoteQueryFailure as e:
        yield _failed_event(e.code, e.message, elapsed_ms=_elapsed_ms(started_at))
        return

    if not _is_query_allowed(parsed_request.query):
        yield _failed_event(
            'invalid_request',
            'Invalid remote query request: query is not allowlisted.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    target = parsed_request.target
    matches = _resolve_matches(target, registry.iter_clickhouse_checks())
    LOGGER.debug('Remote query target match count: %d', len(matches))
    if not matches:
        yield _failed_event(
            'target_not_found',
            'No loaded ClickHouse integration instance matched target selector.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return
    if len(matches) > 1:
        yield _failed_event(
            'target_ambiguous',
            'More than one loaded ClickHouse integration instance matched target selector.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    check = matches[0]
    creds = _resolve_upload_credentials(parsed_request.result_delivery)
    if not creds.api_key or not creds.app_key:
        yield _failed_event(
            'credentials_unavailable',
            'Remote query upload requires api_key and app_key to be configured on the Agent.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    if getattr(check, '_pool_manager', None) is None:
        yield _failed_event(
            'target_unavailable',
            'Matched ClickHouse check HTTP connection pool is unavailable.',
            elapsed_ms=_elapsed_ms(started_at),
        )
        return

    client = http_client if http_client is not None else _default_upload_client()
    stats = RemoteQueryRunStats()
    yield RemoteQueryEvent('metadata', _started_metadata(parsed_request))

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
    except RemoteQueryFailure as e:
        _safe_abort(client, creds)
        yield _failed_event(e.code, e.message, retryable=e.retryable, stats=_stats_metadata(stats, started_at))
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
