# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.remote_queries import RecordFramer, RemoteQueryError, ResultSizer

from .remote_query_helpers import call, request

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("raw", ['[]', 'null', '1', '"resolve"', '{}', '{"operation":"other"}', '{'])
def test_req01_operations(check: PostgreSql, raw: str):
    assert json.loads(check.remote_query(raw))["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "field,value",
    [
        ("unknown", True),
        ("query", ""),
        ("query", "\x00"),
        ("query", 1),
        ("includeSchema", 1),
        ("target", {"host": "db", "port": True, "dbname": "db"}),
        ("target", {"host": "db", "port": 65536, "dbname": "db"}),
        ("target", {"host": "db", "port": 5432}),
        ("target", {"database_instance": " instance "}),
        ("target", {"database_instance": "i", "host": ""}),
        ("traceContext", {"traceId": "0", "parentId": "1", "samplingPriority": 1}),
        ("traceContext", {"traceId": "1", "parentId": "2", "samplingPriority": True}),
        ("resultDelivery.crawlId", "not-uuid"),
        ("resultDelivery.taskId", 1),
        ("resultDelivery.uploadId", "../other/upload"),
        ("resultDelivery.baseUrl", ""),
        ("resultDelivery.limits.maxPages", 0),
        ("resultDelivery.limits.timeoutMs", 1.5),
        ("resultDelivery.limits.maxRowBytes", True),
        ("resultDelivery.limits.extra", 1),
        ("resultDelivery.extra", 1),
        ("resultDelivery.runId", "00000000-0000-0000-0000-000000000001"),
        ("-operation", None),
        ("-target", None),
        ("-query", None),
        ("-includeSchema", None),
        ("-resultDelivery", None),
    ],
)
def test_req02_validation(check: PostgreSql, field: str, value: object):
    payload = request(check, "http://127.0.0.1:1")
    if field.startswith("-"):
        del payload[field[1:]]
        assert call(check, payload)["error"]["code"] == "invalid_request"
        return
    parts = field.split(".")
    obj = payload
    for part in parts[:-1]:
        obj = obj[part]
    obj[parts[-1]] = value
    assert call(check, payload)["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "host,port,dbname,matched",
    [
        (" LOCALHOST. ", 5432, "dbname", True),
        ("localhost..", 5432, "dbname", False),
        ("localhost", 5433, "dbname", False),
        ("localhost", 5432, "DBNAME", False),
    ],
)
def test_match01_host_target(check: PostgreSql, host: str, port: int, dbname: str, matched: bool):
    answer = call(check, {"operation": "resolve", "target": {"host": host, "port": port, "dbname": dbname}})
    assert answer == {"status": "MATCHED"} if matched else answer["error"]["code"] == "target_not_found"


@pytest.mark.parametrize("suffix,matched", [("", True), ("different", False)])
def test_match02_instance_target(check: PostgreSql, suffix: str, matched: bool):
    answer = call(check, {"operation": "resolve", "target": {"database_instance": check.database_identifier + suffix}})
    assert answer == {"status": "MATCHED"} if matched else answer["error"]["code"] == "target_not_found"


def test_match03_last_discovery_snapshot(integration_check: Callable[[dict], PostgreSql], pg_instance: dict):
    pg_instance["database_autodiscovery"] = {"enabled": True}
    check = integration_check(pg_instance)
    check.autodiscovery.remote_query_databases = ("other",)
    for database, status in [(pg_instance["dbname"], "MATCHED"), ("other", "MATCHED"), ("absent", "FAILED")]:
        answer = call(
            check,
            {
                "operation": "resolve",
                "target": {"host": pg_instance["host"], "port": int(pg_instance["port"]), "dbname": database},
            },
        )
        assert answer["status"] == status


@pytest.mark.parametrize("blocks", [[b'1,"a\nb","c""d"\n2,\\N,\n'], [b'1,"a\n', b'b","c"', b'"d"\n2,\\N,\n']])
def test_size03_complete_records(blocks: list[bytes]):
    framer = RecordFramer(100)
    records = [bytes(record) for block in blocks for record in framer.feed(block)]
    framer.finish()
    assert records == [b'1,"a\nb","c""d"\n', b'2,\\N,\n']
    truncated = RecordFramer(100)
    list(truncated.feed(b'"unterminated\n'))
    with pytest.raises(RemoteQueryError, match="incomplete COPY record"):
        truncated.finish()


@pytest.mark.parametrize("blocks", [[b"1234", b"5", b"should not be read\n"], [b"12345\n"]])
def test_size04_row_limit(blocks: list[bytes]):
    framer = RecordFramer(4)
    with pytest.raises(RemoteQueryError) as error:
        for block in blocks:
            list(framer.feed(block))
    assert error.value.code == "row_too_large"


@pytest.mark.parametrize("schema", [True, False])
def test_size01_estimate_includes_repeated_names(check: PostgreSql, schema: bool):
    delivery = request(check, "http://127.0.0.1:1")["resultDelivery"]
    short = ResultSizer(delivery, [{"column_name": "a", "vendor_data_type": "text"}], schema, "agent")
    long = ResultSizer(delivery, [{"column_name": "λ" * 50, "vendor_data_type": "text"}], schema, "agent")
    # The 99 extra UTF-8 name bytes occur in each row, and once more in the optional schema.
    assert long.page_bytes(100, 2) - short.page_bytes(100, 2) == 99 * (3 if schema else 2)


def test_obs01_safe_unexpected_answer(check: PostgreSql, monkeypatch: pytest.MonkeyPatch):
    def explode(*args: object) -> None:
        raise RuntimeError("SECRET query, result, credential, connection string")

    monkeypatch.setattr("datadog_checks.postgres.postgres.match", explode)
    answer = check.remote_query(json.dumps({"operation": "resolve", "target": {"database_instance": "i"}}))
    assert json.loads(answer) == {
        "status": "FAILED",
        "error": {"code": "internal_error", "message": "Remote query failed unexpectedly."},
    }


@pytest.mark.parametrize("timeout,valid", [(None, True), (1, True), (1000, True), (0, False), (-1, False)])
def test_config01_statement_timeout(
    integration_check: Callable[[dict], PostgreSql], pg_instance: dict, timeout: int | None, valid: bool
):
    if timeout is not None:
        pg_instance["remote_queries"] = {"timeout_ms": timeout}
    if valid:
        check = integration_check(pg_instance)
        assert (
            check._config.remote_queries is None
            if timeout is None
            else check._config.remote_queries.timeout_ms == timeout
        )
    else:
        with pytest.raises(ValidationError):
            integration_check(pg_instance)
