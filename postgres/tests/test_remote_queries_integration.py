# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import json
import os
import socket
import socketserver
import ssl
import statistics
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import BinaryIO

import psycopg
import pytest
from psycopg.pq.abc import PGcancel

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.config_models.instance import DatabaseAutodiscovery, RemoteQueries

from .common import PASSWORD_ADMIN, USER_ADMIN
from .remote_query_helpers import StubIntake, StubProxy, call, request

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


@pytest.fixture
def intake() -> Iterator[StubIntake]:
    server = StubIntake()
    server.start()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def rq_check(
    integration_check: Callable[[dict], PostgreSql], pg_instance: dict, monkeypatch: pytest.MonkeyPatch
) -> PostgreSql:
    check = integration_check(pg_instance)
    monkeypatch.setattr(
        "datadog_checks.postgres.postgres.datadog_agent.get_config",
        lambda key: "remote-query-api-key" if key == "api_key" else {},
    )
    monkeypatch.setattr("datadog_checks.postgres.postgres.datadog_agent.get_hostname", lambda: "remote-query-agent")
    return check


@pytest.mark.parametrize("variant", ["modifiers", "logical_types", "domain"])
def test_desc01_02_04_and_finish01_02(
    rq_check: PostgreSql, intake: StubIntake, rq_schema: psycopg.Connection, variant: str
):
    # DESC-01/02/04, FINISH-01/02: describe types before COPY, then finalize the accepted page count.
    cases = {
        "modifiers": (
            "SELECT 1::numeric(10,2) AS number, 'a'::varchar(20) AS label",
            [("number", "numeric(10,2)", "decimal"), ("label", "character varying(20)", "string")],
            b"1.00,a\n",
        ),
        "logical_types": (
            "SELECT true AS b, 3::bigint AS i, 1.25::real AS f, 'a'::text AS s, "
            "DATE '2026-01-02' AS t, '{\"a\":1}'::json AS j, '\\x01'::bytea AS bytes, '127.0.0.1'::inet AS v",
            [
                ("b", "boolean", "boolean"),
                ("i", "bigint", "integer"),
                ("f", "real", "float"),
                ("s", "text", "string"),
                ("t", "date", "temporal"),
                ("j", "json", "json"),
                ("bytes", "bytea", "binary"),
                ("v", "inet", "vendor"),
            ],
            b't,3,1.25,a,2026-01-02,"{""a"":1}",\\x01,127.0.0.1\n',
        ),
        "domain": ("SELECT 1::rq_spec.amount AS amount", [("amount", "numeric(10,2)", "decimal")], b"1.00\n"),
    }
    query, expected_columns, expected_body = cases[variant]
    payload = request(rq_check, intake.address, query)
    assert call(rq_check, payload) == {"status": "SUCCEEDED"}
    assert [r["path"] for r in intake.records] == ["/descriptor", "/pages/0", "/finalize"]
    descriptor = json.loads(intake.records[0]["body"])
    assert descriptor == {
        "format_version": "postgres-copy-csv-v1",
        "include_schema": True,
        "agent_hostname": "remote-query-agent",
        "columns": [
            {"column_name": name, "vendor_data_type": vendor, "logical_type": logical}
            for name, vendor, logical in expected_columns
        ],
    }
    assert intake.pages[0]["body"] == expected_body
    assert all("x-datadog-trace-id" not in record["headers"] for record in intake.records)
    assert json.loads(intake.records[-1]["body"]) == {"expected_page_count": 1}


def test_query02_03_read_only_settings(rq_check: PostgreSql, intake: StubIntake, rq_schema: psycopg.Connection):
    # QUERY-02/03: transaction-local output settings and database read-only enforcement.
    query = """
        SELECT current_setting('transaction_read_only') AS ro, current_setting('client_encoding') AS enc,
               current_setting('TimeZone') AS tz, current_setting('DateStyle') AS ds,
               current_setting('IntervalStyle') AS its, current_setting('bytea_output') AS bo,
               current_setting('extra_float_digits') AS efd
    """
    assert call(rq_check, request(rq_check, intake.address, query))["status"] == "SUCCEEDED"
    assert intake.pages[0]["body"] == b'on,UTF8,UTC,"ISO, MDY",postgres,hex,1\n'
    denied = call(
        rq_check,
        request(
            rq_check,
            intake.address,
            "WITH changed AS (INSERT INTO rq_spec.writes VALUES(1) RETURNING i) SELECT i FROM changed",
        ),
    )
    assert denied["error"]["code"] == "query_failed"
    assert "25006 read_only_sql_transaction" in denied["error"]["message"]
    assert rq_schema.execute("SELECT count(*) FROM rq_spec.writes").fetchone()[0] == 0


@pytest.mark.parametrize(
    "query,code,condition",
    [
        ("SELECT * FROM missing_remote_query_table", "query_failed", "42P01 undefined_table"),
        ("SELECT 1 / 0", "query_failed", "22012 division_by_zero"),
        ("SELECT pg_sleep(2)", "timeout", "time limit"),
        ("SELECT 1", "connection_failed", "08006 connection_failure"),
    ],
)
def test_query04_06_database_conditions(
    rq_check: PostgreSql, intake: StubIntake, query: str, code: str, condition: str
):
    # QUERY-04/06: the instance timeout is a statement ceiling; errors never expose driver messages.
    rq_check._config = rq_check._config.model_copy(update={"remote_queries": RemoteQueries(timeout_ms=40)})
    if code == "connection_failed":
        with socket.socket() as unused:
            unused.bind(("127.0.0.1", 0))
            port = unused.getsockname()[1]
        rq_check._config = rq_check._config.model_copy(update={"host": "127.0.0.1", "port": port})
    answer = call(rq_check, request(rq_check, intake.address, query))
    assert answer["error"]["code"] == code
    assert condition in answer["error"]["message"]
    assert query not in answer["error"]["message"]
    assert intake.records[-1]["path"] == "/abort"


@pytest.mark.parametrize(
    "query",
    ["SELECT ARRAY[1,2] AS bad", "SELECT ROW(1,2) AS bad", "SELECT pg_database AS bad FROM pg_database LIMIT 1"],
)
def test_pg01_unsupported_columns(rq_check: PostgreSql, intake: StubIntake, query: str):
    answer = call(rq_check, request(rq_check, intake.address, query))
    assert answer["error"]["code"] == "unsupported_column"
    assert "bad" in answer["error"]["message"] and "JSON or JSONB" in answer["error"]["message"]
    assert [r["path"] for r in intake.records] == ["/abort"]


@pytest.mark.parametrize(
    "query,limits,code",
    [
        ("SELECT 1 AS a, 2 AS a", {}, "invalid_columns"),
        ("SELECT FROM pg_catalog.pg_database", {}, "invalid_columns"),
        ("SELECT 1 AS a, 2 AS b", {"maxColumns": 1}, "invalid_columns"),
        ("SELECT 1 AS a", {"maxSchemaBytes": 1}, "schema_too_large"),
        ("SELECT 1 AS a", {"maxFileBytes": 1}, "schema_too_large"),
    ],
)
def test_desc03_descriptor_limits(rq_check: PostgreSql, intake: StubIntake, query: str, limits: dict, code: str):
    answer = call(rq_check, request(rq_check, intake.address, query, **limits))
    assert answer["error"]["code"] == code
    assert [r["path"] for r in intake.records] == ["/abort"]


def test_req03_missing_key(rq_check: PostgreSql, intake: StubIntake, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("datadog_checks.postgres.postgres.datadog_agent.get_config", lambda key: None)
    answer = call(rq_check, request(rq_check, intake.address))
    assert answer["error"]["code"] == "credentials_unavailable"
    assert [r["path"] for r in intake.records] == ["/abort"]


def test_match04_unknown_discovery(rq_check: PostgreSql, intake: StubIntake):
    rq_check._config = rq_check._config.model_copy(
        update={"database_autodiscovery": DatabaseAutodiscovery(enabled=True)}
    )
    answer = call(rq_check, request(rq_check, intake.address))
    assert answer["error"]["code"] == "target_unavailable"
    assert [r["path"] for r in intake.records] == ["/abort"]


def test_match05_rematch(rq_check: PostgreSql, intake: StubIntake):
    payload = request(rq_check, intake.address)
    assert call(rq_check, {"operation": "resolve", "target": payload["target"]}) == {"status": "MATCHED"}
    payload["target"]["dbname"] = "out_of_scope"
    answer = call(rq_check, payload)
    assert answer["error"]["code"] == "target_not_found"
    assert [r["path"] for r in intake.records] == ["/abort"]


@pytest.mark.parametrize("schema", [True, False])
def test_size05_empty_result(rq_check: PostgreSql, intake: StubIntake, schema: bool):
    payload = request(rq_check, intake.address, "SELECT 1 AS value WHERE false")
    payload["includeSchema"] = schema
    assert call(rq_check, payload) == {"status": "SUCCEEDED"}
    assert len(intake.pages) == 1 and intake.pages[0]["body"] == b""
    assert intake.pages[0]["headers"]["X-DD-Source-Page-Rows"] == "0"
    assert json.loads(intake.records[-1]["body"]) == {"expected_page_count": 1}


@pytest.mark.parametrize("rows", [1, 5])
def test_size02_split_without_rerun(rq_check: PostgreSql, intake: StubIntake, rq_schema: psycopg.Connection, rows: int):
    intake.reply("/pages/0", (413, "result_file_too_large"))
    answer = call(
        rq_check,
        request(
            rq_check,
            intake.address,
            f"SELECT i, rq_spec.evaluations() AS evaluation FROM generate_series(1,{rows}) AS i",
        ),
    )
    if rows == 1:
        assert answer["error"]["code"] == "row_too_large"
        assert len(intake.pages) == 1 and intake.records[-1]["path"] == "/abort"
        return
    assert answer == {"status": "SUCCEEDED"}
    pages = intake.pages
    assert [(r["path"], r["body"]) for r in pages] == [
        ("/pages/0", b"1,1\n2,2\n3,3\n4,4\n5,5\n"),
        ("/pages/0", b"1,1\n2,2\n"),
        ("/pages/1", b"3,3\n4,4\n5,5\n"),
    ]
    assert [r["headers"]["X-DD-Record-Offset"] for r in pages] == ["0", "0", "2"]


@pytest.mark.parametrize("limits", [{"maxPages": 1, "maxFileBytes": 600}, {"maxResultBytes": 100}])
def test_size06_result_limits(rq_check: PostgreSql, intake: StubIntake, limits: dict):
    answer = call(
        rq_check,
        request(rq_check, intake.address, "SELECT repeat('x', 200) AS value FROM generate_series(1,10)", **limits),
    )
    assert answer["error"]["code"] == "result_too_large"
    assert intake.records[-1]["path"] == "/abort"


def test_upload01_02_sequential_metadata(rq_check: PostgreSql, intake: StubIntake):
    # UPLOAD-01/02: one accepted page at a time, fixed bytes and contiguous offsets.
    assert (
        call(
            rq_check,
            request(
                rq_check,
                intake.address,
                "SELECT i, repeat('x', 100) AS v FROM generate_series(1,8) AS i",
                maxFileBytes=700,
            ),
        )["status"]
        == "SUCCEEDED"
    )
    offset = 0
    for index, page in enumerate(intake.pages):
        headers = page["headers"]
        assert page["path"] == f"/pages/{index}"
        assert headers["X-DD-Record-Offset"] == str(offset)
        rows = int(headers["X-DD-Source-Page-Rows"])
        offset += rows
        assert rows == page["body"].count(b"\n")
        assert int(headers["Content-Length"]) == len(page["body"])
        assert "Content-Encoding" not in headers and "Transfer-Encoding" not in headers
    assert offset == 8 and len(intake.pages) > 1


@pytest.mark.parametrize(
    "path,replies,outcome,count",
    [
        (path, [(0, ""), (500, "internal"), (503, "unavailable")], "SUCCEEDED", 4)
        for path in ("/descriptor", "/pages/0", "/finalize")
    ]
    + [
        ("/pages/0", [(500, "internal")] * 6, "upload_failed", 5),
        ("/pages/0", [(401, "unauthenticated")], "upload_failed", 1),
        ("/pages/0", [(503, "unavailable")] * 6, "SUCCEEDED", 7),
    ],
)
def test_upload03_04_retry_policy(
    rq_check: PostgreSql, intake: StubIntake, path: str, replies: list[tuple[int, str]], outcome: str, count: int
):
    # UPLOAD-03/04: identical retries, five non-capacity failures, capacity retries beyond five, permanent refusal.
    intake.reply(path, *replies)
    answer = call(rq_check, request(rq_check, intake.address, timeoutMs=15000))
    attempts = [r for r in intake.records if r["path"] == path]
    assert len(attempts) == count
    assert all(attempt == attempts[0] for attempt in attempts)
    if outcome == "SUCCEEDED":
        assert answer == {"status": "SUCCEEDED"}
    else:
        assert answer["error"]["code"] == outcome
        assert "DO NOT PROPAGATE" not in answer["error"]["message"]
        assert intake.records[-1]["path"] == "/abort"


def test_obs02_upload07_trace_and_auth(rq_check: PostgreSql, intake: StubIntake):
    # OBS-02, UPLOAD-07: trace accompanies every operation; API-key-only intake auth.
    payload = request(rq_check, intake.address)
    payload["traceContext"] = {"traceId": "123", "parentId": "456", "samplingPriority": 2}
    intake.reply("/finalize", (401, "unauthenticated"))
    assert call(rq_check, payload)["error"]["code"] == "upload_failed"
    assert intake.records[-1]["path"] == "/abort"
    for record in intake.records:
        headers = record["headers"]
        assert headers["DD-API-KEY"] == "remote-query-api-key"
        assert headers["x-datadog-trace-id"] == "123"
        assert headers["x-datadog-parent-id"] == "456"
        assert headers["x-datadog-sampling-priority"] == "2"
        assert "Authorization" not in headers and "DD-APPLICATION-KEY" not in headers


@pytest.mark.parametrize("phase", ["capacity", "resolver"])
def test_time01_run_deadline(rq_check: PostgreSql, intake: StubIntake, monkeypatch: pytest.MonkeyPatch, phase: str):
    release = threading.Event()
    resolving = threading.Event()
    address = intake.address
    if phase == "capacity":
        intake.reply("/pages/0", *([(503, "unavailable")] * 100))
    else:
        original = socket.getaddrinfo

        def stall(*args: object, **kwargs: object) -> list[tuple]:
            resolving.set()
            release.wait(3)
            return original(*args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", stall)
        monkeypatch.setattr("datadog_checks.postgres.remote_queries.ABORT_TIMEOUT", 0.1)
        address = address.replace("127.0.0.1", "localhost")
    try:
        start = time.monotonic()
        answer = call(rq_check, request(rq_check, address, timeoutMs=150))
        assert answer["error"]["code"] == "timeout"
        assert time.monotonic() - start < 2
        if phase == "capacity":
            assert intake.records[-1]["path"] == "/abort"
        else:
            assert resolving.is_set() and not release.is_set()
            assert not intake.records
    finally:
        release.set()


@pytest.mark.parametrize("mode", ["run", "unschedule", "duplicate", "stalled_cancel"])
def test_cancel01_02_03_blocked_first_record(
    rq_check: PostgreSql,
    intake: StubIntake,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mode: str,
):
    # CANCEL-01/02/03: cross-thread cancellation before first row; teardown waits through abort.
    release = threading.Event()
    abandoned = threading.Event()
    abort_started = threading.Event()
    if mode == "unschedule":

        def hold_abort(record: dict) -> None:
            if record["path"] == "/abort":
                abort_started.set()
                release.wait(5)

        intake.callback = hold_abort
    if mode == "stalled_cancel":

        def block_cancel(handle: PGcancel, loop: asyncio.AbstractEventLoop, done: asyncio.Future[None]) -> None:
            try:
                abandoned.set()
                release.wait(10)
            finally:
                handle.free()

        monkeypatch.setattr("datadog_checks.postgres.remote_queries.capabilities.has_cancel_safe", lambda: False)
        monkeypatch.setattr("datadog_checks.postgres.remote_queries._send_legacy_cancel", block_cancel)
    rq_check._config = rq_check._config.model_copy(update={"application_name": "rq_spec_cancel"})
    payload = request(rq_check, intake.address, "SELECT pg_sleep(30)", timeoutMs=60000)
    count = 2 if mode == "duplicate" else 1
    with caplog.at_level("DEBUG"), ThreadPoolExecutor(2) as executor:
        futures = [executor.submit(call, rq_check, payload) for _ in range(count)]
        _wait_for_copy(rq_check, "rq_spec_cancel", count)
        start = time.monotonic()
        try:
            if mode == "unschedule":
                cancellation = executor.submit(rq_check.cancel)
                assert abort_started.wait(3)
                assert not cancellation.done()
                assert json.loads(rq_check.remote_query("not JSON"))["error"]["code"] == "cancelled"
                release.set()
                cancellation.result(5)
            else:
                rq_check.cancel_remote_query(payload["resultDelivery"]["crawlId"])
                assert time.monotonic() - start < 0.5
                rq_check.cancel_remote_query("unknown")
            answers = [future.result(8) for future in futures]
            assert time.monotonic() - start < 6.5
            if mode == "stalled_cancel":
                assert abandoned.is_set()
                assert any("cancel_request_abandoned" in r.message for r in caplog.records)
        finally:
            release.set()
    assert all(answer["error"]["code"] == "cancelled" for answer in answers)
    assert sum(r["path"] == "/abort" for r in intake.records) == count
    if mode == "unschedule":
        assert json.loads(rq_check.remote_query("not JSON"))["error"]["code"] == "cancelled"


@pytest.mark.parametrize("separate_checks", [False, True])
def test_query01_scale01_02_res02_connections(
    rq_check: PostgreSql,
    intake: StubIntake,
    integration_check: Callable[[dict], PostgreSql],
    aggregator: AggregatorStub,
    separate_checks: bool,
):
    # QUERY-01, SCALE-01/02, RES-02: scheduled monitoring runs while both remote connections are held.
    second_check = integration_check(rq_check.instance) if separate_checks else rq_check
    for check in (rq_check, second_check):
        check._config = check._config.model_copy(update={"application_name": "rq_spec_concurrency"})
    ready = threading.Barrier(3)
    release = threading.Event()

    def wait_for_both(record: dict) -> None:
        if record["path"] == "/descriptor":
            ready.wait(3)
            release.wait(5)

    intake.callback = wait_for_both
    with ThreadPoolExecutor(2) as executor:
        first = executor.submit(
            call,
            rq_check,
            request(rq_check, intake.address, "SELECT current_user, current_database(), pg_backend_pid() AS pid"),
        )
        second = executor.submit(
            call,
            second_check,
            request(second_check, intake.address, "SELECT current_user, current_database(), pg_backend_pid() AS pid"),
        )
        try:
            ready.wait(3)
            with rq_check.db() as monitoring:
                monitoring_pid = monitoring.execute("SELECT pg_backend_pid()").fetchone()[0]
                connections = monitoring.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE application_name = 'rq_spec_concurrency'"
                ).fetchone()[0]
                assert connections == 3
            assert rq_check.run() == ""
            aggregator.assert_metric("postgresql.uptime", at_least=1)
        finally:
            release.set()
        assert first.result(5)["status"] == second.result(5)["status"] == "SUCCEEDED"
    pids = [int(page["body"].split(b",")[-1]) for page in intake.pages]
    assert len(set(pids + [monitoring_pid])) == 3
    assert all(page["body"].startswith(b"datadog,datadog_test,") for page in intake.pages)


@pytest.mark.parametrize("mode", ["refused", "stalled"])
def test_abort01_bounded_abort_preserves_answer(
    rq_check: PostgreSql, intake: StubIntake, monkeypatch: pytest.MonkeyPatch, mode: str
):
    release = threading.Event()
    if mode == "refused":
        intake.reply("/abort", (401, "unauthenticated"))
    else:
        monkeypatch.setattr("datadog_checks.postgres.remote_queries.ABORT_TIMEOUT", 0.1)

        def hold_abort(record: dict) -> None:
            if record["path"] == "/abort":
                release.wait(3)

        intake.callback = hold_abort
    try:
        start = time.monotonic()
        answer = call(rq_check, request(rq_check, intake.address, "SELECT 1/0"))
        assert answer["error"]["code"] == "query_failed"
        assert intake.records[-1]["path"] == "/abort"
        assert time.monotonic() - start < 2
    finally:
        release.set()


def _wait_for_copy(check: PostgreSql, application_name: str, count: int) -> None:
    kwargs = check.build_connection_args().as_kwargs(dbname=check._config.dbname)
    kwargs.update(user=USER_ADMIN, password=PASSWORD_ADMIN)
    deadline = time.monotonic() + 3
    with psycopg.connect(**kwargs, autocommit=True) as observer:
        while time.monotonic() < deadline:
            active = observer.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name = %s AND query LIKE 'COPY (%%' AND state = 'active'",
                (application_name,),
            ).fetchone()[0]
            if active == count:
                return
            threading.Event().wait(0.01)
    pytest.fail("Remote COPY did not become active")


@pytest.fixture
def rq_schema(rq_check: PostgreSql) -> Iterator[psycopg.Connection]:
    kwargs = rq_check.build_connection_args().as_kwargs(dbname=rq_check._config.dbname)
    kwargs.update(user=USER_ADMIN, password=PASSWORD_ADMIN)
    with psycopg.connect(**kwargs, autocommit=True) as admin:
        admin.execute("CREATE SCHEMA rq_spec AUTHORIZATION datadog")
        admin.execute("CREATE TABLE rq_spec.writes(i integer)")
        admin.execute("GRANT ALL ON rq_spec.writes TO datadog")
        admin.execute("""
            CREATE FUNCTION rq_spec.evaluations() RETURNS integer LANGUAGE plpgsql AS $$
            BEGIN
                PERFORM set_config('rq_spec.evaluations',
                    (COALESCE(NULLIF(current_setting('rq_spec.evaluations', true), ''), '0')::int + 1)::text, true);
                RETURN current_setting('rq_spec.evaluations')::int;
            END $$
        """)
        admin.execute("CREATE DOMAIN rq_spec.amount AS numeric(10,2)")
        try:
            yield admin
        finally:
            admin.execute("DROP SCHEMA rq_spec CASCADE")


@pytest.mark.parametrize(
    "query,expected",
    [
        ("SELECT rq_spec.evaluations() AS count", "SUCCEEDED"),
        ("SELECT rq_spec.evaluations() AS count -- trailing comment", "SUCCEEDED"),
        ("SELECT rq_spec.evaluations() AS count; SELECT 2", "FAILED"),
    ],
)
def test_query05_describe_without_evaluating(
    rq_check: PostgreSql, intake: StubIntake, rq_schema: psycopg.Connection, query: str, expected: str
):
    answer = call(rq_check, request(rq_check, intake.address, query))
    assert answer["status"] == expected
    if expected == "SUCCEEDED":
        assert intake.pages[0]["body"] == b"1\n"
    else:
        assert answer["error"]["code"] == "query_failed"
        assert [r["path"] for r in intake.records] == ["/abort"]


@pytest.mark.parametrize(
    "mode", ["http_proxy", "http_bypass", "https_trusted", "https_untrusted", "https_proxy", "redirect"]
)
def test_upload06_proxy_and_tls(rq_check: PostgreSql, monkeypatch: pytest.MonkeyPatch, mode: str):
    server = StubIntake()
    proxy = StubProxy()
    address = server.address
    certs = Path(__file__).parent / "fixtures" / "remote_queries"
    if mode.startswith("https"):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certs / "ca.pem", certs / "server.key")
        server.server.socket = context.wrap_socket(server.server.socket, server_side=True)
        address = address.replace("http:", "https:")
        if mode != "https_untrusted":
            monkeypatch.setenv("SSL_CERT_FILE", str(certs / "ca.pem"))
    if mode == "redirect":
        server.reply("/pages/0", (302, "redirect"))
    settings = {}
    if "proxy" in mode or mode == "http_bypass":
        settings = {"http": proxy.address, "https": proxy.address}
        if mode == "http_bypass":
            settings["no_proxy"] = ["127.0.0.1"]
    monkeypatch.setattr(
        "datadog_checks.postgres.postgres.datadog_agent.get_config",
        lambda key: settings if key == "proxy" else "remote-query-api-key",
    )
    server.start()
    proxy.start()
    try:
        answer = call(rq_check, request(rq_check, address))
        if mode in ("https_untrusted", "redirect"):
            assert answer["error"]["code"] == "upload_failed"
            if mode == "https_untrusted":
                assert not server.records
            else:
                assert len(server.pages) == 1
                assert server.records[-1]["path"] == "/abort"
        else:
            assert answer == {"status": "SUCCEEDED"}
            assert len(server.records) == 3
        assert bool(proxy.requests) == ("proxy" in mode)
    finally:
        server.close()
        proxy.close()


@pytest.mark.parametrize("phase", ["connect", "response", "send", "progress"])
def test_upload05_attempt_bounds(rq_check: PostgreSql, intake: StubIntake, monkeypatch: pytest.MonkeyPatch, phase: str):
    # UPLOAD-05: real sockets that cannot complete a TLS handshake, send, or response.
    release = threading.Event()
    arrivals = []
    transport = "datadog_checks.postgres.remote_query_intake"
    monkeypatch.setattr(f"{transport}.CONNECT_TIMEOUT", 0.04)
    monkeypatch.setattr(f"{transport}.SEND_STALL_TIMEOUT", 0.04)
    monkeypatch.setattr(f"{transport}.OTHER_TIMEOUT", 0.08)
    monkeypatch.setattr(f"{transport}.PAGE_TIMEOUT", 0.15)
    monkeypatch.setattr(f"{transport}.random.uniform", lambda low, high: 0)
    monkeypatch.setattr("datadog_checks.postgres.remote_queries.ABORT_TIMEOUT", 0.1)
    stalled = None
    if phase == "connect":

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                arrivals.append(1)
                release.wait(3)

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True

        stalled = Server(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=stalled.serve_forever, daemon=True)
        worker.start()
        address = f"https://127.0.0.1:{stalled.server_address[1]}/intake"
        payload = request(rq_check, address)
    elif phase == "response":

        def response(record: dict) -> None:
            if record["path"] == "/descriptor":
                arrivals.append(1)
                release.wait(3)

        intake.callback = response
        payload = request(rq_check, intake.address)
    elif phase == "progress":

        def slow_body(_connection: socket.socket, reader: BinaryIO, length: int) -> bytes:
            data = bytearray()
            while len(data) < length:
                chunk = reader.read(min(8192, length - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
                release.wait(0.05)
            return bytes(data)

        intake.body_reader = slow_body
        monkeypatch.setattr(f"{transport}.SEND_STALL_TIMEOUT", 0.5)
        monkeypatch.setattr(f"{transport}.PAGE_TIMEOUT", 4)
        monkeypatch.setattr(f"{transport}.OTHER_TIMEOUT", 2)
        payload = request(
            rq_check, intake.address, "SELECT repeat('x', 262144) AS value", maxFileBytes=1048576, maxRowBytes=1048576
        )
    else:

        def body(path: str) -> None:
            if "/pages/" in path:
                arrivals.append(1)
                release.wait(3)

        intake.before_body = body
        payload = request(
            rq_check,
            intake.address,
            "SELECT repeat('x', 8388608) AS value",
            maxRowBytes=16777216,
            maxFileBytes=16777216,
            maxResultBytes=33554432,
        )
    try:
        start = time.monotonic()
        answer = call(rq_check, payload)
        if phase == "progress":
            assert answer == {"status": "SUCCEEDED"}
            assert len(intake.pages) == 1
            assert time.monotonic() - start > 0.5
        else:
            assert answer["error"]["code"] == "upload_failed"
            assert time.monotonic() - start < 2
            assert len(arrivals) >= 5
    finally:
        release.set()
        if stalled:
            stalled.shutdown()
            stalled.server_close()
            worker.join(3)


def test_obs03_data_free_run_logs(rq_check: PostgreSql, intake: StubIntake, caplog: pytest.LogCaptureFixture):
    payload = request(rq_check, intake.address, "SELECT 'result-secret'::integer AS secret")
    with caplog.at_level("DEBUG"):
        answer = call(rq_check, payload)
    assert answer["error"]["code"] == "query_failed"
    lines = [record.message for record in caplog.records if record.message.startswith("Remote query ")]
    assert lines
    for line in lines:
        assert all(payload["resultDelivery"][key] in line for key in ("crawlId", "taskId", "uploadId"))
        assert all(secret not in line for secret in ("result-secret", "remote-query-api-key", "SELECT"))


@pytest.mark.remote_query_quality
def test_perf01_res01_median_of_five(
    rq_check: PostgreSql,
    intake: StubIntake,
    pytestconfig: pytest.Config,
    record_property: Callable[[str, object], None],
):
    if not pytestconfig.getoption("--remote-query-quality"):
        pytest.skip("requires --remote-query-quality on an idle m6gd.4xlarge")
    # PERF-01 / RES-01: real query, local intake, >=1 GiB, one framing core; no result retention by the stub.
    intake.retain_bodies = False
    payload = request(
        rq_check,
        intake.address,
        "SELECT repeat('x', 65535) AS value FROM generate_series(1,16384)",
        maxFileBytes=16 * 1024 * 1024,
        maxRowBytes=16 * 1024 * 1024,
        maxResultBytes=2 * 1024**3,
        maxPages=1024,
        timeoutMs=600000,
    )
    original_affinity = os.sched_getaffinity(0)
    rates, memory = [], []

    def anonymous_bytes() -> int:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("RssAnon:"):
                return int(line.split()[1]) * 1024
        raise RuntimeError("anonymous memory measurement is unavailable")

    try:
        os.sched_setaffinity(0, {min(original_affinity)})
        baseline = anonymous_bytes()
        for _ in range(5):
            peaks = [baseline]
            stop = threading.Event()

            def sample(stop: threading.Event = stop, peaks: list[int] = peaks) -> None:
                while not stop.wait(0.005):
                    peaks.append(anonymous_bytes())

            sampler = threading.Thread(target=sample, daemon=True)
            sampler.start()
            start = time.perf_counter()
            try:
                assert call(rq_check, payload) == {"status": "SUCCEEDED"}
                assert sum(int(page["headers"]["Content-Length"]) for page in intake.pages) >= 1024**3
            finally:
                stop.set()
                sampler.join(1)
            rates.append(1024 / (time.perf_counter() - start))
            memory.append(max(peaks) - baseline)
            intake.records.clear()
        median_rate, median_memory = statistics.median(rates), statistics.median(memory)
        record_property("median_mib_per_second", median_rate)
        record_property("median_incremental_anonymous_bytes", median_memory)
        assert median_rate >= 50
        assert (
            median_memory
            <= payload["resultDelivery"]["limits"]["maxFileBytes"] + payload["resultDelivery"]["limits"]["maxRowBytes"]
        )
    finally:
        os.sched_setaffinity(0, original_affinity)
