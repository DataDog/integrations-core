# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Execute remote queries through Postgres COPY in a read-only transaction.

Describe the result without fetching it, then execute the query once through COPY.
CopyPageWriter frames the native CSV; the shared uploader only sends complete records
and verifies intake receipts. The Agent callback carries status and the final receipt,
never result bytes. resolve_target and execution use the same configured database scope.
"""

from __future__ import annotations

import logging
import time
import uuid
from array import array
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import psycopg.errors as psycopg_errors
from pydantic import ValidationError

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import timing as rq_timing
from datadog_checks.base.utils.remote_queries import upload as rq_upload

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


@dataclass(frozen=True)
class ResultColumn:
    """One described result field: its column name, type OID, and type modifier."""

    name: str
    type_oid: int
    type_modifier: int | None


# ---------------------------------------------------------------------------
# Result description, vendor types, and the upload descriptor
# ---------------------------------------------------------------------------

# The catalog lookup resolves each described type through domain chains to its effective
# base type, decides whether that effective type is an array (typcategory 'A'), and for
# array columns resolves the ELEMENT type's own domain chain to read its typdelim — the
# delimiter PostgreSQL's own array parser uses for that element family (box is semicolon-
# delimited, for example). Depth bounds keep a pathological domain loop from recursing
# forever; DISTINCT ON keeps the deepest (fully resolved) walk row per requested type.
VENDOR_TYPE_QUERY = """
WITH RECURSIVE
requested AS (
    SELECT t.type_oid::oid AS type_oid, t.type_mod::int4 AS type_mod
    FROM unnest(%s::text[], %s::text[]) AS t(type_oid, type_mod)
),
type_walk(origin, type_oid, depth) AS (
    SELECT r.type_oid, r.type_oid, 0 FROM requested r
    UNION ALL
    SELECT w.origin, b.typbasetype, w.depth + 1
    FROM type_walk w
    JOIN pg_catalog.pg_type b ON b.oid = w.type_oid AND b.typtype = 'd'
    WHERE w.depth < 32
),
effective AS (
    SELECT DISTINCT ON (origin) origin, type_oid FROM type_walk ORDER BY origin, depth DESC
),
element_walk(origin, type_oid, depth) AS (
    SELECT e.origin, a.typelem, 0
    FROM effective e
    JOIN pg_catalog.pg_type a ON a.oid = e.type_oid
    WHERE a.typcategory = 'A'
    UNION ALL
    SELECT w.origin, b.typbasetype, w.depth + 1
    FROM element_walk w
    JOIN pg_catalog.pg_type b ON b.oid = w.type_oid AND b.typtype = 'd'
    WHERE w.depth < 32
),
element AS (
    SELECT DISTINCT ON (origin) origin, type_oid FROM element_walk ORDER BY origin, depth DESC
)
SELECT r.type_oid, r.type_mod,
       pg_catalog.format_type(r.type_oid, r.type_mod) AS vendor_data_type,
       (a.typcategory = 'A') AS is_array,
       pg_catalog.ascii(e.typdelim::text) AS element_delimiter
FROM requested r
JOIN effective f ON f.origin = r.type_oid
JOIN pg_catalog.pg_type a ON a.oid = f.type_oid
LEFT JOIN element el ON el.origin = r.type_oid
LEFT JOIN pg_catalog.pg_type e ON e.oid = el.type_oid
"""


@dataclass(frozen=True)
class ResolvedVendorType:
    """One described type's vendor name plus its catalog-resolved array metadata."""

    vendor_data_type: str
    is_array: bool
    # The element delimiter's internal-char byte code, or None for non-array types.
    element_delimiter: int | None


def described_columns(cursor: Any) -> list[ResultColumn]:
    """Read the ordered result column names, type OIDs, and type modifiers.

    A named cursor's description is available immediately after the DECLARE, including for
    zero-row results, so a schema-bearing empty page can still be produced. psycopg keeps
    the raw RowDescription type modifier on the `Column` object (`_fmod`); it is the
    exact value `pg_catalog.format_type` expects.
    """
    description = getattr(cursor, 'description', None)
    if not description:
        raise rq_contract.RemoteQueryFailure('query_failed', 'Query returned no result description.')

    columns = []
    for described in description:
        name = described.name
        if not isinstance(name, str) or not name:
            raise rq_contract.RemoteQueryFailure(
                'schema_unavailable', 'Result description carried an empty column name.'
            )
        type_oid = described.type_code
        if not isinstance(type_oid, int):
            raise rq_contract.RemoteQueryFailure(
                'schema_unavailable', 'Result description carried a non-integer type oid.'
            )
        columns.append(ResultColumn(name=name, type_oid=type_oid, type_modifier=getattr(described, '_fmod', None)))
    return columns


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


def resolve_vendor_types(
    control_cursor: Any, columns: Sequence[ResultColumn]
) -> dict[tuple[int, int], ResolvedVendorType]:
    """Resolve every DISTINCT (type_oid, type_modifier) pair with one parameterized lookup.

    The catalog query runs in the same read-only transaction and statement timeout scope as
    the user query. Types are passed as text arrays and cast element-wise (text -> oid and
    text -> int4 both cast via I/O), which is version-stable and avoids psycopg's
    element-width-dependent int array dump OIDs. Each resolved type carries its vendor
    name, whether its domain-resolved effective type is an array, and — for array types —
    the byte code of the element type's own typdelim, resolved through the element's
    domain chain.
    """
    distinct_pairs = sorted({(column.type_oid, column.type_modifier) for column in columns})
    if any(pair[1] is None for pair in distinct_pairs):
        raise rq_contract.RemoteQueryFailure(
            'schema_unavailable', 'Result description did not expose type modifiers for every column.'
        )

    oids = [str(pair[0]) for pair in distinct_pairs]
    type_modifiers = [str(pair[1]) for pair in distinct_pairs]
    control_cursor.execute(VENDOR_TYPE_QUERY, (oids, type_modifiers))
    rows = control_cursor.fetchall()

    type_map: dict[tuple[int, int], ResolvedVendorType] = {}
    for row in rows:
        oid, type_modifier, vendor_data_type, is_array, element_delimiter = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
        )
        if not isinstance(vendor_data_type, str) or not vendor_data_type:
            raise rq_contract.RemoteQueryFailure(
                'schema_unavailable', 'pg_catalog.format_type returned an unusable type name.'
            )
        type_map[(oid, type_modifier)] = ResolvedVendorType(
            vendor_data_type=vendor_data_type,
            is_array=bool(is_array),
            element_delimiter=element_delimiter,
        )

    missing = [pair for pair in distinct_pairs if pair not in type_map]
    if missing:
        raise rq_contract.RemoteQueryFailure(
            'schema_unavailable',
            'pg_catalog.format_type lookup did not resolve {} requested type(s).'.format(len(missing)),
        )
    return type_map


# Descriptor logical types for the built-in OID families. Any array family (a vendor type
# rendered with an `[]` suffix) carries a JSON array, decoded by intake from the element
# type the vendor name carries; custom types, domains, and extensions have no stable
# cross-vendor family, so they map to `vendor` — intake falls back to the family's
# documented string form, never a guess from contents.
POSTGRES_LOGICAL_TYPE_BY_OID = {
    16: 'boolean',  # bool
    17: 'binary',  # bytea
    18: 'string',  # char
    19: 'string',  # name
    20: 'integer',  # int8
    21: 'integer',  # int2
    23: 'integer',  # int4
    25: 'string',  # text
    26: 'integer',  # oid
    114: 'json',  # json
    700: 'float',  # float4
    701: 'float',  # float8
    1700: 'decimal',  # numeric
    790: 'vendor',  # money (locale-dependent text)
    829: 'vendor',  # macaddr
    869: 'vendor',  # inet
    650: 'vendor',  # cidr
    1042: 'string',  # bpchar
    1043: 'string',  # varchar
    1082: 'temporal',  # date
    1083: 'temporal',  # time
    1114: 'temporal',  # timestamp
    1184: 'temporal',  # timestamptz
    1186: 'temporal',  # interval
    1266: 'temporal',  # timetz
    2249: 'json',  # record
    2950: 'string',  # uuid
    3802: 'json',  # jsonb
}


def logical_type_for_column(column: ResultColumn, vendor_data_type: str) -> str:
    """Map one described column to a closed descriptor logical type, deterministically."""
    if vendor_data_type.endswith('[]'):
        return 'json'
    return POSTGRES_LOGICAL_TYPE_BY_OID.get(column.type_oid, 'vendor')


def build_upload_descriptor(
    request: rq_contract.RemoteQueryRequest,
    columns: Sequence[ResultColumn],
    type_map: Mapping[tuple[int, int], ResolvedVendorType],
    agent_hostname: str,
) -> rq_contract.RemoteQueryUploadDescriptor:
    """Build the immutable source-page descriptor from the described result columns.

    The vendor type names always come from `pg_catalog.format_type` — schema or not —
    because the descriptor is registered once, before any result record is read, and intake
    stamps the schema (when requested) into every final page from it. The format version
    selects the native COPY CSV cell grammar, so intake decodes the source pages by these
    column types instead of canonical JSON tokens. Every array column (a vendor name
    rendered with an `[]` suffix) carries its element type's own typdelim — resolved
    through the catalog, never guessed — so intake splits the native array literal on
    exactly the separator PostgreSQL uses; a rendered array whose catalog type disagrees
    fails closed instead of describing an undecodable column.
    """
    descriptor_columns = []
    for column in columns:
        resolved = type_map[(column.type_oid, column.type_modifier)]
        vendor_data_type = resolved.vendor_data_type
        is_array_column = vendor_data_type.endswith('[]')
        element_delimiter = None
        if is_array_column:
            if not resolved.is_array or resolved.element_delimiter is None:
                raise rq_contract.RemoteQueryFailure(
                    'schema_unavailable',
                    'A rendered array column type did not resolve to a catalog array element delimiter.',
                )
            element_delimiter = valid_array_element_delimiter_code(resolved.element_delimiter)
        descriptor_columns.append(
            rq_contract.RemoteQueryDescriptorColumn(
                column_name=column.name,
                vendor_data_type=vendor_data_type,
                logical_type=logical_type_for_column(column, vendor_data_type),
                array_element_delimiter=element_delimiter,
            )
        )
    return rq_contract.RemoteQueryUploadDescriptor(
        format_version='postgres-copy-csv-v1',
        include_schema=request.include_schema,
        agent_hostname=agent_hostname,
        columns=descriptor_columns,
    )


# ---------------------------------------------------------------------------
# Native COPY CSV source wire (postgres-copy-csv-v1)
# ---------------------------------------------------------------------------

# The frozen native wire: the customer query is evaluated exactly once, by a single
# `COPY ... TO STDOUT`. `FORCE_QUOTE *` makes every non-null field quoted — including
# empty strings, numerics, booleans, and a literal backslash-N text — and `NULL '\\N'`
# makes NULL the sole unquoted field, so NULL, empty string, and a literal `\\N` stay
# distinguishable in the raw bytes and quote provenance survives to intake. Standard
# PostgreSQL CSV escaping doubles quotes inside quoted fields, and commas and CR/LF ride
# raw inside them; records end with one LF, so a record's terminator is the first LF that
# closes every quoted field (an even number of quotes since the record's start).
POSTGRES_COPY_SQL_OPTIONS = "FORMAT CSV, NULL '\\N', FORCE_QUOTE *"

# Session output settings pinned transaction-locally so the native COPY text is a pure
# function of the values, never of the pooled session's ambient configuration:
# timestamptz renders in UTC, dates and timestamps in ISO style, intervals in the
# documented postgres spelling, bytea in hex, and float4/float8 in the server's shortest
# round-trip text. All are USERSET GUCs, so `SET LOCAL` works for every non-superuser,
# and `SET LOCAL` scopes each change to this read-only transaction: the closing ROLLBACK
# restores the pooled connection's session state untouched.
POSTGRES_COPY_SESSION_SETTINGS = (
    "SET LOCAL TimeZone = 'UTC'",
    "SET LOCAL DateStyle = 'ISO, MDY'",
    "SET LOCAL IntervalStyle = 'postgres'",
    "SET LOCAL bytea_output = 'hex'",
    'SET LOCAL extra_float_digits = 1',
)


def native_copy_sql(query: str) -> str:
    """The one COPY statement that evaluates the validated query and emits its native CSV."""
    return 'COPY ({}) TO STDOUT WITH ({})'.format(query, POSTGRES_COPY_SQL_OPTIONS)


# ---------------------------------------------------------------------------
# Producer: one validated query execution through the native COPY CSV path
# ---------------------------------------------------------------------------


def valid_array_element_delimiter_code(code: int) -> str:
    """Validate pg_type.typdelim: one printable, non-structural ASCII character."""
    if code < 0x21 or code > 0x7E:
        raise rq_contract.RemoteQueryFailure(
            'schema_unavailable', 'A column type carries an array element delimiter that is not printable.'
        )
    value = chr(code)
    if value in '" \\{}':
        raise rq_contract.RemoteQueryFailure(
            'schema_unavailable', 'A column type carries an array-literal structural element delimiter.'
        )
    return value


class CopyPageWriter:
    """Frame COPY CSV blocks without decoding values or copying individual records.

    With FORCE_QUOTE *, an LF terminates a record only at even quote parity.
    Preserve parity across arbitrary libpq block boundaries, including doubled quotes.
    """

    def __init__(
        self,
        delivery: rq_contract.RemoteQueryResultDelivery,
        creds: rq_upload.UploadCredentials,
        client: rq_upload.UploadClient,
        descriptor: rq_contract.RemoteQueryUploadDescriptor,
        guard: Callable[[], None],
        stats: rq_contract.RemoteQueryRunStats,
        timings: rq_timing.RemoteQueryProducerTimings,
    ):
        self._uploader = rq_pages.PageUploader(delivery, creds, client, descriptor, guard, stats, timings)
        self._guard = guard
        self._max_row_bytes = delivery.limits.max_row_bytes
        self._target = delivery.limits.max_file_bytes * 4 // 5
        self._buf = bytearray()
        self._record_ends = array('q')
        self._scan_pos = self._record_start = self._quote_parity = 0

    def feed_native_copy_block(self, block: bytes | bytearray | memoryview) -> None:
        buf = self._buf
        buf += block
        pos, start, parity = self._scan_pos, self._record_start, self._quote_parity
        while True:
            end = buf.find(b'\n', pos)
            if end < 0:
                break
            parity ^= buf.count(b'"', pos, end) & 1
            pos = end + 1
            if parity:
                continue
            if pos - start > self._max_row_bytes:
                raise rq_contract.RemoteQueryFailure('row_too_large', 'A single native record exceeds maxRowBytes.')
            self._guard()
            self._record_ends.append(pos)
            start = pos
            if pos >= self._target:
                consumed = self._close_page()
                pos -= consumed
                start -= consumed
        parity ^= buf.count(b'"', pos) & 1
        self._scan_pos, self._record_start, self._quote_parity = len(buf), start, parity
        if len(buf) - start > self._max_row_bytes:
            raise rq_contract.RemoteQueryFailure('row_too_large', 'A single native record exceeds maxRowBytes.')

    def finish_native_copy_stream(self) -> None:
        if len(self._buf) != self._record_start:
            raise rq_contract.RemoteQueryFailure(
                'query_failed', 'The COPY stream ended before the open native record was complete.'
            )

    def _close_page(self) -> int:
        count, consumed = self._uploader.upload(self._buf, self._record_ends)
        del self._buf[:consumed]
        self._record_ends = array('q', (end - consumed for end in self._record_ends[count:]))
        return consumed

    def finish(self) -> dict[str, Any]:
        self.finish_native_copy_stream()
        while self._record_ends:
            self._close_page()
        if self._uploader.descriptor.include_schema and not self._uploader.stats.pages_emitted:
            self._uploader.upload(self._buf, ())
        return self._uploader.finalize()

    def discard(self) -> None:
        self._buf.clear()
        del self._record_ends[:]
        self._scan_pos = self._record_start = self._quote_parity = 0


def produce_remote_query(
    request: rq_contract.RemoteQueryRequest,
    check: 'PostgreSql',
    creds: rq_upload.UploadCredentials,
    client: rq_upload.UploadClient,
    execution_dbname: str,
    started_at: float,
    stats: rq_contract.RemoteQueryRunStats,
    timings: rq_timing.RemoteQueryProducerTimings | None = None,
) -> dict[str, Any]:
    """Execute the validated query once, natively, and return the compact run receipt.

    The query's values are evaluated exactly once: a named server-side cursor DECLAREs it
    inside the existing read-only transaction with the effective statement timeout applied
    — the smaller of the instance-configured `remote_queries.timeout_ms` and the remaining
    run-wide wall, where the wall is the delivered `limits.timeout_ms` that no instance
    setting may lengthen — but is never fetched, so the DECLARE only plans and its
    description yields the column metadata; the single `COPY (query) TO STDOUT` then
    evaluates the query and streams its native CSV records. Session output settings are
    pinned in the same transaction, the vendor-type lookup and descriptor registration both
    precede the first record, and CopyPageWriter frames the native blocks,
    buffers one bounded source page, and uploads it without re-querying.

    Producer phases: connection acquisition through descriptor registration and the COPY
    dispatch is database setup, each `copy.read` call is a database fetch, record
    framing and page buffering are encode and page build (with any upload triggers nested
    inside it), and page uploads and finalize are accounted by the shared source-page
    writer. Everything else — timeout resolution, the pre-read guards, transaction
    teardown — lands in `otherMs`.
    """
    delivery = request.result_delivery
    limits = delivery.limits
    # The delivered timeout is the run-wide monotonic hard wall; the instance-configured
    # remote_queries.timeout_ms may shorten the statement timeout below it but never
    # replace or lengthen the wall.
    deadline = started_at + limits.timeout_ms / 1000
    statement_timeout_ms = _resolve_statement_timeout_ms(check, deadline)
    timings = timings or rq_timing.RemoteQueryProducerTimings(time.monotonic())

    def guard() -> None:
        rq_events.raise_if_timed_out(deadline)
        rq_events.raise_if_cancelled(check)

    cursor_name = 'remote_query_{}'.format(uuid.uuid4().hex)
    # The setup phase spans pool connection acquisition through descriptor registration and
    # the COPY dispatch, and ends before the first data read; the connection and cursor
    # contexts outlive the phase, so it is entered and exited explicitly. The inline exit
    # marks the boundary before the record loop; the spanning `finally` re-exits it
    # (idempotently) so a setup interrupted mid-flight still reports its partial wall.
    setup_phase = timings.enter_phase('database_setup')
    try:
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
                    for session_setting in POSTGRES_COPY_SESSION_SETTINGS:
                        control.execute(session_setting)
                    with conn.cursor(name=cursor_name) as described_cursor:
                        # The DECLARE plans the query and yields its result description —
                        # including for zero-row results — without fetching: no value is
                        # evaluated here, only by the COPY below.
                        described_cursor.execute(request.query)
                        columns = described_columns(described_cursor)
                        validate_columns(columns, limits.max_columns)
                        # The descriptor needs every vendor type name, schema or not: it is
                        # registered once, before any result record is read.
                        type_map = resolve_vendor_types(control, columns)
                        descriptor = build_upload_descriptor(request, columns, type_map, check.hostname)
                        # The executing check's Agent-reported hostname: the descriptor carries it
                        # so intake stamps the envelope with the agent node identity Fleet reports,
                        # never socket.gethostname().
                        writer = CopyPageWriter(delivery, creds, client, descriptor, guard, stats, timings)
                        guard()
                        with conn.cursor() as stream_cursor:
                            with stream_cursor.copy(native_copy_sql(request.query)) as copy:
                                # Setup ends here: the first copy.read below is its own phase.
                                timings.exit_phase(setup_phase)
                                try:
                                    with timings.phase('encode_and_page_build'):
                                        while True:
                                            # One fetch phase per read, entered and exited
                                            # explicitly like the setup phase above: the
                                            # per-record loop is the hot path, and a phase
                                            # context manager per read costs more than the
                                            # read itself.
                                            fetch_phase = timings.enter_phase('database_fetch')
                                            try:
                                                block = copy.read()
                                            finally:
                                                timings.exit_phase(fetch_phase)
                                            if not block:
                                                break
                                            guard()
                                            writer.feed_native_copy_block(block)
                                        # Fail closed unless the COPY stream ended exactly at a
                                        # record boundary; the final page close and the run
                                        # finalize below are their own phases.
                                        writer.finish_native_copy_stream()
                                    return writer.finish()
                                finally:
                                    # Release the page even if record framing or the copy fails.
                                    writer.discard()
                finally:
                    if in_transaction:
                        try:
                            control.execute('ROLLBACK')
                        except Exception:
                            # Fixed text only: the driver's exception can quote connection strings
                            # or identifiers embedded in its message.
                            LOGGER.debug('Unable to roll back remote query read-only transaction')
    finally:
        timings.exit_phase(setup_phase)


def _resolve_statement_timeout_ms(check: 'PostgreSql', deadline: float) -> int:
    """Resolve the statement timeout that protects the customer database for this run.

    `deadline` is the run-wide hard wall derived from the delivered `limits.timeout_ms`:
    it covers target resolution, query execution, page construction, upload, and retries,
    and instance configuration can never lengthen it. The instance config
    `remote_queries.timeout_ms` stays a customer-database protection with per-instance
    granularity (a warehouse instance can allow minutes while an OLTP instance allows
    seconds), but it may only shorten the run: the effective statement timeout is the smaller
    of the positive instance value and the remaining wall, and the wall's remainder applies
    when the instance does not configure one. The value is resolved locally per run; the
    delivery limits object is never mutated.
    """
    config = getattr(check, '_config', None)
    instance_timeout_ms = getattr(getattr(config, 'remote_queries', None), 'timeout_ms', None)
    remaining_ms = rq_events.remaining_wall_ms(deadline)
    if isinstance(instance_timeout_ms, int) and instance_timeout_ms > 0:
        return min(instance_timeout_ms, remaining_ms)
    return remaining_ms


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def _match_check_for_target(target: rq_contract.RemoteQueryTarget, check: 'PostgreSql') -> 'PostgreSql | None':
    """The matching authority shared by resolve and execute, on the supplied check alone.

    A database_instance selector matches by rendered identifier. A tuple selector matches
    only when the check's normalized configured endpoint equals the request and its
    effective monitoring scope includes the requested database. Returns the matched check
    or None; raises RemoteQueryFailure when the scope cannot be established — fail-closed
    and visible, never a silent no-match. Selecting zero, one, or many matching checks
    across the Agent's loaded checks is the Agent's own responsibility, so both operations
    report identical verdicts for the same target and check state.
    """
    if target.database_instance is not None:
        return check if getattr(check, 'database_identifier', None) == target.database_instance else None
    return check if _target_matches_scope(check, target) else None


def _resolved_dbname(target: rq_contract.RemoteQueryTarget, check: 'PostgreSql') -> str | None:
    """The database a matched check admits for the target.

    A tuple target's dbname is part of match identity and is the admitted database. A
    database_instance selector identifies one loaded check and admits its materialized
    configured database, never a request-named other one; None means the matched check
    cannot name a database at all.
    """
    if target.database_instance is not None:
        return _dbname_from_check(check)
    return target.dbname


def _target_matches_scope(check: 'PostgreSql', target: rq_contract.RemoteQueryTarget) -> bool:
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
        return rq_contract.normalize_host(host), port
    except ValueError:
        return None


def _dbname_from_check(check: 'PostgreSql') -> str | None:
    config = getattr(check, '_config', None)
    return getattr(config, 'dbname', None)


def database_in_monitoring_scope(check: 'PostgreSql', dbname: str) -> bool:
    """Answer whether one database lies inside a loaded check's effective monitoring scope.

    Single integration-owned source of truth for Remote Query database targeting, consumed by
    target matching and execution alike. The scope is the check's materialized `config.dbname`
    — an explicit `dbname`, else the `postgres` default, else
    `database_autodiscovery.global_view_db`, exactly as the integration's own `build_config`
    materialized it — plus, when database autodiscovery is enabled, the current database set
    admitted by the check's own autodiscovery implementation with its existing include/exclude
    filters, refresh cycle, and `max_databases` bound. Defaulting and filtering stay
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
    except Exception:
        # The caught exception neither reaches the message nor rides the wrapper's
        # exception chain: discovery failures can quote connection strings, identifiers, or
        # other server detail, so a traceback log of the wrapper must not recover them.
        # Classification and retryability are what the event carries, not the underlying
        # text.
        raise rq_contract.RemoteQueryFailure(
            'target_unavailable',
            "Unable to determine the matched check's autodiscovered database scope.",
            retryable=True,
        ) from None


# ---------------------------------------------------------------------------
# Agent entry points
# ---------------------------------------------------------------------------


def execute_agent_rpc_stream_copy(
    request_json: str | bytes | bytearray, check: 'PostgreSql', emit: rq_contract.RemoteQueryEmit
) -> None:
    """Execute a remote query request and emit its events, dispatching by operation.

    The entry point name is kept for the Agent's rtloader bridge, which resolves this
    function by name. `produce_json_pages` drives the page producer and emits `metadata`
    (STARTED), then one `final` (SUCCEEDED with the compact receipt) or `error` (FAILED)
    event; bulk page bytes never cross the callback. `resolve_target` drives the
    side-effect-free resolver and emits one `final` (MATCHED verdict) or `error` event.
    Diagnostics collection starts before the request JSON is parsed, so even a malformed
    request reports its measured wall.
    """
    request, timings, failure = rq_events.parse_agent_rpc_request(request_json)
    if failure is not None:
        rq_events.emit_event(emit, failure)
        return

    if request.get('operation') == 'resolve_target':
        rq_events.emit_agent_rpc_events(emit, iter_agent_resolve_events(request, check))
        return

    rq_events.emit_agent_rpc_events(emit, iter_agent_rpc_stream_events(request, check, timings=timings))


def iter_agent_resolve_events(request: Any, check: 'PostgreSql') -> Iterator[rq_contract.RemoteQueryEvent]:
    """Yield the per-check resolve verdict: one MATCHED `final` event or one `error` event.

    Resolve evaluates the target against the supplied check's effective monitoring scope
    with the same matching authority as execute, then reports the sanitized match identity
    the Agent aggregates across its loaded checks and binds into its match fingerprint.
    It is side-effect free: no customer SQL, no result delivery, no upload, and no probe of
    the requested database. An invalid request or an undeterminable eligible set is an
    error other than target_not_found, so the Agent fails its aggregate resolution instead
    of skipping the check.
    """
    started_at = time.monotonic()
    try:
        parsed_request = rq_contract.RemoteQueryResolveRequest.model_validate(request)
    except ValidationError as e:
        yield rq_events.failed_event(
            'invalid_request', rq_contract.validation_message(e), elapsed_ms=rq_events.elapsed_ms(started_at)
        )
        return

    target = parsed_request.target
    try:
        if _match_check_for_target(target, check) is None:
            yield rq_events.failed_event(
                'target_not_found',
                'No loaded Postgres integration instance matched target selector.',
                elapsed_ms=rq_events.elapsed_ms(started_at),
            )
            return
    except rq_contract.RemoteQueryFailure as e:
        yield rq_events.failed_event(
            e.code, e.message, retryable=e.retryable, elapsed_ms=rq_events.elapsed_ms(started_at)
        )
        return

    resolved_dbname = _resolved_dbname(target, check)
    if resolved_dbname is None:
        yield rq_events.failed_event(
            'target_unavailable',
            'Matched Postgres check does not expose a configured database name.',
            elapsed_ms=rq_events.elapsed_ms(started_at),
        )
        return

    endpoint = _endpoint_from_check(check)
    yield rq_events.matched_resolve_event(
        host=endpoint[0] if endpoint is not None else None,
        port=endpoint[1] if endpoint is not None else None,
        configured_dbname=_dbname_from_check(check),
        resolved_dbname=resolved_dbname,
        database_instance=getattr(check, 'database_identifier', None),
    )


def iter_agent_rpc_stream_events(
    request: Any,
    check: 'PostgreSql',
    http_client: rq_upload.UploadClient | None = None,
    timings: rq_timing.RemoteQueryProducerTimings | None = None,
) -> Iterator[rq_contract.RemoteQueryEvent]:
    """Execute on the supplied check; emit only status and the intake receipt."""
    timings = timings or rq_timing.RemoteQueryProducerTimings(time.monotonic())
    stats = None
    client = None
    creds = None
    try:
        parsed = rq_events.validate_request(request, REMOTE_QUERY_QUERY_ALLOWLIST)
        if _match_check_for_target(parsed.target, check) is None:
            raise rq_contract.RemoteQueryFailure(
                'target_not_found', 'No loaded Postgres integration instance matched target selector.'
            )
        execution_dbname = _resolved_dbname(parsed.target, check)
        if execution_dbname is None:
            raise rq_contract.RemoteQueryFailure(
                'target_unavailable', 'Matched Postgres check does not expose a configured database name.'
            )
        creds = rq_upload.resolve_upload_credentials(parsed.result_delivery, timings.started_at, parsed.trace_context)
        if not creds.api_key or not creds.app_key:
            raise rq_contract.RemoteQueryFailure(
                'credentials_unavailable',
                'Remote query upload requires api_key and app_key to be configured on the Agent.',
            )
        pool = getattr(check, 'db_pool', None)
        if pool is None:
            raise rq_contract.RemoteQueryFailure(
                'credentials_unavailable', 'Matched Postgres check does not expose a connection pool.'
            )
        if pool.is_closed():
            raise rq_contract.RemoteQueryFailure(
                'target_unavailable', 'Matched Postgres check connection pool is closed.'
            )
        client = http_client if http_client is not None else rq_upload.RequestsUploadClient(timings=timings)
        stats = rq_contract.RemoteQueryRunStats()
        yield rq_contract.RemoteQueryEvent('metadata', rq_events.started_metadata(parsed))
        try:
            receipt = produce_remote_query(
                parsed, check, creds, client, execution_dbname, timings.started_at, stats, timings
            )
        except psycopg_errors.QueryCanceled:
            raise rq_contract.RemoteQueryFailure(
                'timeout', 'Remote query was canceled by the server (statement timeout or cancellation).', True
            ) from None
        except RuntimeError:
            raise rq_contract.RemoteQueryFailure(
                'target_unavailable', 'Matched Postgres check connection pool is unavailable.'
            ) from None
    except BaseException as error:
        if client is not None:
            rq_upload.safe_abort(client, creds)
        if not isinstance(error, Exception):
            raise
        yield rq_events.query_failure_event(error, timings, stats)
        return
    yield rq_contract.RemoteQueryEvent(
        'final', rq_events.succeeded_metadata(receipt, stats, timings.started_at, timings)
    )
