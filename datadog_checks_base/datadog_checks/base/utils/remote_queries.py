# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Source-page contracts, bounded page buffering, direct intake uploads, and producer timing.

Database execution and value normalization belong to integration adapters. The producer
registers one immutable source-page descriptor per upload and sends record-complete CSV
source pages to its-agent-intake: native ``COPY TO STDOUT`` blocks stream through one
bounded mutable page buffer with single-pass CSV framing — no per-record objects are
materialized — while canonical-token producers append framed rows to the same buffer.
Intake decodes, redacts, and writes the final JSON pages, so the producer never constructs
a final JSON envelope and never claims its source bytes or checksums are final artifact
metadata. Only metadata and the compact receipt return through the Agent's native callback.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import re
import time
from array import array
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, BinaryIO, Literal, Protocol

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

LOGGER = logging.getLogger(__name__)


REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY = 'remote_queries.execute.enable_query_allowlist'


REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES = frozenset(('false', 'no', '0', 'n', 'off'))


REMOTE_QUERY_UPLOAD_MAX_FILE_BYTES = 128 * 1024 * 1024


REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES = 100 * 1024 * 1024 * 1024


REMOTE_QUERY_DEFAULT_TIMEOUT_MS = 30_000


# The RFC-format page contract, labeled contract_version 1: a top-level numeric
# ``contract_version``, the run serialized under the contract field name ``crawl_id``, no
# ``batch_index`` in the body (the page index lives in the upload URL path and page metadata),
# and a bare ``data`` array of row objects. The number is RFC-owner-assigned, not ours to shift:
# the POC emits the RFC format everywhere and claims no v2; the shape is unchanged.
REMOTE_QUERY_ARTIFACT_VERSION = 1


# The bytes appended after the last row: close the bare ``data`` array and the document.
# The producer no longer writes final pages; page_prefix/PAGE_SUFFIX model the envelope intake
# generates so the producer can bound the final page it asks intake to build.
PAGE_SUFFIX = b']}'


# The two active source-page cell grammars, selected per upload by the descriptor's
# ``format_version``: canonical JSON value tokens framed as CSV (``csv-json-cell-v1``)
# and PostgreSQL-native ``COPY ... TO STDOUT`` CSV text (``postgres-copy-csv-v1``). Intake
# decodes by the same closed pair; a producer cannot invent a third grammar or mix them
# within one upload.
REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION = 'csv-json-cell-v1'
POSTGRES_COPY_CSV_DESCRIPTOR_FORMAT_VERSION = 'postgres-copy-csv-v1'
REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSIONS = (
    REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION,
    POSTGRES_COPY_CSV_DESCRIPTOR_FORMAT_VERSION,
)

RemoteQueryDescriptorFormat = Literal[
    REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION, POSTGRES_COPY_CSV_DESCRIPTOR_FORMAT_VERSION
]

# The source page's private media type: one record-complete CSV body per page index.
REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE = 'application/vnd.datadog.remote-query.rows+csv;version=1'

# Intake's defensive rejection when the final JSON page it would write exceeds maxFileBytes
# despite the producer's conservative bound. The producer answers by splitting the buffered
# records and retrying the same page index.
REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE = 'final_page_too_large'

# The closed descriptor logical-type set: the stable cross-database families intake accepts.
# ``vendor`` marks supported values without a narrower stable family; it is never a stringify
# escape hatch, because every value still has to pass the fail-closed value contract.
REMOTE_QUERY_LOGICAL_TYPES = (
    'boolean',
    'integer',
    'decimal',
    'float',
    'string',
    'temporal',
    'json',
    'binary',
    'vendor',
)

RemoteQueryLogicalType = Literal[
    'boolean', 'integer', 'decimal', 'float', 'string', 'temporal', 'json', 'binary', 'vendor'
]

# The fixed, bounded replacement marker intake substitutes for any matched scalar string or
# number leaf. The producer never emits it; the page bound accounts for intake emitting it in
# place of a shorter string or number — the only way redaction can grow a final page, since
# booleans and null are never scanned.
REMOTE_QUERY_REDACTED_MARKER = '[REDACTED]'
REMOTE_QUERY_REDACTED_MARKER_TOKEN = b'"[REDACTED]"'

# The canonical JSON spelling of the private wire, pinned by intake's canonical encoder:
# valid non-ASCII rides raw UTF-8 (never ``\uXXXX`` escapes) while JSON control characters,
# quote, and backslash stay escaped. Descriptor request bytes, the descriptor-derived schema
# and page-prefix bound bytes, the column-name key bytes used in bounds, and canonical string
# cell tokens and nested object keys all use it, so the producer's bytes are exactly the
# bytes intake canonicalizes and checksums.


def canonical_json_text(value: Any) -> str:
    """The canonical JSON text: raw non-ASCII, escaped JSON controls, quote, and backslash."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def canonical_json_bytes(value: Any) -> bytes:
    """The canonical JSON text as UTF-8 bytes, failing closed on unencodable text.

    A string that reached Python's text layer but cannot be encoded (a lone surrogate from
    a driver or a server payload) is a fixed ``unsupported_value`` failure, never an
    uncaught ``UnicodeEncodeError`` mid-upload.
    """
    try:
        return canonical_json_text(value).encode('utf-8')
    except UnicodeEncodeError:
        raise RemoteQueryFailure('unsupported_value', 'A canonical JSON string cannot be encoded as UTF-8.') from None


def redactable_leaf_final_bound(token: bytes | bytearray) -> int:
    """A redactable scalar leaf's final bytes: its own token or the marker, whichever is larger.

    Intake scans string and number leaves alike and substitutes the fixed marker string token
    for any match, so both families bound against the marker; booleans and null are never
    scanned and keep their exact token bounds at the encoding call sites.
    """
    return max(len(token), len(REMOTE_QUERY_REDACTED_MARKER_TOKEN))


def string_cell_token(text: str) -> tuple[bytes, int]:
    """A scalar string cell: its canonical JSON token and the redactable-leaf final bound."""
    token = canonical_json_bytes(text)
    return token, redactable_leaf_final_bound(token)


# The transport-only array-element delimiter contract, shared by both sides of the wire:
# one PostgreSQL internal ``char`` — exactly one byte — that is printable (no space, no
# control bytes, no DEL) and none of the native array literal's structural characters
# (quote, backslash, brace), so a literal split on it is unambiguous. Producers resolve
# it from ``pg_type.typdelim`` of the column's effective array element type; intake splits
# native array literals on exactly this character and nothing else.
POSTGRES_ARRAY_ELEMENT_DELIMITER_STRUCTURAL_CHARS = frozenset('" \\{}')


def validate_array_element_delimiter(value: str | None) -> str | None:
    """Validate one delimiter character: a single printable non-structural byte, or null."""
    if value is None:
        return value
    encoded = value.encode('utf-8', errors='strict')
    if len(encoded) != 1 or len(value) != 1:
        raise ValueError('array_element_delimiter must be exactly one single-byte character.')
    code = encoded[0]
    if code < 0x21 or code > 0x7E:
        raise ValueError('array_element_delimiter must be a printable character.')
    if value in POSTGRES_ARRAY_ELEMENT_DELIMITER_STRUCTURAL_CHARS:
        raise ValueError('array_element_delimiter must not be an array-literal structural character.')
    return value


def valid_array_element_delimiter_code(code: int) -> str:
    """Validate one ``pg_type.typdelim`` internal-char byte code into its delimiter string.

    Producers resolve the delimiter as the raw internal ``char`` code from the catalog;
    this is the same contract as :func:`validate_array_element_delimiter` applied to the
    byte before it becomes descriptor text.
    """
    if code < 0x21 or code > 0x7E:
        raise RemoteQueryFailure(
            'schema_unavailable', 'A column type carries an array element delimiter that is not printable.'
        )
    value = chr(code)
    if value in POSTGRES_ARRAY_ELEMENT_DELIMITER_STRUCTURAL_CHARS:
        raise RemoteQueryFailure(
            'schema_unavailable', 'A column type carries an array-literal structural element delimiter.'
        )
    return value


def _validate_utf8_byte_length(value: str, field: str, maximum_bytes: int) -> str:
    """Bound one descriptor text field by its UTF-8 encoded length.

    Server length limits are byte limits, so a multibyte name is bounded by its encoded byte
    count, not its character count, and text that cannot be encoded at all (a lone
    surrogate) is rejected at validation instead of failing the canonical JSON encoding
    later in the wire.
    """
    try:
        encoded = value.encode('utf-8')
    except UnicodeEncodeError:
        raise ValueError('{} must be encodable as UTF-8.'.format(field)) from None
    if len(encoded) > maximum_bytes:
        raise ValueError('{} must be at most {} UTF-8 bytes.'.format(field, maximum_bytes))
    return value


class RemoteQueryDescriptorColumn(BaseModel):
    """One ordered descriptor column: result name, vendor type, logical type, and delimiter.

    ``column_name`` and ``vendor_data_type`` are bounded by UTF-8 byte length because the
    server limits they mirror are byte limits: 255 bytes for names, 1024 for vendor types.
    ``array_element_delimiter`` is transport-only schema metadata — one PostgreSQL
    ``pg_type.typdelim`` of the column's effective array ELEMENT type for the native
    postgres-copy-csv-v1 array columns, null for every non-array column and every
    csv-json-cell-v1 column — that never reaches the consumer-visible final page: intake
    splits native array literals on it instead of guessing a separator from contents.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    column_name: StrictStr = Field(min_length=1, max_length=255)
    vendor_data_type: StrictStr = Field(min_length=1, max_length=1024)
    logical_type: RemoteQueryLogicalType
    array_element_delimiter: StrictStr | None = None

    @field_validator('column_name')
    @classmethod
    def validate_column_name(cls, value: str) -> str:
        return _validate_utf8_byte_length(value, 'column_name', 255)

    @field_validator('vendor_data_type')
    @classmethod
    def validate_vendor_data_type(cls, value: str) -> str:
        return _validate_utf8_byte_length(value, 'vendor_data_type', 1024)

    @field_validator('array_element_delimiter')
    @classmethod
    def validate_array_element_delimiter(cls, value: str | None) -> str | None:
        return validate_array_element_delimiter(value)


class RemoteQueryUploadDescriptor(BaseModel):
    """The immutable per-upload source-page descriptor, registered once before result rows.

    Intake persists the descriptor and stamps the schema (when requested) into every final
    page from it. ``agent_hostname`` is the executing check's Agent-reported identity, threaded
    from the check instance, never the delivery or the machine's socket name. The
    ``format_version`` selects the source-page cell grammar — canonical JSON tokens or
    PostgreSQL-native COPY CSV — and intake dispatches its decode on the same value.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    format_version: RemoteQueryDescriptorFormat
    include_schema: StrictBool
    agent_hostname: StrictStr = Field(min_length=1, max_length=255)
    columns: tuple[RemoteQueryDescriptorColumn, ...] = Field(min_length=1)

    @field_validator('agent_hostname')
    @classmethod
    def validate_agent_hostname(cls, value: str) -> str:
        return _validate_utf8_byte_length(value, 'agent_hostname', 255)

    @model_validator(mode='after')
    def validate_unique_columns(self) -> 'RemoteQueryUploadDescriptor':
        names = [column.column_name for column in self.columns]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError('Duplicate descriptor column name(s): {}'.format(', '.join(duplicates)))
        for column in self.columns:
            is_array = column.vendor_data_type.endswith('[]')
            if self.format_version == POSTGRES_COPY_CSV_DESCRIPTOR_FORMAT_VERSION:
                if is_array and column.array_element_delimiter is None:
                    raise ValueError(
                        'Array columns of the postgres-copy-csv-v1 format require an array_element_delimiter.'
                    )
                if not is_array and column.array_element_delimiter is not None:
                    raise ValueError('array_element_delimiter must be null for non-array postgres-copy-csv-v1 columns.')
            elif column.array_element_delimiter is not None:
                raise ValueError('array_element_delimiter must be null for the csv-json-cell-v1 format.')
        return self


def descriptor_request_bytes(descriptor: RemoteQueryUploadDescriptor) -> bytes:
    """Canonical compact JSON for the descriptor registration request.

    Field order is the model's declaration order and the spelling is intake's canonical
    JSON, so the body is a pure function of the descriptor, every registration retry for one
    upload is byte-identical, and the checksum in intake's receipt is over exactly these
    bytes.
    """
    return canonical_json_bytes(descriptor.model_dump())


def descriptor_schema_bytes(descriptor: RemoteQueryUploadDescriptor) -> bytes | None:
    """The schema JSON intake stamps into every final page, or None when schema emission is off.

    Intake derives the per-page schema from the registered descriptor; the producer computes
    the same bytes only to bound and validate the final pages it asks intake to build.
    """
    if not descriptor.include_schema:
        return None
    entries = [
        {'column_name': column.column_name, 'vendor_data_type': column.vendor_data_type}
        for column in descriptor.columns
    ]
    return canonical_json_bytes(entries)


RemoteQueryEmit = Callable[[str, str, bytes], None]


def normalize_host(value: str | None) -> str | None:
    """Normalize one host for endpoint identity: trimmed, lowercased, one trailing dot removed.

    Shared by the target model and the integration adapters so a configured host and a
    requested host normalize identically before any comparison.
    """
    if value is None:
        return None
    host = value.strip().lower()
    if host.endswith('.'):
        host = host[:-1]
    if not host:
        raise ValueError('host must be a non-empty string')
    return host


class RemoteQueryTarget(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    host: StrictStr | None = Field(default=None, min_length=1)
    port: StrictInt | None = Field(default=None, ge=1, le=65535)
    dbname: StrictStr | None = Field(default=None, min_length=1)
    database_instance: StrictStr | None = Field(default=None, min_length=1)

    @field_validator('host')
    @classmethod
    def validate_host(cls, value: str | None) -> str | None:
        return normalize_host(value)

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

        if self.database_instance is not None:
            # database_instance selects one loaded check, whose materialized configured
            # database is the execution database; host/port/dbname is the other selector
            # mode. dbname must not override the selected check's monitored database, so
            # it is rejected together with the endpoint fields.
            if self.model_fields_set & {'host', 'port', 'dbname'}:
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
    # The page-count ceiling itself is worker/intake-owned: the integration only enforces
    # the delivered value.
    max_pages: StrictInt = Field(alias='maxPages', ge=1)
    # The delivery-injected timeout is the run-wide monotonic hard wall: it covers target
    # resolution, query execution, page construction, upload, and retries, and no instance
    # configuration may lengthen it. An instance-configured database timeout may shorten
    # the effective database statement timeout, never the wall itself.
    timeout_ms: StrictInt = Field(default=REMOTE_QUERY_DEFAULT_TIMEOUT_MS, alias='timeoutMs', ge=1)

    @model_validator(mode='after')
    def validate_limit_relations(self) -> 'RemoteQueryUploadLimits':
        if self.max_row_bytes > self.max_file_bytes:
            raise ValueError('maxRowBytes must not exceed maxFileBytes: a row must fit inside one page')
        if self.max_schema_bytes > self.max_file_bytes:
            raise ValueError('maxSchemaBytes must not exceed maxFileBytes')
        if self.max_file_bytes > self.max_result_bytes:
            raise ValueError('maxFileBytes must not exceed maxResultBytes')
        return self


class RemoteQueryResultDelivery(BaseModel):
    """Backend-injected upload instructions and artifact contract metadata.

    The Agent forwards the run-scoped intake session instructions (``uploadId``,
    ``baseUrl``), the effective server-owned limits, the artifact contract version, and the
    authoritative run/task identity used in every page envelope. The session is identified
    by ``uploadId`` alone; the upload calls authorize with the org API/application keys from
    Agent config. Every field is server-owned: the integration validates what it receives
    and never invents values.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    run_id: StrictStr = Field(alias='runId', min_length=1)
    task_id: StrictStr = Field(alias='taskId', min_length=1)
    artifact_version: Literal[REMOTE_QUERY_ARTIFACT_VERSION] = Field(alias='artifactVersion')
    upload_id: StrictStr = Field(alias='uploadId', min_length=1)
    base_url: StrictStr = Field(alias='baseUrl', min_length=1)
    limits: RemoteQueryUploadLimits


# The standard Datadog distributed-tracing headers injected into every intake upload request
# when the request carried a trace context: the validated trace and parent IDs in their
# canonical decimal spelling and the integer sampling priority, exactly the header set the
# Datadog tracing libraries and intake's middleware exchange.
REMOTE_QUERY_TRACE_ID_HEADER = 'x-datadog-trace-id'
REMOTE_QUERY_TRACE_PARENT_ID_HEADER = 'x-datadog-parent-id'
REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER = 'x-datadog-sampling-priority'

# 64-bit trace identity arrives as an unsigned decimal string: a JSON number cannot carry
# every uint64 without precision loss, so the ids never round-trip through a numeric type.
REMOTE_QUERY_TRACE_ID_PATTERN = re.compile(r'\A[0-9]+\Z')
REMOTE_QUERY_TRACE_ID_MAX = (1 << 64) - 1

# The tracer's positive keep priorities: 1 auto-keep, 2 user-keep. Drop and reject
# priorities are never propagated onto uploads the producer must still make.
REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_KEEP_VALUES = frozenset((1, 2))


class RemoteQueryTraceContext(BaseModel):
    """The optional Agent-supplied tracing carrier for one execution's upload requests.

    The Agent attaches the active ``action.run`` trace context so the producer can inject
    standard Datadog distributed-tracing headers into its intake page, finalize, and abort
    requests, making intake's request spans children of the Agent execution trace instead of
    unrelated traces. The carrier is observability metadata only: it never authorizes,
    routes, or validates an upload, and it never appears in page bodies, result envelopes,
    execution diagnostics, errors, metrics, or logs. A valid absent carrier is supported
    for mixed versions and preserves request behavior byte for byte; a supplied-but-invalid
    carrier is a strict validation error, never a silently dropped one.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    trace_id: StrictStr = Field(alias='traceId')
    parent_id: StrictStr = Field(alias='parentId')
    sampling_priority: StrictInt = Field(alias='samplingPriority')

    @field_validator('trace_id', 'parent_id')
    @classmethod
    def validate_trace_identity(cls, value: str) -> str:
        if REMOTE_QUERY_TRACE_ID_PATTERN.match(value) is None:
            raise ValueError('must be an unsigned decimal integer string')
        parsed = int(value)
        if parsed == 0 or parsed > REMOTE_QUERY_TRACE_ID_MAX:
            raise ValueError('must be a non-zero unsigned decimal uint64 value')
        # The canonical decimal spelling: the emitted header value is byte-stable for every
        # valid spelling of the same id and never echoes a zero-padded input form.
        return str(parsed)

    @field_validator('sampling_priority')
    @classmethod
    def validate_sampling_priority(cls, value: int) -> int:
        if value not in REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_KEEP_VALUES:
            raise ValueError('must be a supported positive keep sampling priority (1 or 2)')
        return value

    def trace_headers(self) -> dict[str, str]:
        """The standard distributed-tracing headers this validated context injects."""
        return {
            REMOTE_QUERY_TRACE_ID_HEADER: self.trace_id,
            REMOTE_QUERY_TRACE_PARENT_ID_HEADER: self.parent_id,
            REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER: str(self.sampling_priority),
        }


class RemoteQueryRequest(BaseModel):
    """A single remote query execution producing bounded JSON result pages."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['produce_json_pages'] = Field(alias='operation')
    target: RemoteQueryTarget
    query: StrictStr = Field(min_length=1)
    include_schema: StrictBool = Field(default=False, alias='includeSchema')
    result_delivery: RemoteQueryResultDelivery = Field(alias='resultDelivery')
    trace_context: RemoteQueryTraceContext | None = Field(default=None, alias='traceContext')


class RemoteQueryResolveRequest(BaseModel):
    """A resolve_target request: one strict target-only operation, nothing else.

    The Agent's resolve dispatch carries only the operation and the target. Strict validation
    rejects every execution field — query, includeSchema, resultDelivery, credentials, a match
    fingerprint, or anything else — so a resolve sweep can never carry SQL or upload
    instructions.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['resolve_target'] = Field(alias='operation')
    target: RemoteQueryTarget


@dataclass
class RemoteQueryRunStats:
    """Mutable run accounting shared with the page writer so failures can report partials."""

    rows_emitted: int = 0
    pages_emitted: int = 0
    bytes_emitted: int = 0


REMOTE_QUERY_DIAGNOSTICS_CONTRACT_VERSION = 1


@dataclass
class RemoteQueryTimingPhase:
    """One entered producer phase segment; also the exit token for ``exit_phase``."""

    name: str
    segment_start: float


# The producer phase vocabulary, in contract emission order, with each phase's camelCase
# metadata key. The database and encode phases are entered by the integration adapters;
# the page-upload and finalize phases by ``SourcePageWriter``.
PRODUCER_PHASE_METADATA_KEYS = (
    ('database_setup', 'databaseSetupMs'),
    ('database_fetch', 'databaseFetchMs'),
    ('encode_and_page_build', 'encodeAndPageBuildMs'),
    ('page_upload', 'pageUploadMs'),
    ('finalize', 'finalizeMs'),
)


def nearest_rank_percentile(sorted_ms: Sequence[float], quantile: float) -> float:
    """The pinned nearest-rank percentile: the ceil(quantile*N)-th of N ascending values.

    One definition shared by the emitted aggregates and their tests; ``sorted_ms`` must
    hold at least one value.
    """
    return sorted_ms[max(1, math.ceil(quantile * len(sorted_ms))) - 1]


class RemoteQueryProducerTimings:
    """Bounded per-run timing accumulator for the producer execution diagnostics contract.

    Phases are non-overlapping by construction: entering a phase suspends the enclosing
    phase's accumulation and exiting resumes it, so nested work (a fetch inside the row
    loop, an upload inside a row's ``add_row``) is attributed to exactly one bucket.
    Un-instrumented time — request validation, target and credential resolution,
    transaction teardown — is never accumulated; it is the ``otherMs`` remainder
    computed at emission.

    Space is constant except for at most one duration per completed page: a page's full
    upload wall is promoted into the per-page distribution only after its receipt is
    verified and it is counted, and the page count is bounded by ``maxPages``.

    The clock defaults to the module's ``time.monotonic`` so the existing scripted-clock
    test style keeps working; pass ``clock`` to script the accumulator directly.
    """

    def __init__(self, started_at: float, clock: Callable[[], float] | None = None):
        self.started_at = started_at
        self._clock = clock
        self._phase_ms: dict[str, float] = {}
        self._stack: list[RemoteQueryTimingPhase] = []
        self._page_walls_ms: list[float] = []
        self._pending_page_wall_ms: float | None = None
        self._upload_attempts = 0
        self._upload_retries = 0
        self._upload_attempts_measured = False
        self._first_page_ack_ms: float | None = None

    def _now(self) -> float:
        if self._clock is not None:
            return self._clock()
        return time.monotonic()

    def enter_phase(self, name: str) -> RemoteQueryTimingPhase:
        """Enter one phase, suspending the enclosing phase's accumulation."""
        now = self._now()
        if self._stack:
            enclosing = self._stack[-1]
            segment_ms = max(0.0, now - enclosing.segment_start) * 1000
            self._phase_ms[enclosing.name] = self._phase_ms.get(enclosing.name, 0.0) + segment_ms
        phase = RemoteQueryTimingPhase(name, now)
        self._stack.append(phase)
        return phase

    def exit_phase(self, phase: RemoteQueryTimingPhase) -> float:
        """Account one entered phase segment in ms; idempotent for an already-exited phase.

        The exit is a no-op unless the segment is still the top of the stack, so a phase
        that spans nested ``with`` blocks can be exited inline and then offered again from
        its spanning ``finally``.
        """
        if not self._stack or self._stack[-1] is not phase:
            return 0.0
        now = self._now()
        self._stack.pop()
        segment_ms = max(0.0, now - phase.segment_start) * 1000
        self._phase_ms[phase.name] = self._phase_ms.get(phase.name, 0.0) + segment_ms
        if self._stack:
            self._stack[-1].segment_start = now
        return segment_ms

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        phase = self.enter_phase(name)
        try:
            yield
        finally:
            self.exit_phase(phase)

    @contextmanager
    def page_upload(self) -> Iterator[None]:
        """Bracket one whole ``put_source_page`` call — every attempt plus backoff — as page upload.

        The measured wall is stashed until ``note_page_acknowledged`` promotes it into the
        per-page distribution, so only verified, counted pages enter it; the cumulative
        ``pageUploadMs`` keeps every attempted wall either way.
        """
        phase = self.enter_phase('page_upload')
        try:
            yield
        finally:
            self._pending_page_wall_ms = self.exit_phase(phase)

    def note_page_acknowledged(self) -> None:
        """Promote the last uploaded page: receipt verified, counted, and acknowledged."""
        if self._pending_page_wall_ms is not None:
            self._page_walls_ms.append(self._pending_page_wall_ms)
            self._pending_page_wall_ms = None
        if self._first_page_ack_ms is None:
            self._first_page_ack_ms = max(0.0, self._now() - self.started_at) * 1000

    def note_upload_attempt(self, *, retry: bool) -> None:
        """Count one HTTP upload attempt; ``retry`` marks an attempt beyond a page's first."""
        self._upload_attempts += 1
        if retry:
            self._upload_retries += 1
        self._upload_attempts_measured = True

    def metadata(self, stats: RemoteQueryRunStats | None = None) -> dict[str, Any]:
        """The contract's camelCase producer diagnostics; only measured fields are present.

        ``stats`` mirrors the run counters at emission time; pass ``None`` when the run
        never started producing, so no receipt counters exist to mirror.
        """
        total_ms = max(0, int((self._now() - self.started_at) * 1000))
        producer: dict[str, Any] = {'totalMs': total_ms}
        named_ms = 0
        for phase_name, metadata_key in PRODUCER_PHASE_METADATA_KEYS:
            if phase_name in self._phase_ms:
                phase_ms = int(self._phase_ms[phase_name])
                producer[metadata_key] = phase_ms
                named_ms += phase_ms
        producer['otherMs'] = max(0, total_ms - named_ms)
        if self._first_page_ack_ms is not None:
            producer['timeToFirstPageMs'] = int(self._first_page_ack_ms)
        if stats is not None:
            producer['pageCount'] = stats.pages_emitted
            producer['rowCount'] = stats.rows_emitted
            producer['byteCount'] = stats.bytes_emitted
        if self._upload_attempts_measured:
            producer['uploadAttemptCount'] = self._upload_attempts
            producer['uploadRetryCount'] = self._upload_retries
        if self._page_walls_ms:
            walls = sorted(self._page_walls_ms)
            producer['pageUploadMinMs'] = int(walls[0])
            producer['pageUploadP50Ms'] = int(nearest_rank_percentile(walls, 0.50))
            producer['pageUploadP95Ms'] = int(nearest_rank_percentile(walls, 0.95))
            producer['pageUploadMaxMs'] = int(walls[-1])
        return {'contractVersion': REMOTE_QUERY_DIAGNOSTICS_CONTRACT_VERSION, 'producer': producer}


class NullRemoteQueryProducerTimings(RemoteQueryProducerTimings):
    """No-op timings so instrumentation call sites never branch on ``timings is None``."""

    def __init__(self) -> None:
        super().__init__(0.0)

    def enter_phase(self, name: str) -> RemoteQueryTimingPhase:
        return RemoteQueryTimingPhase(name, 0.0)

    def exit_phase(self, phase: RemoteQueryTimingPhase) -> float:
        return 0.0

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        yield

    @contextmanager
    def page_upload(self) -> Iterator[None]:
        yield

    def note_page_acknowledged(self) -> None:
        pass

    def note_upload_attempt(self, *, retry: bool) -> None:
        pass


NULL_PRODUCER_TIMINGS = NullRemoteQueryProducerTimings()


@dataclass(frozen=True)
class EncodedCell:
    """One canonical JSON value token plus the conservative bound on its final JSON bytes.

    ``token`` is the pinned value-contract encoding of the cell. ``final_bound`` bounds the
    bytes intake can emit for the cell after redaction: every scalar string or number leaf
    either keeps its token or is replaced by the fixed ``[REDACTED]`` marker, whichever is
    longer; booleans and null are never scanned and keep their exact token bounds.
    """

    token: bytes
    final_bound: int


@dataclass(frozen=True)
class SourcePageUploadMetadata:
    """The complete identity of one buffered source page, declared in the page PUT headers.

    Every field is computed while the page's complete CSV records are buffered, so the page
    request and any whole-page retry carry stable source metadata. Intake derives the final
    page's own key, bytes, and checksum; these source values identify the retry and are never
    claims about the final artifact.
    """

    batch_index: int
    record_offset: int
    source_bytes: int
    rows: int
    sha256_hex: str


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


JSON_NUMBER_PATTERN = re.compile(r'\A-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?\Z')


NON_FINITE_NUMERIC_TEXT = frozenset(('NaN', 'Infinity', '-Infinity'))


def encode_non_finite_text(out: bytearray, text: str) -> None:
    out += canonical_json_bytes(text)


def encode_raw_number_text(out: bytearray, text: str) -> None:
    if not JSON_NUMBER_PATTERN.match(text):
        raise RemoteQueryFailure('unsupported_value', 'Database returned invalid JSON numeric text.')
    out += text.encode('utf-8')


def encode_decimal(out: bytearray, value: Decimal) -> None:
    if value.is_finite():
        encode_raw_number_text(out, str(value))
        return
    if value.is_nan():
        encode_non_finite_text(out, 'NaN')
    elif value > 0:
        encode_non_finite_text(out, 'Infinity')
    else:
        encode_non_finite_text(out, '-Infinity')


def encode_float(out: bytearray, value: float) -> None:
    if math.isfinite(value):
        # Python repr is the shortest string that round-trips the float.
        encode_raw_number_text(out, repr(value))
    elif math.isnan(value):
        encode_non_finite_text(out, 'NaN')
    elif value > 0:
        encode_non_finite_text(out, 'Infinity')
    else:
        encode_non_finite_text(out, '-Infinity')


def page_prefix(
    *,
    run_id: str,
    task_id: str,
    record_offset: int,
    agent_hostname: str,
    schema_json: bytes | None,
) -> bytes:
    """The envelope bytes through the opening of ``data``, with no trailing space.

    The authoritative ITS ``run_id`` is serialized under the contract field name ``crawl_id``;
    it is a field-name mapping only, never a second identifier. ``agent_hostname`` is the
    executing host's Agent-reported identity, always stamped so the console can attribute
    a run to the agent that produced its pages. It is host identity, not job data, so it is
    threaded from the executing check instance, never the delivery. The page index is
    metadata-only in the RFC format labeled contract_version 1: it reaches the upload URL path
    and ``SourcePageUploadMetadata``, not the serialized body.
    """
    head = b''.join(
        (
            b'{"contract_version":%d,"crawl_id":' % REMOTE_QUERY_ARTIFACT_VERSION,
            canonical_json_bytes(run_id),
            b',"task_id":',
            canonical_json_bytes(task_id),
            b',"record_offset":%d,"agent_hostname":' % record_offset,
            canonical_json_bytes(agent_hostname),
            b',',
        )
    )
    parts = [head]
    if schema_json is not None:
        parts.append(b'"schema":')
        parts.append(schema_json)
        parts.append(b',')
    parts.append(b'"data":[')
    return b''.join(parts)


# A framed CSV record is at most twice its final-JSON row bound minus a positive constant:
# a canonical-token cell at worst doubles the token's quotes and adds two framing quotes,
# while every column contributes at least a three-byte key token to the row bound. The
# cap below is a defensive split trigger that valid operation can never reach: the
# source-page target closes every page at the target plus at most one record, and
# maxRowBytes can never exceed maxFileBytes, so a page stays strictly below
# target + maxFileBytes < 2 * maxFileBytes. It keeps retry memory bounded even if that
# proof ever breaks.
REMOTE_QUERY_SOURCE_PAGE_CAP_FACTOR = 2


class _StringSink:
    """A ``csv.writer`` target that collects the written string pieces."""

    __slots__ = ('pieces',)

    def __init__(self) -> None:
        self.pieces: list[str] = []

    def write(self, value: str) -> int:
        self.pieces.append(value)
        return len(value)


def frame_csv_record(tokens: Sequence[bytes]) -> bytes:
    """Frame canonical cell tokens as one source-page CSV record.

    The pinned private dialect: Python ``csv`` with the default comma delimiter, ``"`` doubled
    by minimal quoting, LF record endings, UTF-8, and no header row. Canonical tokens are
    UTF-8 JSON (valid non-ASCII rides raw), so the text round-trip is byte-exact and only CSV
    framing is added; a raw carriage return inside a token would corrupt the record, so it
    fails closed instead.
    """
    for token in tokens:
        if b'\r' in token:
            raise RemoteQueryFailure('unsupported_value', 'A canonical cell token carried a raw carriage return.')
    sink = _StringSink()
    csv.writer(sink, lineterminator='\n').writerow([token.decode('utf-8') for token in tokens])
    return ''.join(sink.pieces).encode('utf-8')


# ---------------------------------------------------------------------------
# PostgreSQL-native COPY CSV framing and source-page sizing (postgres-copy-csv-v1)
# ---------------------------------------------------------------------------

# In the native grammar every non-null field is quoted with internal quotes doubled, NULL
# is the sole unquoted field (the two-byte \N marker), and every record ends with one LF;
# commas and CR/LF can appear raw inside quoted fields. The producer never predicts the
# transformed final JSON bytes of a native record — intake stays authoritative for
# maxFileBytes and answers an oversized attempt with final_page_too_large, which the
# writer splits at a recorded record boundary and retries at the same page index — so the
# producer's own sizing is transport policy only.

# The native wire's two framing bytes: every record ends with one LF, and a record's true
# terminator is the first LF that closes every quoted field — with ``FORCE_QUOTE *`` every
# non-null field's quotes pair and escaped quotes double, so an even running quote count
# since the record's start marks every field boundary — which keeps embedded commas,
# quotes, and CR/LF inside their record while records stay whole.
POSTGRES_COPY_CSV_RECORD_TERMINATOR = b'\n'
POSTGRES_COPY_CSV_FIELD_QUOTE = b'"'

# The internal source-page target, as a fraction of the final-file limit: the raw source
# bytes one page request may carry before the writer closes the page at the record
# boundary that reaches it. 4/5 puts the target at 80 MiB for the normal 100 MiB final-file
# target: the representative large-result row's decoded JSON grows only a few percent
# over its native record (per-column keys and separators), so an ordinary page fits
# without a rejection round trip, while row distributions that grow more — arrays,
# redaction, narrow rows — stay covered by intake's authoritative rejection path.
REMOTE_QUERY_SOURCE_PAGE_TARGET_NUM = 4
REMOTE_QUERY_SOURCE_PAGE_TARGET_DEN = 5


class _SourcePageBody:
    """A seekable read-only view over the active page buffer's first ``end`` bytes.

    ``put_source_page`` receives the live buffer so no whole-page copy exists between the
    writer and an HTTP attempt: each ``read`` slices the buffer and copies only the chunk
    requested, and ``seek(0)`` rewinds a whole-page retry to the exact same bytes. The view
    derives its buffer export per call and holds none between calls, so the writer can
    compact the buffer as soon as an attempt is complete. ``read`` always returns ``bytes``
    — a retained chunk must never pin the shared buffer.
    """

    __slots__ = ('_buf', '_end', '_pos')

    def __init__(self, buf: bytearray, end: int):
        self._buf = buf
        self._end = end
        self._pos = 0

    def read(self, amount: int | None = -1) -> bytes:
        if amount is None or amount < 0:
            amount = self._end - self._pos
        else:
            amount = max(0, min(amount, self._end - self._pos))
        data = bytes(memoryview(self._buf)[self._pos : self._pos + amount])
        self._pos += amount
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self._end + offset
        else:
            raise ValueError('invalid whence ({!r}, should be 0, 1 or 2).'.format(whence))
        self._pos = max(0, min(self._pos, self._end))
        return self._pos

    def tell(self) -> int:
        return self._pos

    def __iter__(self):
        # requests streams a body that exposes ``__iter__``; the HTTP sender consumes the
        # body through ``read`` alone, so iteration itself never happens.
        raise TypeError('the source-page body is a byte stream, not an iterable.')


class SourcePageWriter:
    """Keep one record-complete source page in RAM through its retries; never the full result.

    The writer registers the upload descriptor once before any record is read and keeps one
    bounded mutable byte buffer holding exactly the active page's complete records —
    canonical-token records framed from ``add_row`` cells, or the native ``COPY TO STDOUT``
    blocks fed to :meth:`feed_native_copy_block` verbatim — plus the record-end offsets that
    carry the page's row boundaries. The token grammar splits pages by the conservative
    final-JSON bound; the native grammar closes a page at the record boundary that reaches
    the internal source-page target and leaves intake authoritative for the transformed
    final size, splitting a rejected page at a recorded boundary and retrying the same page
    index without requerying. Every retry sends the same buffered bytes, and the page
    checksum is fed each record's bytes exactly once. Stats and the compact receipt
    accumulate from intake's returned final metadata, never from local source sizes. The
    Agent admits one execution at a time; each adapter must call discard in its finally
    block so query/encoding failures also release the active page.
    """

    def __init__(
        self,
        delivery: RemoteQueryResultDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
        timings: RemoteQueryProducerTimings | None = None,
    ):
        self._delivery = delivery
        self._creds = creds
        self._client = client
        self._descriptor = descriptor
        self._guard = guard
        self._stats = stats
        self._timings = timings if timings is not None else NULL_PRODUCER_TIMINGS
        limits = delivery.limits
        if len(descriptor.columns) > limits.max_columns:
            raise RemoteQueryFailure(
                'max_columns_exceeded',
                'Descriptor carries {} columns; the limit is {}.'.format(len(descriptor.columns), limits.max_columns),
            )
        self._schema_json = descriptor_schema_bytes(descriptor)
        if self._schema_json is not None and len(self._schema_json) > limits.max_schema_bytes:
            raise RemoteQueryFailure(
                'max_schema_bytes_exceeded',
                'Encoded schema is {} bytes; the limit is {}.'.format(len(self._schema_json), limits.max_schema_bytes),
            )
        if (
            len(
                page_prefix(
                    run_id=delivery.run_id,
                    task_id=delivery.task_id,
                    record_offset=0,
                    agent_hostname=descriptor.agent_hostname,
                    schema_json=self._schema_json,
                )
            )
            + len(PAGE_SUFFIX)
            > limits.max_file_bytes
        ):
            raise RemoteQueryFailure(
                'max_file_bytes_exceeded',
                'The repeated schema plus the minimal page envelope exceeds maxFileBytes.',
            )
        # Each row object repeats every descriptor key, so the canonical key tokens' UTF-8
        # bytes are part of the token grammar's conservative row bound.
        self._key_bound = sum(len(canonical_json_bytes(column.column_name)) for column in descriptor.columns)
        self._native_mode = descriptor.format_version == POSTGRES_COPY_CSV_DESCRIPTOR_FORMAT_VERSION
        # The internal transport policy: the raw source bytes one page request may carry
        # before the page closes at the record boundary that reaches it. Intake stays
        # authoritative for the transformed final page size.
        self._source_page_target = (
            limits.max_file_bytes * REMOTE_QUERY_SOURCE_PAGE_TARGET_NUM // REMOTE_QUERY_SOURCE_PAGE_TARGET_DEN
        )
        # The defensive hard source transport cap (see REMOTE_QUERY_SOURCE_PAGE_CAP_FACTOR):
        # unreachable while the target close holds, kept so retry memory stays bounded even
        # if that proof ever breaks.
        self._source_page_cap = REMOTE_QUERY_SOURCE_PAGE_CAP_FACTOR * limits.max_file_bytes
        # One bounded mutable source-page buffer: complete records append verbatim, the
        # record-end offsets carry the page's row boundaries for close and split, and the
        # page checksum is fed each record's bytes exactly once.
        self._buf = bytearray()
        self._record_ends: array = array('q')
        self._record_bounds: array | None = None if self._native_mode else array('q')
        self._page_bound = 0
        self._page_active = False
        self._page_record_offset = 0
        self._page_sha = hashlib.sha256()
        self._page_hashed = 0
        # Native framing state, carried across COPY blocks: the scanned position, the
        # running quote parity of the still-open record, and where that record begins.
        self._scan_pos = 0
        self._quote_parity = 0
        self._open_start = 0
        # Registration precedes any result row: one byte-identical body per upload, and
        # intake's receipt must exactly confirm the registered descriptor before rows flow.
        request_body = descriptor_request_bytes(descriptor)
        response = client.register_descriptor(creds, request_body)
        verify_descriptor_response(response, creds.upload_id, descriptor, request_body)

    def add_row(self, cells: Sequence[EncodedCell]) -> None:
        """Frame and buffer one row's canonical tokens; split the page before the final bound overflows."""
        if self._descriptor.format_version != REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION:
            raise RemoteQueryFailure(
                'unsupported_value', 'Canonical cell tokens require a csv-json-cell-v1 descriptor.'
            )
        if len(cells) != len(self._descriptor.columns):
            raise RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
        record = frame_csv_record([cell.token for cell in cells])
        row_bound = 1 + self._key_bound + 2 * len(cells) + sum(cell.final_bound for cell in cells)
        self._append_record(record, row_bound)

    def feed_native_copy_block(self, block: bytes | bytearray | memoryview) -> None:
        """Append one ``COPY TO STDOUT`` block to the active page and close pages at the target.

        libpq block boundaries are not a CSV record contract: the block's bytes append
        verbatim to the active page buffer and are scanned once — a record completes at the
        first LF that closes every quoted field, an even running quote count since the
        record's start — with the framing state carried across blocks, so embedded commas,
        quotes, and CR/LF ride inside their record. Each completed record's end offset is
        recorded; a page closes at the record boundary that reaches the internal
        source-page target, and its upload runs inside this call. Only one partial record
        beyond the last completed record is ever buffered, bounded by ``maxRowBytes``.
        """
        if self._descriptor.format_version != POSTGRES_COPY_CSV_DESCRIPTOR_FORMAT_VERSION:
            raise RemoteQueryFailure(
                'unsupported_value', 'Native COPY blocks require a postgres-copy-csv-v1 descriptor.'
            )
        # The record loop below is the producer's hot path, so every value it touches per
        # record — the framing bytes, the budgets, the guard, the record offsets, the
        # checksum — is bound once per block; a page close rebinds the two it replaces.
        max_row_bytes = self._delivery.limits.max_row_bytes
        record_terminator = POSTGRES_COPY_CSV_RECORD_TERMINATOR
        field_quote = POSTGRES_COPY_CSV_FIELD_QUOTE
        target = self._source_page_target
        cap = self._source_page_cap
        guard = self._guard
        record_ends = self._record_ends
        sha = self._page_sha
        active = self._page_active
        buf = self._buf
        buf += block
        pos = self._scan_pos
        parity = self._quote_parity
        open_start = self._open_start
        while True:
            terminator = buf.find(record_terminator, pos)
            if terminator < 0:
                break
            # Quotes since the record's start decide whether this LF closes the record or
            # rides inside a quoted field.
            parity ^= buf.count(field_quote, pos, terminator) & 1
            pos = terminator + 1
            if parity:
                continue
            if pos - open_start > max_row_bytes:
                raise RemoteQueryFailure(
                    'row_too_large',
                    'A single native record exceeds maxRowBytes ({} > {} bytes).'.format(
                        pos - open_start, max_row_bytes
                    ),
                )
            guard()
            if not active:
                self._begin_page()
                active = True
            record_ends.append(pos)
            open_start = pos
            if pos >= target or pos > cap:
                consumed = self._close_page()
                active = self._page_active
                if consumed:
                    pos -= consumed
                    open_start -= consumed
                buf = self._buf
                record_ends = self._record_ends
                sha = self._page_sha
        # Quotes between the last LF and the block's end belong to the still-open record.
        end = len(buf)
        if pos < end:
            parity ^= buf.count(field_quote, pos, end) & 1
        self._quote_parity = parity
        self._scan_pos = end
        self._open_start = open_start
        # A partial record already beyond maxRowBytes can only complete beyond it: fail
        # now instead of buffering an unbounded record.
        if end - open_start > max_row_bytes:
            raise RemoteQueryFailure(
                'row_too_large',
                'A single native record exceeds maxRowBytes ({} > {} bytes).'.format(end - open_start, max_row_bytes),
            )
        # Feed the page checksum the records this block completed: each byte exactly once.
        hashed_to = record_ends[-1] if record_ends else 0
        if hashed_to > self._page_hashed:
            sha.update(memoryview(buf)[self._page_hashed : hashed_to])
            self._page_hashed = hashed_to

    def finish_native_copy_stream(self) -> None:
        """Fail closed unless the COPY stream ended exactly at a record boundary."""
        last_end = self._record_ends[-1] if self._record_ends else 0
        if len(self._buf) > last_end:
            raise RemoteQueryFailure(
                'query_failed', 'The COPY stream ended before the open native record was complete.'
            )

    def _append_record(self, record: bytes, row_bound: int) -> None:
        """Buffer one complete framed record under the conservative final-JSON page bound."""
        limits = self._delivery.limits
        if len(record) > limits.max_row_bytes:
            raise RemoteQueryFailure(
                'row_too_large',
                'A single record exceeds maxRowBytes ({} > {} bytes).'.format(len(record), limits.max_row_bytes),
            )
        if not self._page_active:
            self._begin_page()
        while True:
            rows = len(self._record_ends)
            page_needed = self._page_bound + (1 if rows else 0) + row_bound
            if page_needed > limits.max_file_bytes and rows:
                self._close_page()
                # An oversize rejection leaves the uncommitted tail as the active page with
                # its bound recomputed, so a page begins only when the close consumed it all.
                if not self._page_active:
                    self._begin_page()
                continue
            if page_needed > limits.max_file_bytes:
                raise RemoteQueryFailure('row_too_large', 'A single row plus the page envelope exceeds maxFileBytes.')
            if self._stats.bytes_emitted + page_needed > limits.max_result_bytes:
                raise RemoteQueryFailure('max_result_bytes_exceeded', 'Result pages exceed maxResultBytes.')
            page_source_bytes = self._record_ends[-1] if rows else 0
            if page_source_bytes + len(record) > self._source_page_cap and rows:
                self._close_page()
                if not self._page_active:
                    self._begin_page()
                continue
            if page_source_bytes + len(record) > self._source_page_cap:
                raise RemoteQueryFailure('row_too_large', 'A single record exceeds the source page cap.')
            break
        if rows:
            self._page_bound += 1
        self._page_bound += row_bound
        self._record_bounds.append(row_bound)
        self._buf += record
        self._record_ends.append(len(self._buf))
        # The page checksum is fed each record's bytes exactly once.
        self._page_sha.update(record)
        self._page_hashed = len(self._buf)

    def finish(self) -> dict[str, Any]:
        """Close any open page and return the compact receipt from intake's authoritative totals."""
        if not self._page_active and self._descriptor.include_schema and self._stats.pages_emitted == 0:
            # Preserve schema discovery for an empty result: one zero-record source page makes
            # intake create the schema-bearing final page with empty ``data``.
            self._begin_page()
        while self._page_active:
            self._close_page()
        return self._finalize_run()

    def _finalize_run(self) -> dict[str, Any]:
        # Finalize includes its receipt verification and authoritative totals in its own phase.
        with self._timings.phase('finalize'):
            response = self._client.finalize_run(self._creds)
            verify_run_finalize_response(response, self._creds.upload_id)
            page_count, total_rows, total_bytes = finalize_totals(response)
        return {
            'uploadId': self._creds.upload_id,
            'pageCount': page_count,
            'totalRows': total_rows,
            'totalBytes': total_bytes,
        }

    def discard(self) -> None:
        """Release the buffered page; safe when no page is open."""
        self._page_active = False
        self._buf = bytearray()
        self._record_ends = array('q')
        if not self._native_mode:
            self._record_bounds = array('q')
        self._page_sha = hashlib.sha256()
        self._page_hashed = 0
        self._scan_pos = 0
        self._quote_parity = 0
        self._open_start = 0

    def _begin_page(self) -> None:
        if self._stats.pages_emitted >= self._delivery.limits.max_pages:
            raise RemoteQueryFailure('max_pages_exceeded', 'Page count reached maxPages.')
        if not self._native_mode:
            prefix = page_prefix(
                run_id=self._delivery.run_id,
                task_id=self._delivery.task_id,
                record_offset=self._stats.rows_emitted,
                agent_hostname=self._descriptor.agent_hostname,
                schema_json=self._schema_json,
            )
            # The envelope's record_offset digits grow with the run, so the fit is re-checked for
            # every page, not only once at construction.
            if len(prefix) + len(PAGE_SUFFIX) > self._delivery.limits.max_file_bytes:
                raise RemoteQueryFailure('row_too_large', 'Page envelope exceeds maxFileBytes.')
            self._page_bound = len(prefix) + len(PAGE_SUFFIX)
            self._record_bounds = array('q')
        self._page_record_offset = self._stats.rows_emitted
        self._page_active = True

    def _close_page(self) -> int:
        """Commit the buffered records as one source page at the next sequential index.

        One source page maps to one final page at the same index. When intake defensively
        rejects a page as ``final_page_too_large``, the buffered records are split in half and
        the same index is retried with fewer records — without requerying or reordering rows —
        and the uncommitted tail stays buffered as the active page. Returns the buffered
        bytes the acknowledged page consumed; the buffer's remaining bytes are the active
        page, so a caller scanning the buffer adjusts its offsets by that amount.
        """
        if self._stats.pages_emitted >= self._delivery.limits.max_pages:
            raise RemoteQueryFailure('max_pages_exceeded', 'Page count reached maxPages.')
        record_ends = self._record_ends
        record_bounds = self._record_bounds
        offset = self._page_record_offset
        total = len(record_ends)
        page_end = record_ends[-1] if total else 0
        # Intake's receipts are authoritative for final bytes, so the native grammar's
        # aggregate check uses them plus the page's own source bytes — a lower bound on its
        # final JSON, since every row object repeats the descriptor keys over its record.
        if self._native_mode and self._stats.bytes_emitted + page_end > self._delivery.limits.max_result_bytes:
            raise RemoteQueryFailure('max_result_bytes_exceeded', 'Result pages exceed maxResultBytes.')
        count = total
        receipt: Mapping[str, Any]
        while True:
            page_end = record_ends[count - 1] if count else 0
            if count == total:
                sha256_hex = self._page_digest(page_end)
            else:
                # A halved retry declares only the prefix it sends: one bounded pass over the
                # prefix, exceptional retry work rather than ordinary per-page cost.
                sha256_hex = hashlib.sha256(memoryview(self._buf)[:page_end]).hexdigest()
            metadata = SourcePageUploadMetadata(
                batch_index=self._stats.pages_emitted,
                record_offset=offset,
                source_bytes=page_end,
                rows=count,
                sha256_hex=sha256_hex,
            )
            body = _SourcePageBody(self._buf, page_end)
            try:
                self._guard()
                # The upload phase covers the whole put_source_page call (every attempt plus
                # backoff), so a halving retry measures its own upload wall; the receipt
                # verification below stays in the enclosing phase's bucket.
                with self._timings.page_upload():
                    receipt = self._client.put_source_page(self._creds, metadata, body)
                verify_source_page_receipt(receipt, metadata)
            except RemoteQueryFailure as failure:
                if failure.code != REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE or count <= 1:
                    raise
                count //= 2
                continue
            break
        # Intake is authoritative for the final page's bytes; stats never use source sizes.
        self._stats.pages_emitted += 1
        self._stats.rows_emitted += receipt['rows']
        self._stats.bytes_emitted += receipt['bytes']
        # Only the acknowledged page enters the upload distribution; a split attempt's wall
        # stays in the cumulative pageUploadMs.
        self._timings.note_page_acknowledged()
        acknowledged = record_ends[count - 1] if count else 0
        # The acknowledged bytes leave the buffer; the uncommitted tail is the active page.
        del self._buf[:acknowledged]
        if count == total:
            self._record_ends = array('q')
            if record_bounds is not None:
                self._record_bounds = array('q')
            self._page_active = False
        else:
            self._record_ends = array('q', (end - acknowledged for end in record_ends[count:]))
            if record_bounds is not None:
                self._record_bounds = array('q', record_bounds[count:])
            self._page_record_offset = offset + count
            if not self._native_mode:
                self._recompute_page_accounting()
        # The retained tail's checksum state: one bounded pass over its completed records.
        self._page_sha = hashlib.sha256()
        self._page_hashed = self._record_ends[-1] if self._record_ends else 0
        if self._page_hashed:
            self._page_sha.update(memoryview(self._buf)[: self._page_hashed])
        if self._native_mode:
            # The still-open record's framing state shifts with the buffer.
            self._scan_pos -= acknowledged
            self._open_start -= acknowledged
        return acknowledged

    def _page_digest(self, page_end: int) -> str:
        """The active page's source checksum, finalized over its last unhashed segment."""
        if self._page_hashed != page_end:
            self._page_sha.update(memoryview(self._buf)[self._page_hashed : page_end])
            self._page_hashed = page_end
        return self._page_sha.hexdigest()

    def _recompute_page_accounting(self) -> None:
        prefix_len = len(
            page_prefix(
                run_id=self._delivery.run_id,
                task_id=self._delivery.task_id,
                record_offset=self._page_record_offset,
                agent_hostname=self._descriptor.agent_hostname,
                schema_json=self._schema_json,
            )
        )
        self._page_bound = (
            prefix_len + len(PAGE_SUFFIX) + sum(self._record_bounds) + max(0, len(self._record_bounds) - 1)
        )


def raise_if_timed_out(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise RemoteQueryFailure('timeout', 'Remote query exceeded timeoutMs.', retryable=True)


def remaining_wall_ms(deadline: float) -> int:
    """The wall's remaining milliseconds, clamped to at least 1.

    Derived database timeouts must never reach 0: a zero PostgreSQL statement timeout or a
    zero ClickHouse ``max_execution_time`` would disable the database-side protection
    entirely instead of expiring the run.
    """
    return max(1, int((deadline - time.monotonic()) * 1000))


def raise_if_cancelled(check: Any) -> None:
    # The Agent runtime exposes ``is_cancelled`` as a plain bool attribute on the check
    # object, while other runtimes (and test doubles) may expose a callable hook; honor
    # both shapes. An absent attribute carries no cancellation signal.
    is_cancelled = getattr(check, 'is_cancelled', None)
    if is_cancelled is None:
        return
    cancelled = is_cancelled() if callable(is_cancelled) else is_cancelled
    if cancelled:
        raise RemoteQueryFailure('cancelled', 'Remote query run was cancelled.', retryable=True)


def normalize_target(target: Mapping[str, Any]) -> RemoteQueryTarget:
    try:
        return RemoteQueryTarget.model_validate(target)
    except ValidationError as e:
        # Pydantic's error object retains the raw request input even though the message is
        # built with include_input=False, so sever the chain: a traceback log of the
        # wrapper must not recover the rejected request.
        raise ValueError(validation_message(e)) from None


def is_query_allowlist_enabled() -> bool:
    try:
        config_value = datadog_agent.get_config(REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY)
    except Exception:
        # Fixed text only: the config layer's exception can quote configuration values.
        LOGGER.debug('Unable to read remote query allowlist configuration')
        return True

    if config_value is None:
        return True
    if isinstance(config_value, str):
        normalized_value = config_value.strip().lower()
        return normalized_value not in REMOTE_QUERY_DISABLE_ALLOWLIST_VALUES

    return is_affirmative(config_value)


REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY = 'remote_queries.execute.intake_test_drive'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX = 'test-drive-'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE = '1'


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH = 63


REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_PATTERN = re.compile(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?')


REMOTE_QUERY_UPLOAD_MAX_RETRIES = 4


REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS = 0.1


REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS = 5.0


REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS = 10


# The socket read timeout below is only a stall backstop: it fires when the socket is fully
# silent for its full span, so a slow-drip response never triggers it and it is not a wall on
# one request's duration. The attempt bound is that wall: it bounds one whole-page upload
# HTTP attempt below the effective public request ceiling measured through the intake data
# plane (~123-124 s, public frontend ingress), with more than 2x headroom, so a page that
# cannot fit the window (application work is budgeted at ~50 s) fails and retries instead of
# hanging until the edge kill or the stall backstop fires.
REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS = 55


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
    test_drive: str | None
    # The run-wide monotonic hard wall for this session's upload requests; None means the
    # request is not wall-scoped (best-effort abort, or a test double driving the client).
    wall_deadline: float | None = None
    # The validated request tracing carrier, injected as standard distributed-tracing headers
    # on every page, finalize, and abort request; None means the Agent supplied no context
    # (mixed versions) and the upload requests carry no tracing headers.
    trace_context: RemoteQueryTraceContext | None = None


class UploadClient(Protocol):
    def register_descriptor(self, creds: UploadCredentials, body: bytes) -> Mapping[str, Any]: ...

    def put_source_page(
        self, creds: UploadCredentials, page: SourcePageUploadMetadata, body: BinaryIO
    ) -> Mapping[str, Any]: ...

    def finalize_run(self, creds: UploadCredentials) -> Mapping[str, Any]: ...

    def abort(self, creds: UploadCredentials) -> None: ...


class UploadAttemptExpired(Exception):
    """One HTTP upload attempt passed its per-attempt deadline; the run itself may retry."""


class DeadlinedPageBody:
    """A file-like view over one page body that kills its HTTP attempt at a deadline.

    A page is fully buffered before its request starts, so the request carries a stable
    Content-Length and streams the body through ``read``. Checking the attempt deadline at
    every read bounds the attempt's wall-clock upload time even while the socket keeps
    accepting bytes, which the socket-level stall timeout cannot do. The position lives in
    the underlying buffer, so the retry loop's whole-page rewind applies to the view too.
    """

    def __init__(self, body: BinaryIO, deadline: float):
        self._body = body
        self._deadline = deadline

    def read(self, amount: int | None = -1) -> bytes:
        if time.monotonic() > self._deadline:
            raise UploadAttemptExpired('Page upload attempt exceeded its per-attempt deadline.')
        if amount is None or amount < 0:
            return self._body.read()
        return self._body.read(amount)

    def seek(self, *args: Any) -> Any:
        return self._body.seek(*args)

    def tell(self) -> int:
        return self._body.tell()


class RequestsUploadClient:
    """Direct HTTP upload client for its-agent-intake. Imports requests lazily."""

    def __init__(
        self,
        timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT,
        timings: RemoteQueryProducerTimings | None = None,
    ) -> None:
        self._timeout = timeout
        self._timings = timings if timings is not None else NULL_PRODUCER_TIMINGS

    def _headers(self, creds: UploadCredentials, content_type: str | None = None) -> dict[str, str]:
        headers = {
            'dd-api-key': creds.api_key,
            'dd-application-key': creds.app_key,
        }
        if content_type is not None:
            headers['Content-Type'] = content_type
        if creds.test_drive:
            test_drive_header = REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX + creds.test_drive
            headers[test_drive_header] = REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_VALUE
        if creds.trace_context is not None:
            # Tracing headers ride on every request built from these credentials — page,
            # finalize, abort, and each retry attempt — alongside the unchanged auth,
            # integrity, content-length, and Test Drive headers.
            headers.update(creds.trace_context.trace_headers())
        return headers

    def register_descriptor(self, creds: UploadCredentials, body: bytes) -> Mapping[str, Any]:
        """Register the immutable source-page descriptor; retries send byte-identical bodies."""
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/descriptor'.format(creds.base_url.rstrip('/'), creds.upload_id)
        _status, response_body = upload_with_retry(
            'POST', url, headers, body, self._timeout, deadline=creds.wall_deadline
        )
        return parse_json_object_response(response_body, 'descriptor registration')

    def put_source_page(
        self, creds: UploadCredentials, page: SourcePageUploadMetadata, buffer: BinaryIO
    ) -> Mapping[str, Any]:
        """Upload one record-complete source page and return the parsed final page receipt.

        The buffered page is streamed as the request body with stable declared source
        metadata; every bounded retry rewinds the buffer and resends byte-identical content
        for the same page index. Intake's defensive ``final_page_too_large`` rejection surfaces
        as its own failure code so the writer can split the buffered records and retry the
        same index.
        """
        headers = self._headers(creds, REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE)
        headers['X-DD-Source-Page-Bytes'] = str(page.source_bytes)
        headers['X-DD-Source-Page-Rows'] = str(page.rows)
        headers['X-DD-Record-Offset'] = str(page.record_offset)
        headers['X-DD-Source-Page-SHA256'] = page.sha256_hex
        # The buffer is complete and rewound before the request, so the exact source size is
        # declared as a stable Content-Length for one non-chunked request body.
        headers['Content-Length'] = str(page.source_bytes)
        url = '{}/uploads/{}/pages/{}'.format(creds.base_url.rstrip('/'), creds.upload_id, page.batch_index)
        _status, response_body = upload_with_retry(
            'PUT',
            url,
            headers,
            buffer,
            self._timeout,
            mapped_error_codes={
                REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE: REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE
            },
            deadline=creds.wall_deadline,
            timings=self._timings,
        )
        return parse_json_object_response(response_body, 'page upload')

    def finalize_run(self, creds: UploadCredentials) -> Mapping[str, Any]:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/finalize'.format(creds.base_url.rstrip('/'), creds.upload_id)
        _status, body = upload_with_retry('POST', url, headers, b'{}', self._timeout, deadline=creds.wall_deadline)
        return parse_json_object_response(body, 'run finalize')

    def abort(self, creds: UploadCredentials) -> None:
        headers = self._headers(creds, 'application/json')
        url = '{}/uploads/{}/abort'.format(creds.base_url.rstrip('/'), creds.upload_id)
        try:
            # Abort is cleanup: it must stay possible after the run wall expired (that is
            # exactly when it runs), so it carries no deadline.
            upload_with_retry('POST', url, headers, b'{}', self._timeout)
        except RemoteQueryFailure:
            LOGGER.debug('Remote query upload abort failed (best-effort)')


def parse_json_object_response(body: bytes, source: str) -> Mapping[str, Any]:
    """Parse one intake response, failing closed on a non-JSON or non-object body."""
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake {} response was not valid JSON.'.format(source))
    if not isinstance(parsed, Mapping):
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake {} response was not a JSON object.'.format(source)
        )
    return parsed


def verify_descriptor_receipt_field(response: Mapping[str, Any], field: str, expected: Any) -> None:
    reported = response.get(field)
    if type(reported) is not type(expected) or reported != expected:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake descriptor response reported {} {!r} instead of {!r}.'.format(field, reported, expected),
        )


def verify_descriptor_response(
    response: Mapping[str, Any],
    upload_id: str,
    descriptor: RemoteQueryUploadDescriptor,
    request_bytes: bytes,
) -> None:
    """Fail closed unless intake's descriptor receipt exactly confirms the registration.

    Intake pins the receipt as exactly ``upload_id``, ``format_version``, ``include_schema``,
    ``columns``, and ``sha256`` over the canonical descriptor bytes — the same bytes the
    producer registered — so the key set is fixed, every field is required, and every value
    must match exactly. A missing, mistyped, mismatched, or unknown extra key is an invalid
    receipt: registration is the gate before any result row flows, so a receipt that does
    not confirm the descriptor never admits rows.
    """
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake descriptor response was not a JSON object.')
    extra_keys = set(response) - {'upload_id', 'format_version', 'include_schema', 'columns', 'sha256'}
    if extra_keys:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake descriptor response carried unknown key(s): {}.'.format(', '.join(sorted(extra_keys))),
        )
    verify_descriptor_receipt_field(response, 'upload_id', upload_id)
    verify_descriptor_receipt_field(response, 'format_version', descriptor.format_version)
    verify_descriptor_receipt_field(response, 'include_schema', descriptor.include_schema)
    verify_descriptor_receipt_field(response, 'columns', len(descriptor.columns))
    verify_descriptor_receipt_field(response, 'sha256', hashlib.sha256(request_bytes).hexdigest())


def verify_source_page_receipt(response: Mapping[str, Any], page: SourcePageUploadMetadata) -> None:
    """Fail closed unless intake's final page receipt matches the source page identity.

    ``batch_index``, ``record_offset``, and ``rows`` must match exactly: one source page maps
    to one final page with the same rows and offset. ``key``, ``bytes``, and ``sha256`` are
    intake-derived final metadata, so they are validated for shape only — never compared to
    the source page's own bytes or checksum. The final key's exact value is verified
    downstream by its-agent against intake's authoritative result.
    """
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake page upload response was not a JSON object.')
    key = response.get('key')
    if not isinstance(key, str) or not key:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake page upload response did not carry a usable object key.'
        )
    verify_page_receipt_field(response, 'batch_index', page.batch_index)
    verify_page_receipt_field(response, 'record_offset', page.record_offset)
    verify_page_receipt_field(response, 'rows', page.rows)
    final_bytes = response.get('bytes')
    if type(final_bytes) is not int or final_bytes < 0:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake page upload response did not report usable final bytes.'
        )
    final_sha256 = response.get('sha256')
    if not isinstance(final_sha256, str) or re.fullmatch(r'[0-9a-f]{64}', final_sha256) is None:
        raise RemoteQueryFailure(
            'invalid_receipt', 'its-agent-intake page upload response did not report a valid final sha256.'
        )


def finalize_totals(response: Mapping[str, Any]) -> tuple[int, int, int]:
    """Intake's authoritative run totals: ``(page_count, total_rows, total_bytes)``.

    Run finalization is the authority for the compact completion receipt, so a response that
    does not report all three totals is an invalid receipt rather than a fallback to local
    source accounting.
    """
    totals = []
    for field in ('page_count', 'total_rows', 'total_bytes'):
        reported = response.get(field)
        if type(reported) is not int or reported < 0:
            raise RemoteQueryFailure(
                'invalid_receipt', 'its-agent-intake run finalize response did not report {}.'.format(field)
            )
        totals.append(reported)
    return totals[0], totals[1], totals[2]


def verify_page_receipt_field(response: Mapping[str, Any], field: str, expected: int) -> None:
    reported = response.get(field)
    if type(reported) is not int or reported != expected:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake page upload response reported {} {!r} instead of {}.'.format(field, reported, expected),
        )


def verify_run_finalize_response(response: Mapping[str, Any], upload_id: str) -> None:
    """Fail closed when intake's authoritative response reports a different upload session."""
    if not isinstance(response, Mapping):
        raise RemoteQueryFailure('invalid_receipt', 'its-agent-intake run finalize response was not a JSON object.')
    reported_upload_id = response.get('upload_id')
    if reported_upload_id is None or reported_upload_id == '':
        # The receipt's totals are already intake-derived, and intake's authoritative result
        # is verified by its-agent downstream, so an absent identity echo is accepted.
        return
    if str(reported_upload_id) != upload_id:
        raise RemoteQueryFailure(
            'invalid_receipt',
            'its-agent-intake run finalize response reported upload id {!r} instead of {!r}.'.format(
                str(reported_upload_id), upload_id
            ),
        )


def is_transient_upload_status(status: int) -> bool:
    return status == 408 or status == 429 or status >= 500


def parse_error_code(body: bytes) -> str | None:
    """Read intake's public error code from a rejection body, if it carries one."""
    if not body or not body.strip():
        return None
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(parsed, Mapping):
        return None
    error = parsed.get('error')
    if not isinstance(error, Mapping):
        return None
    code = error.get('code')
    return code if isinstance(code, str) else None


def upload_with_retry(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | BinaryIO,
    timeout: tuple[int, int] = REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT,
    mapped_error_codes: Mapping[str, str] | None = None,
    deadline: float | None = None,
    timings: RemoteQueryProducerTimings | None = None,
) -> tuple[int, bytes]:
    """Send one intake request with bounded retries; ``deadline`` is the run-wide wall.

    With a deadline, no attempt starts after the wall and every whole-page attempt is
    additionally bounded by ``REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS`` capped at the wall,
    so a bounded retry sequence can never meaningfully extend the wall. A page attempt
    that passes its own bound is killed mid-body and retried with whole-page rewind.

    ``timings``, when given, counts each HTTP attempt (and each retry beyond a page's
    first attempt) on the producer accumulator; only ``put_source_page`` passes one, so
    descriptor, finalize, and abort attempts are not page upload attempts.
    """
    import requests  # lazy: only the POC upload path needs it

    timings = timings if timings is not None else NULL_PRODUCER_TIMINGS
    # The default is an empty mapping, normalized once here: descriptor, finalize, and abort
    # map no intake error codes, so their terminal rejections fail closed as upload_failed.
    if mapped_error_codes is None:
        mapped_error_codes = {}
    backoff = REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS
    # The exhausted sequence's diagnostic: intake's HTTP status (a public counter) or one of
    # the fixed failure categories assigned below, never the caught exception's text or
    # repr — a transport exception can quote the URL, the request body, or credentials.
    last_failure = 'transport failure'
    for attempt in range(REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1):
        if deadline is not None:
            raise_if_timed_out(deadline)
        if not isinstance(body, bytes):
            # Whole-page retry: rewind the buffer so every attempt sends byte-identical
            # content for the same page index with unchanged declared metadata.
            body.seek(0)
        request_body: bytes | BinaryIO = body
        if deadline is not None and not isinstance(body, bytes):
            attempt_deadline = min(deadline, time.monotonic() + REMOTE_QUERY_UPLOAD_HTTP_ATTEMPT_SECONDS)
            request_body = DeadlinedPageBody(body, attempt_deadline)
        timings.note_upload_attempt(retry=attempt > 0)
        try:
            resp = requests.request(method, url, headers=dict(headers), data=request_body, timeout=timeout)
        except UploadAttemptExpired:
            last_failure = 'the page upload attempt exceeded its per-attempt deadline'
        except requests.exceptions.RequestException:
            last_failure = 'transport failure'
        else:
            if 200 <= resp.status_code < 300:
                return resp.status_code, resp.content
            if is_transient_upload_status(resp.status_code):
                last_failure = 'HTTP status {}'.format(resp.status_code)
            else:
                error_code = parse_error_code(resp.content)
                mapped_code = mapped_error_codes.get(error_code) if error_code is not None else None
                if mapped_code is not None:
                    # A terminal rejection intake defines a producer behavior for (today the
                    # defensive final_page_too_large), surfaced as its own failure code.
                    raise RemoteQueryFailure(
                        mapped_code, 'its-agent-intake rejected the upload with error code {}.'.format(error_code)
                    )
                raise RemoteQueryFailure(
                    'upload_failed', 'upload to its-agent-intake rejected with status {}'.format(resp.status_code)
                )
        if attempt == REMOTE_QUERY_UPLOAD_MAX_RETRIES:
            break
        time.sleep(backoff)
        backoff = min(backoff * 2, REMOTE_QUERY_UPLOAD_MAX_BACKOFF_SECONDS)
    raise RemoteQueryFailure(
        'upload_failed',
        'upload to its-agent-intake failed after {} attempts: {}'.format(
            REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, last_failure
        ),
        retryable=True,
    )


def get_agent_config(key: str) -> str:
    try:
        value = datadog_agent.get_config(key)
    except Exception:
        # Fixed text and the fixed key name only: the config layer's exception can quote
        # configuration values.
        LOGGER.debug('Unable to read agent config %s', key)
        return ''
    if value is None:
        return ''
    return str(value)


def validate_test_drive_name(value: str | None) -> str | None:
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
        # The configured value never reaches the log; only the verdict and the grammar it
        # failed. The value is customer configuration text, not a safe diagnostic.
        LOGGER.warning(
            'Ignoring invalid remote query intake Test Drive name: it must be 1-%d '
            'lowercase ASCII alphanumerics or hyphens, starting and ending with an alphanumeric.',
            REMOTE_QUERY_UPLOAD_TEST_DRIVE_NAME_MAX_LENGTH,
        )
        return None
    return name


def resolve_upload_credentials(
    delivery: RemoteQueryResultDelivery,
    started_at: float,
    trace_context: RemoteQueryTraceContext | None = None,
) -> UploadCredentials:
    """Build the session credentials, carrying the run-wide wall for upload retries.

    The wall is derived from the same started-at origin and delivered timeout the producer
    uses for its monotonic guard, so the guard and the upload client enforce one deadline.
    ``trace_context`` is the request's validated tracing carrier; when given it rides on the
    credentials so every upload request carries the standard tracing headers, and when absent
    the request behavior is unchanged.
    """
    test_drive = validate_test_drive_name(get_agent_config(REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY))
    return UploadCredentials(
        base_url=delivery.base_url,
        upload_id=delivery.upload_id,
        api_key=get_agent_config('api_key'),
        app_key=get_agent_config('app_key'),
        test_drive=test_drive,
        wall_deadline=started_at + delivery.limits.timeout_ms / 1000,
        trace_context=trace_context,
    )


def safe_abort(client: UploadClient, creds: UploadCredentials) -> None:
    if not creds.base_url or not creds.upload_id:
        return
    try:
        client.abort(creds)
    except Exception:
        # Fixed text only: the caught exception can quote the URL, the request body, or
        # credentials embedded in a transport error string.
        LOGGER.debug('Remote query upload abort failed (best-effort)')


def started_metadata(request: RemoteQueryRequest) -> dict[str, Any]:
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
            'baseUrl': delivery.base_url,
            'artifactVersion': delivery.artifact_version,
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


def succeeded_metadata(
    receipt: Mapping[str, Any],
    stats: RemoteQueryRunStats,
    started_at: float,
    timings: RemoteQueryProducerTimings | None = None,
) -> dict[str, Any]:
    metadata = {
        'status': 'SUCCEEDED',
        'upload_receipt': dict(receipt),
        'stats': stats_metadata(stats, started_at),
    }
    if timings is not None:
        metadata['executionDiagnostics'] = timings.metadata(stats)
    return metadata


def stats_metadata(stats: RemoteQueryRunStats, started_at: float) -> dict[str, Any]:
    return {
        'rowsEmitted': stats.rows_emitted,
        'pagesEmitted': stats.pages_emitted,
        'bytesEmitted': stats.bytes_emitted,
        'elapsedMs': elapsed_ms(started_at),
    }


def failed_event(
    code: str,
    message: str,
    retryable: bool = False,
    stats: Mapping[str, Any] | None = None,
    elapsed_ms: int | None = None,
    execution_diagnostics: Mapping[str, Any] | None = None,
) -> RemoteQueryEvent:
    metadata: dict[str, Any] = {
        'status': 'FAILED',
        'error': {'code': code, 'message': message, 'retryable': retryable},
    }
    if stats is not None:
        metadata['stats'] = dict(stats)
    elif elapsed_ms is not None:
        metadata['stats'] = {'elapsedMs': elapsed_ms}
    if execution_diagnostics is not None:
        metadata['executionDiagnostics'] = dict(execution_diagnostics)
    return RemoteQueryEvent('error', metadata)


def matched_resolve_event(
    host: str | None,
    port: int | None,
    configured_dbname: str | None,
    resolved_dbname: str,
    database_instance: str | None,
) -> RemoteQueryEvent:
    """The per-check MATCHED resolve verdict: sanitized effective identity, no payload.

    ``host``, ``port``, ``configured_dbname``, and ``database_instance`` identify the matched
    check as the integration sees it; ``resolved_dbname`` is the database admitted for the
    target. The keys are pinned by the cross-repo resolve contract and feed the Agent's
    match fingerprint: never credentials or raw config. Only identity fields that genuinely
    do not exist for the matched check are omitted.
    """
    match: dict[str, Any] = {}
    if host is not None:
        match['host'] = host
    if port is not None:
        match['port'] = port
    if configured_dbname is not None:
        match['configuredDbname'] = configured_dbname
    match['resolvedDbname'] = resolved_dbname
    if database_instance is not None:
        match['databaseInstance'] = database_instance
    return RemoteQueryEvent('final', {'status': 'MATCHED', 'match': match})


def emit_event(emit: RemoteQueryEmit, event: RemoteQueryEvent) -> None:
    emit(event.event_type, json.dumps(event.metadata, default=str), event.payload)


def elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def validation_message(error: ValidationError) -> str:
    details = []
    for item in error.errors(include_input=False):
        location = validation_location(item.get('loc', ()))
        message = item.get('msg', 'Invalid value')
        if location:
            details.append(f'{location}: {message}')
        else:
            details.append(message)
    return 'Invalid remote query request: {}'.format('; '.join(details))


def validation_location(location: tuple[Any, ...]) -> str:
    return '.'.join(str(part) for part in location)
