# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Session-backed remote queries on a loaded Postgres check."""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from array import array
from collections.abc import Iterator
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import UUID

import psycopg
from psycopg import capabilities, errors, generators, pq, waiting
from psycopg.abc import PQGen

from .remote_query_intake import ABORT_TIMEOUT, Intake, UploadError

if TYPE_CHECKING:
    from .postgres import PostgreSql

CANCEL_TIMEOUT = 5

LIMIT_KEYS = {"maxFileBytes", "maxResultBytes", "maxRowBytes", "maxColumns", "maxSchemaBytes", "maxPages", "timeoutMs"}
LOGICAL_TYPES = {
    "bool": "boolean",
    **dict.fromkeys(("int2", "int4", "int8", "oid"), "integer"),
    "numeric": "decimal",
    **dict.fromkeys(("float4", "float8"), "float"),
    **dict.fromkeys(("text", "varchar", "bpchar", "char", "name", "uuid"), "string"),
    **dict.fromkeys(("date", "time", "timetz", "timestamp", "timestamptz", "interval"), "temporal"),
    **dict.fromkeys(("json", "jsonb"), "json"),
    "bytea": "binary",
}
TYPE_QUERY = """
WITH RECURSIVE base AS (
    SELECT oid, typname, typtype, typcategory, typbasetype, typnamespace
    FROM pg_catalog.pg_type WHERE oid = %s
    UNION ALL
    SELECT t.oid, t.typname, t.typtype, t.typcategory, t.typbasetype, t.typnamespace
    FROM pg_catalog.pg_type t JOIN base b ON t.oid = b.typbasetype
)
SELECT pg_catalog.format_type(%s, %s), typname, typtype, typcategory, oid,
       typnamespace = 'pg_catalog'::pg_catalog.regnamespace
FROM base WHERE typbasetype = 0
"""


class RemoteQueryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def encode(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def failed(code: str, message: str) -> str:
    return encode({"status": "FAILED", "error": {"code": code, "message": message}}).decode()


def _object(value: object, keys: set[str], optional: set[str] | frozenset[str] = frozenset()) -> bool:
    return isinstance(value, dict) and keys <= value.keys() and value.keys() <= keys | optional


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def _positive(value: object) -> bool:
    return type(value) is int and value > 0


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def parse_request(raw: str) -> dict:
    """Validate completely before any database or intake I/O."""
    try:
        request = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(request, dict):
            raise ValueError
        operation = request.get("operation")
        if operation == "resolve":
            valid = _object(request, {"operation", "target"})
        elif operation == "execute":
            valid = _object(
                request, {"operation", "target", "query", "includeSchema", "resultDelivery"}, {"traceContext"}
            )
        else:
            valid = False
        if not valid:
            raise ValueError
        target = request["target"]
        if _object(target, {"database_instance"}):
            name = target["database_instance"]
            if not _text(name) or name != name.strip():
                raise ValueError
        elif _object(target, {"host", "port", "dbname"}):
            if (
                not _text(target["host"])
                or not _text(target["dbname"])
                or not _positive(target["port"])
                or target["port"] > 65535
            ):
                raise ValueError
        else:
            raise ValueError
        encode(request)  # Reject strings that cannot be represented as UTF-8.
        if operation == "resolve":
            return request
        if not _text(request["query"]) or type(request["includeSchema"]) is not bool:
            raise ValueError
        delivery = request["resultDelivery"]
        if not _object(delivery, {"crawlId", "taskId", "uploadId", "baseUrl", "limits"}):
            raise ValueError
        for key in ("crawlId", "taskId"):
            if not isinstance(delivery[key], str):
                raise ValueError
            UUID(delivery[key])
        if not isinstance(delivery["uploadId"], str) or not re.fullmatch(r"[a-zA-Z0-9._-]+", delivery["uploadId"]):
            raise ValueError
        if not _text(delivery["baseUrl"]):
            raise ValueError
        # Site authorization belongs to the Agent. Reject URL syntax that could change the appended path or headers.
        address = delivery["baseUrl"]
        url = urlsplit(address)
        if (
            url.scheme not in ("https", "http")
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or re.search(r"[\s\\\x00-\x1f\x7f]", address)
        ):
            raise ValueError
        _ = url.port  # Validate the port's syntax too.
        limits = delivery["limits"]
        if not _object(limits, LIMIT_KEYS) or not all(_positive(n) for n in limits.values()):
            raise ValueError
        if "traceContext" in request:
            trace = request["traceContext"]
            if not _object(trace, {"traceId", "parentId", "samplingPriority"}):
                raise ValueError
            if type(trace["samplingPriority"]) is not int or trace["samplingPriority"] not in (1, 2):
                raise ValueError
            for key in ("traceId", "parentId"):
                if (
                    not isinstance(trace[key], str)
                    or not re.fullmatch(r"[0-9]+", trace[key])
                    or not 0 < int(trace[key]) < 2**64
                ):
                    raise ValueError
        return request
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        raise RemoteQueryError("invalid_request", "Invalid remote query request.") from None


def match(check: PostgreSql, target: dict) -> str | None:
    """Read the loaded configuration and last discovery snapshot only."""
    config = check._config
    databases = {config.dbname}
    if config.database_autodiscovery.enabled:
        try:
            discovered = check.autodiscovery.remote_query_databases if check.autodiscovery is not None else None
            if discovered is None:
                raise ValueError
            databases.update(discovered)
        except Exception:
            raise RemoteQueryError("target_unavailable", "The monitoring scope is unavailable.") from None
    if "database_instance" in target:
        if check.database_identifier == target["database_instance"]:
            return config.dbname
    else:
        host = config.host
        port = config.port
        if isinstance(host, str) and host.strip() and port is not None:

            def normalize(value: str) -> str:
                return value.strip().lower().removesuffix(".")

            if (
                normalize(host) == normalize(target["host"])
                and port == target["port"]
                and target["dbname"] in databases
            ):
                return target["dbname"]
    raise RemoteQueryError("target_not_found", "No Postgres instance matches the target.")


class RecordFramer:
    """Find CSV record boundaries without decoding fields, including across COPY blocks."""

    def __init__(self, max_row_bytes: int) -> None:
        self.limit = max_row_bytes
        self.record = bytearray()
        self.quoted = False

    def feed(self, block: bytes | memoryview) -> Iterator[bytearray | memoryview]:
        # Quote parity is sufficient for database-produced CSV: escaped quotes occur in pairs.
        start = 0
        for token in re.finditer(rb'["\n]', block):
            index = token.start()
            if len(self.record) + index - start + 1 > self.limit:
                raise RemoteQueryError("row_too_large", "A result record exceeds its size limit.")
            if token.group() == b'"':
                self.quoted = not self.quoted
            elif not self.quoted:
                if self.record:
                    self.record.extend(block[start : index + 1])
                    record, self.record = self.record, bytearray()
                else:
                    record = memoryview(block)[start : index + 1]
                start = index + 1
                yield record
        if len(self.record) + len(block) - start > self.limit:
            raise RemoteQueryError("row_too_large", "A result record exceeds its size limit.")
        self.record.extend(block[start:])

    def finish(self) -> None:
        if self.record or self.quoted:
            raise RemoteQueryError("query_failed", "The database returned an incomplete COPY record.")


class Page:
    def __init__(self) -> None:
        self.data = bytearray()
        self.ends = array("Q", [0])

    def add(self, record: bytearray | memoryview) -> None:
        self.data.extend(record)
        self.ends.append(len(self.data))

    @property
    def rows(self) -> int:
        return len(self.ends) - 1


class ResultSizer:
    """Estimate intake's JSON file without decoding or converting PostgreSQL values."""

    def __init__(self, delivery: dict, columns: list[dict], include_schema: bool, hostname: str) -> None:
        schema = [{"column_name": c["column_name"], "vendor_data_type": c["vendor_data_type"]} for c in columns]
        header = {
            "contract_version": "1.0.0",
            "crawl_id": delivery["crawlId"],
            "task_id": delivery["taskId"],
            "record_offset": 2**63 - 1,
            "data": [],
            "org_id": 2**63 - 1,
            "agent_hostname": hostname,
            "sensitive_data_scanned": False,
        }
        if include_schema:
            if len(encode(schema)) > delivery["limits"]["maxSchemaBytes"]:
                raise RemoteQueryError("schema_too_large", "The result schema exceeds its size limit.")
            header["schema"] = schema
        self.header_bytes = len(encode(header))
        if include_schema and self.header_bytes >= delivery["limits"]["maxFileBytes"]:
            raise RemoteQueryError("schema_too_large", "The schema leaves no room in a result file.")
        self.row_overhead = 3 + sum(len(encode(c["column_name"])) + 4 for c in columns)

    def page_bytes(self, uploaded_bytes: int, rows: int) -> int:
        return self.header_bytes + uploaded_bytes + rows * self.row_overhead


class RemoteConnection(psycopg.AsyncConnection):
    async def wait[T](self, gen: PQGen[T], interval: float = 0.1) -> T:
        # The ordinary driver cancellation path drains the query without a deadline.
        # This connection is disposable: Run explicitly bounds cancellation, then closes it.
        return await waiting.wait_async(gen, self.pgconn.socket, interval=interval)


def _send_legacy_cancel(cancel: pq.abc.PGcancel, loop: asyncio.AbstractEventLoop, done: asyncio.Future[None]) -> None:
    def finish() -> None:
        if not done.done():
            done.set_result(None)

    try:
        cancel.cancel()
    except Exception:
        pass
    finally:
        cancel.free()
        try:
            loop.call_soon_threadsafe(finish)
        except RuntimeError:
            pass


class Run:
    def __init__(self, request: dict, received: float) -> None:
        self.request = request
        self.delivery = request["resultDelivery"]
        self.limits = self.delivery["limits"]
        self.deadline = received + self.limits["timeoutMs"] / 1000
        self.cancelled = threading.Event()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.task: asyncio.Task | None = None
        self.connection: RemoteConnection | None = None
        self.intake: Intake | None = None
        self.finalized = False
        self.page_count = 0
        self.record_offset = 0
        self.result_bytes = 0
        self.sizer: ResultSizer | None = None

    def cancel(self) -> None:
        if self.cancelled.is_set():
            return
        self.cancelled.set()
        loop, task = self.loop, self.task
        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass  # The run has already ended.

    def log(self, check: PostgreSql, event: str, code: str) -> None:
        check.log.debug(
            "Remote query %s code=%s crawl_id=%s task_id=%s upload_id=%s",
            event,
            code,
            self.delivery["crawlId"],
            self.delivery["taskId"],
            self.delivery["uploadId"],
        )

    def _guard(self) -> None:
        if self.cancelled.is_set():
            raise asyncio.CancelledError
        if time.monotonic() >= self.deadline:
            raise TimeoutError

    async def execute(self, check: PostgreSql, api_key: str, hostname: str, proxy: dict) -> str:
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        answer = failed("internal_error", "Remote query failed unexpectedly.")
        try:
            self._guard()
            async with asyncio.timeout(max(0, self.deadline - time.monotonic())):
                self.intake = Intake(self.delivery, api_key, hostname, proxy, self.request.get("traceContext"))
                if not api_key:
                    raise RemoteQueryError("credentials_unavailable", "The Agent API key is unavailable.")
                database = match(check, self.request["target"])
                kwargs = check.build_connection_args().as_kwargs(dbname=database)
                provider = check.db_pool.token_provider
                if provider is not None:
                    kwargs["password"] = provider.get_token()
                self._guard()
                self.connection = await RemoteConnection.connect(**kwargs, autocommit=True, prepare_threshold=None)
                await self._query(check)
                self._guard()
                await self.intake.request(
                    "POST", "/finalize", encode({"expected_page_count": self.page_count}), deadline=self.deadline
                )
                self.finalized = True
                answer = encode({"status": "SUCCEEDED"}).decode()
                self.log(check, "finished", "succeeded")
        except asyncio.CancelledError:
            answer = failed("cancelled", "The remote query was cancelled.")
            self.log(check, "failed", "cancelled")
        except TimeoutError:
            answer = failed("timeout", "The remote query exceeded its time limit.")
            self.log(check, "failed", "timeout")
        except RemoteQueryError as error:
            answer = failed(error.code, error.message)
            self.log(check, "failed", error.code)
        except UploadError as error:
            answer = failed("upload_failed", f"Intake request failed: {error.code}.")
            self.log(check, "failed", "upload_failed")
        except psycopg.Error as error:
            code, message = self._database_error(error)
            answer = failed(code, message)
            self.log(check, "failed", code)
        except Exception:
            self.log(check, "failed", "internal_error")
        finally:
            # Cancellation of the work must not cancel its independent, bounded cleanup.
            self.task = None
            await self._close_database(check)
            if not self.finalized:
                # Abort has its own budget and is also required after the run deadline.
                try:
                    if self.intake is None:
                        self.intake = Intake(self.delivery, api_key, hostname, proxy, self.request.get("traceContext"))
                    async with asyncio.timeout(ABORT_TIMEOUT):
                        await self.intake.request("POST", "/abort")
                except (Exception, asyncio.CancelledError):
                    self.log(check, "abort_failed", "upload_failed")
        if self.cancelled.is_set() and not self.finalized:
            return failed("cancelled", "The remote query was cancelled.")
        return answer

    def _database_error(self, error: psycopg.Error) -> tuple[str, str]:
        if self.cancelled.is_set():
            return "cancelled", "The remote query was cancelled."
        if error.sqlstate == "57014":
            return "timeout", "The database statement exceeded its time limit."
        state = error.sqlstate or "08006"
        try:
            condition = re.sub(r"(?<!^)(?=[A-Z])", "_", errors.lookup(state).__name__).lower()
        except KeyError:
            condition = "database_error"
        code = "connection_failed" if self.connection is None or state.startswith("08") else "query_failed"
        return code, f"Database error: {state} {condition}."

    async def _cancel_database(self, check: PostgreSql) -> None:
        if capabilities.has_cancel_safe():
            await self.connection.cancel_safe(timeout=CANCEL_TIMEOUT)
            return
        # PQcancel before libpq 17 has no timeout. Capture its independent cancel
        # handle before closing the run connection; never put it on asyncio's executor,
        # whose shutdown would make the run wait indefinitely.
        cancel = self.connection.pgconn.get_cancel()
        loop = asyncio.get_running_loop()
        done = loop.create_future()

        threading.Thread(
            target=_send_legacy_cancel,
            args=(cancel, loop, done),
            name="postgres-remote-query-cancel",
            daemon=True,
        ).start()
        try:
            await asyncio.wait_for(done, CANCEL_TIMEOUT)
        except TimeoutError:
            self.log(check, "cancel_request_abandoned", "cancelled")

    async def _close_database(self, check: PostgreSql) -> None:
        conn = self.connection
        if conn is None:
            return
        try:
            if conn.pgconn.transaction_status == pq.TransactionStatus.ACTIVE:
                async with asyncio.timeout(CANCEL_TIMEOUT + 0.01):
                    await self._cancel_database(check)
            elif conn.pgconn.transaction_status in (pq.TransactionStatus.INTRANS, pq.TransactionStatus.INERROR):
                async with asyncio.timeout(1):
                    await conn.rollback()
        except (Exception, asyncio.CancelledError):
            pass
        finally:
            # Disconnect also rolls back an active/failed transaction; never drain COPY on failure.
            await conn.close()

    async def _protocol_result(self) -> pq.abc.PGresult:
        results = await self.connection.wait(generators.execute(self.connection.pgconn))
        for result in results:
            if result.status == pq.ExecStatus.FATAL_ERROR:
                raise errors.error_from_result(result, encoding="utf-8")
        return results[-1]

    async def _statement_timeout(self, check: PostgreSql) -> None:
        self._guard()
        milliseconds = max(1, int((self.deadline - time.monotonic()) * 1000))
        configured = check._config.remote_queries
        if configured is not None and configured.timeout_ms is not None:
            milliseconds = min(milliseconds, configured.timeout_ms)
        await self.connection.execute(f"SET LOCAL statement_timeout = {milliseconds}")

    async def _query(self, check: PostgreSql) -> None:
        conn = self.connection
        await conn.execute("BEGIN READ ONLY")
        for name, value in (
            ("client_encoding", "UTF8"),
            ("TimeZone", "UTC"),
            ("DateStyle", "ISO, MDY"),
            ("IntervalStyle", "postgres"),
            ("bytea_output", "hex"),
            ("extra_float_digits", "1"),
        ):
            await conn.execute(f"SET LOCAL {name} = '{value}'")
        await self._statement_timeout(check)
        query = self.request["query"].encode("utf-8")
        # Extended Parse rejects multiple statements. Describe never executes the query.
        conn.pgconn.send_prepare(b"", query)
        await self._protocol_result()
        conn.pgconn.send_describe_prepared(b"")
        description = await self._protocol_result()
        if not 0 < description.nfields <= self.limits["maxColumns"]:
            raise RemoteQueryError("invalid_columns", "The result has no columns or exceeds the column limit.")
        columns = []
        names = set()
        for index in range(description.nfields):
            name = description.fname(index).decode("utf-8")
            if name in names:
                raise RemoteQueryError("invalid_columns", f"Duplicate result column: {json.dumps(name)}.")
            names.add(name)
            oid, modifier = description.ftype(index), description.fmod(index)
            cursor = await conn.execute(TYPE_QUERY, (oid, oid, modifier))
            vendor, base, kind, category, base_oid, builtin = await cursor.fetchone()
            if kind == "c" or category == "A" or base_oid == 2249:
                raise RemoteQueryError(
                    "unsupported_column",
                    f"Unsupported column {json.dumps(name)}; expand its fields into separate columns "
                    "or convert it to JSON or JSONB.",
                )
            columns.append(
                {
                    "column_name": name,
                    "vendor_data_type": vendor,
                    "logical_type": LOGICAL_TYPES.get(base, "vendor") if builtin else "vendor",
                }
            )
        self.sizer = ResultSizer(self.delivery, columns, self.request["includeSchema"], self.intake.hostname)
        descriptor = {
            "format_version": "postgres-copy-csv-v1",
            "include_schema": self.request["includeSchema"],
            "agent_hostname": self.intake.hostname,
            "columns": columns,
        }
        self._guard()
        await self.intake.request("POST", "/descriptor", encode(descriptor), deadline=self.deadline)
        await self._statement_timeout(check)
        conn.pgconn.send_query(b"COPY (\n" + query + b"\n) TO STDOUT WITH (FORMAT CSV, NULL E'\\\\N')")
        result = await self._protocol_result()
        if result.status != pq.ExecStatus.COPY_OUT:
            raise RemoteQueryError("query_failed", "The query did not return COPY output.")
        framer = RecordFramer(self.limits["maxRowBytes"])
        page = Page()
        while True:
            self._guard()
            block = await conn.wait(generators.copy_from(conn.pgconn))
            if not isinstance(block, memoryview):
                break
            for record in framer.feed(block):
                self._guard()
                size = self.sizer.page_bytes(len(page.data) + len(record), page.rows + 1)
                if page.rows and size > self.limits["maxFileBytes"]:
                    await self._upload(page, 0, page.rows)
                    page = Page()
                page.add(record)
        framer.finish()
        if page.rows or not self.page_count:
            await self._upload(page, 0, page.rows)

    async def _upload(self, page: Page, first: int, last: int) -> None:
        self._guard()
        rows = last - first
        body = memoryview(page.data)[page.ends[first] : page.ends[last]]
        estimate = self.sizer.page_bytes(len(body), rows)
        if self.page_count >= self.limits["maxPages"] or self.result_bytes + estimate > self.limits["maxResultBytes"]:
            raise RemoteQueryError("result_too_large", "The result exceeds its page or total size limit.")
        try:
            await self.intake.request(
                "PUT",
                f"/pages/{self.page_count}",
                body,
                {"X-DD-Source-Page-Rows": str(rows), "X-DD-Record-Offset": str(self.record_offset)},
                deadline=self.deadline,
            )
        except UploadError as error:
            if error.code != "result_file_too_large":
                raise
            if rows <= 1:
                raise RemoteQueryError(
                    "row_too_large", "A one-record page exceeds intake's result file limit."
                ) from None
            middle = first + rows // 2
            await self._upload(page, first, middle)
            await self._upload(page, middle, last)
            return
        self.page_count += 1
        self.record_offset += rows
        self.result_bytes += estimate
