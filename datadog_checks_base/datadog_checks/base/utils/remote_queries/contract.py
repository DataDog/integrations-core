# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query contract."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    Tag,
    ValidationError,
    field_validator,
    model_validator,
)

REMOTE_QUERY_UPLOAD_MAX_FILE_BYTES = 128 * 1024 * 1024


REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES = 100 * 1024 * 1024 * 1024


REMOTE_QUERY_DEFAULT_TIMEOUT_MS = 30_000


# The consumer-visible final page contract version, an exact semver string mirrored from
# intake's final page writer. The RFC-format page contract labels every page
# `contract_version` with this string; the producer emits the same bytes only to bound the
# final pages it asks intake to build.
REMOTE_QUERY_PAGE_CONTRACT_VERSION = '1.0.0'


REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION = 'csv-json-cell-v1'


# The opt-in sessionless upload: independently routed pages, no upload session, and a bounded
# completion proposal instead of a finalize receipt. The experiment ceilings below bound what
# its `session_info` may ask for; they are a POC profile, never raised by the Agent or the integration.
REMOTE_QUERY_SESSIONLESS_MAX_FILE_BYTES = 16 * 1024 * 1024


REMOTE_QUERY_SESSIONLESS_MAX_RESULT_BYTES = 1024 * 1024 * 1024


REMOTE_QUERY_SESSIONLESS_MAX_PAGES = 128


REMOTE_QUERY_SESSIONLESS_MAX_COLUMNS = 1024


# The encoded descriptor travels in every page's metadata part, so it is bounded as a whole.
REMOTE_QUERY_SESSIONLESS_MAX_DESCRIPTOR_BYTES = 1024 * 1024


REMOTE_QUERY_SESSIONLESS_MAX_COMPLETION_BYTES = 16 * 1024


REMOTE_QUERY_SESSIONLESS_OBJECT_ID_PATTERN = re.compile(
    r'\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z'
)


RemoteQueryLogicalType = Literal[
    'boolean', 'integer', 'decimal', 'float', 'string', 'temporal', 'json', 'binary', 'vendor'
]


def canonical_json_text(value: Any) -> str:
    """The canonical JSON text: raw non-ASCII, escaped JSON controls, quote, and backslash."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def canonical_json_bytes(value: Any) -> bytes:
    """The canonical JSON text as UTF-8 bytes, failing closed on unencodable text.

    A string that reached Python's text layer but cannot be encoded (a lone surrogate from
    a driver or a server payload) is a fixed `unsupported_value` failure, never an
    uncaught `UnicodeEncodeError` mid-upload.
    """
    try:
        return canonical_json_text(value).encode('utf-8')
    except UnicodeEncodeError:
        raise RemoteQueryFailure('unsupported_value', 'A canonical JSON string cannot be encoded as UTF-8.') from None


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
    """One wire column. Adapters supply and validate source-format-specific metadata."""

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


class RemoteQueryUploadDescriptor(BaseModel):
    """Immutable source metadata registered before any rows. The adapter chooses its format."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    format_version: StrictStr
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
    """The session-backed `session_info`: the backend-injected upload instructions.

    Its `uploadId` is what selects this shape. The Agent transports `session_info` as an
    opaque JSON object, so this model is the only strict validator of its current fields.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    run_id: StrictStr = Field(alias='runId', min_length=1)
    task_id: StrictStr = Field(alias='taskId', min_length=1)
    upload_id: StrictStr = Field(alias='uploadId', min_length=1)
    base_url: StrictStr = Field(alias='baseUrl', min_length=1)
    limits: RemoteQueryUploadLimits


class RemoteQuerySessionlessLimits(RemoteQueryUploadLimits):
    """The delivered limits of a sessionless run, additionally bounded by the experiment ceilings.

    The numeric types and relations are the session limits'; the ceilings are intake's
    experimental profile, so a delivery that asks for more is rejected instead of being
    clamped or sent to intake only to be refused page by page.
    """

    @model_validator(mode='after')
    def validate_experiment_ceilings(self) -> 'RemoteQuerySessionlessLimits':
        ceilings = (
            ('maxFileBytes', self.max_file_bytes, REMOTE_QUERY_SESSIONLESS_MAX_FILE_BYTES),
            ('maxResultBytes', self.max_result_bytes, REMOTE_QUERY_SESSIONLESS_MAX_RESULT_BYTES),
            ('maxPages', self.max_pages, REMOTE_QUERY_SESSIONLESS_MAX_PAGES),
            ('maxColumns', self.max_columns, REMOTE_QUERY_SESSIONLESS_MAX_COLUMNS),
            ('maxSchemaBytes', self.max_schema_bytes, REMOTE_QUERY_SESSIONLESS_MAX_DESCRIPTOR_BYTES),
        )
        for name, value, ceiling in ceilings:
            if value > ceiling:
                raise ValueError('{} must not exceed the sessionless experiment ceiling of {}'.format(name, ceiling))
        return self


class RemoteQuerySessionlessResultDelivery(BaseModel):
    """The sessionless `session_info`: the backend-injected instructions of the opt-in sessionless upload.

    There is no upload session: no upload id, bucket, account routing, token, or scan stamp.
    The absence of `uploadId` is what selects this shape.
    `runId` keeps its wire name but is the fresh per-delivery crawl id, never the ITS run id.
    `scanSensitiveData` is a required strict boolean: it is requested of intake, which
    decides and records whether it actually scanned.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    run_id: StrictStr = Field(alias='runId', min_length=1)
    task_id: StrictStr = Field(alias='taskId', min_length=1)
    base_url: StrictStr = Field(alias='baseUrl', min_length=1)
    scan_sensitive_data: StrictBool = Field(alias='scanSensitiveData')
    limits: RemoteQuerySessionlessLimits


RemoteQueryDelivery = RemoteQueryResultDelivery | RemoteQuerySessionlessResultDelivery


def delivery_variant(value: Any) -> str:
    """Select the `session_info` model from the input: `uploadId` present means session-backed.

    There is no mode or version field: a session-backed run is the one that names an upload
    session. Each model is strict with no unknown keys, so a mixed shape (an `uploadId` with
    `scanSensitiveData`, or a sessionless object missing it) fails validation instead of
    being silently read as the other mode.
    """
    if isinstance(value, Mapping):
        return 'session' if 'uploadId' in value else 'sessionless'
    return 'session' if isinstance(value, RemoteQueryResultDelivery) else 'sessionless'


RemoteQueryDeliveryInput = Annotated[
    Annotated[RemoteQueryResultDelivery, Tag('session')]
    | Annotated[RemoteQuerySessionlessResultDelivery, Tag('sessionless')],
    Discriminator(delivery_variant),
]


REMOTE_QUERY_TRACE_ID_HEADER = 'x-datadog-trace-id'


REMOTE_QUERY_TRACE_PARENT_ID_HEADER = 'x-datadog-parent-id'


REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER = 'x-datadog-sampling-priority'


REMOTE_QUERY_TRACE_ID_PATTERN = re.compile(r'\A[0-9]+\Z')


REMOTE_QUERY_TRACE_ID_MAX = (1 << 64) - 1


REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_KEEP_VALUES = frozenset((1, 2))


class RemoteQueryTraceContext(BaseModel):
    """The optional Agent-supplied tracing carrier for one execution's upload requests."""

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
    session_info: RemoteQueryDeliveryInput = Field(alias='session_info')
    trace_context: RemoteQueryTraceContext | None = Field(default=None, alias='traceContext')


class RemoteQueryResolveRequest(BaseModel):
    """A resolve_target request: one strict target-only operation, nothing else.

    The Agent's resolve dispatch carries only the operation and the target. Strict validation
    rejects every execution field — query, includeSchema, session_info, credentials, a match
    fingerprint, or anything else — so a resolve sweep can never carry SQL or upload
    instructions.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    operation: Literal['resolve_target'] = Field(alias='operation')
    target: RemoteQueryTarget


@dataclass
class RemoteQueryRunStats:
    """Accepted page accounting, replaced by authoritative intake totals on finalization."""

    rows_emitted: int = 0
    pages_emitted: int = 0
    bytes_emitted: int = 0


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


def sessionless_page_metadata_bytes(
    delivery: RemoteQuerySessionlessResultDelivery,
    page: SourcePageUploadMetadata,
    descriptor_json: bytes,
) -> bytes:
    """The strict metadata part of one sessionless page request, in intake's field order.

    Every page repeats the complete descriptor because the requests are independent. The
    bytes are a pure function of the delivery, the page identity, and the canonical
    descriptor bytes, so every retry of one page request is byte-identical. The crawl id is
    the delivery's `runId`; no org, bucket, path, policy, or scan stamp is ever sent.
    """
    return b''.join(
        (
            b'{"task_id":',
            canonical_json_bytes(delivery.task_id),
            b',"crawl_id":',
            canonical_json_bytes(delivery.run_id),
            b',"page_index":%d,"record_offset":%d,"source_bytes":%d,"source_rows":%d,'
            % (
                page.batch_index,
                page.record_offset,
                page.source_bytes,
                page.rows,
            ),
            b'"scan_sensitive_data":',
            b'true' if delivery.scan_sensitive_data else b'false',
            b',"descriptor":',
            descriptor_json,
            b'}',
        )
    )


class SessionlessPageReceipt(BaseModel):
    """Intake's exact 201 receipt for one accepted sessionless page: strict, no unknown fields."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    object_id: StrictStr
    page_index: StrictInt = Field(ge=0)
    record_offset: StrictInt = Field(ge=0)
    rows: StrictInt = Field(ge=0)
    bytes: StrictInt = Field(gt=0)

    @field_validator('object_id')
    @classmethod
    def validate_object_id(cls, value: str) -> str:
        if REMOTE_QUERY_SESSIONLESS_OBJECT_ID_PATTERN.match(value) is None:
            raise ValueError('object_id must be a canonical lowercase UUID')
        return value


class SessionlessCompletionReceipt(BaseModel):
    """The bounded completion proposal the integration reports: ordered object ids and totals.

    Every field is required and the shape is exact. The ids and totals are claims the
    trusted worker verifies against intake's stored objects, never authority themselves, and
    the proposal carries no scan stamp. At most one id per logical page, so the count is the
    page count; an empty proposal is the zero-page, zero-row, zero-byte empty result.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    object_ids: tuple[StrictStr, ...] = Field(alias='objectIds', max_length=REMOTE_QUERY_SESSIONLESS_MAX_PAGES)
    page_count: StrictInt = Field(alias='pageCount', ge=0)
    total_rows: StrictInt = Field(alias='totalRows', ge=0)
    total_bytes: StrictInt = Field(alias='totalBytes', ge=0)

    @field_validator('object_ids')
    @classmethod
    def validate_object_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(REMOTE_QUERY_SESSIONLESS_OBJECT_ID_PATTERN.match(object_id) is None for object_id in value):
            raise ValueError('objectIds must be canonical lowercase UUIDs')
        if len(set(value)) != len(value):
            raise ValueError('objectIds must be unique')
        return value

    @model_validator(mode='after')
    def validate_totals(self) -> 'SessionlessCompletionReceipt':
        if self.page_count != len(self.object_ids):
            raise ValueError('pageCount must equal the number of objectIds')
        if not self.object_ids and (self.total_rows or self.total_bytes):
            raise ValueError('an empty proposal must report zero rows and bytes')
        return self

    def wire(self) -> dict[str, Any]:
        """The AP camelCase receipt, failing closed when its serialization exceeds the cap."""
        wire = self.model_dump(by_alias=True, mode='json')
        if len(canonical_json_bytes(wire)) > REMOTE_QUERY_SESSIONLESS_MAX_COMPLETION_BYTES:
            raise RemoteQueryFailure('invalid_receipt', 'The sessionless completion proposal exceeds its size cap.')
        return wire


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
