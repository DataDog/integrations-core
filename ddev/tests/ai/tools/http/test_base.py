# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import gzip
import json
from pathlib import Path

import httpx
import pytest

from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.fs.read_file import ReadFileTool
from ddev.ai.tools.http.http_get import HttpGetTool
from ddev.ai.tools.http.http_post import HttpPostTool
from ddev.ai.tools.http.response_format import MAX_BODY_BYTES, MAX_OUTPUT_CHARS
from ddev.ai.tools.http.response_store import ResponseStore
from ddev.ai.tools.shell.grep import GrepTool

from .helpers import TARGET, RecordingTransport, respond, saved_files

OPENAPI_URL = f"{TARGET}/api/openapi.json"


def openapi_document(schema_count: int = 400) -> dict:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Prefect", "version": "3"},
        "components": {
            "schemas": {
                f"Schema{i}_{'n' * 40}": {"type": "object", "properties": {"limit": {"type": "integer"}}}
                for i in range(schema_count)
            }
        },
    }


@pytest.fixture
def store(tmp_path: Path) -> ResponseStore:
    return ResponseStore(tmp_path / "exec")


def get_tool(store: ResponseStore | None, transport: httpx.AsyncBaseTransport) -> HttpGetTool:
    return HttpGetTool(store, transport=transport)


@pytest.mark.parametrize("url", ["http://user:pass@localhost:4200/api", "http://tok@127.0.0.1:4200/api"])
async def test_embedded_credentials_are_rejected_for_every_method(url: str):
    for tool_cls in (HttpGetTool, HttpPostTool):
        transport = respond(httpx.Response(200))

        result = await tool_cls(transport=transport).run({"url": url})

        assert result.success is False
        assert "embedded credentials" in result.error
        assert transport.requests == []


@pytest.mark.parametrize("tool_cls,method", [(HttpGetTool, "GET"), (HttpPostTool, "POST")])
@pytest.mark.parametrize(
    "body_input,expected_content,content_type",
    [
        ({"json": {"limit": 1, "sort": None}}, b'{"limit":1,"sort":null}', "application/json"),
        ({"json": None}, b"null", "application/json"),
        ({"content": "<filter>café</filter>"}, "<filter>café</filter>".encode(), "application/xml"),
    ],
)
async def test_body_and_headers_are_sent_for_each_verb(
    tool_cls: type[HttpGetTool] | type[HttpPostTool],
    method: str,
    body_input: dict,
    expected_content: bytes,
    content_type: str,
):
    transport = respond(httpx.Response(200, text="ok"))
    headers = {"Authorization": "Bearer deliberate-token", "Accept": "application/json"}
    if "content" in body_input:
        headers["Content-Type"] = content_type

    result = await tool_cls(transport=transport).run({"url": OPENAPI_URL, "headers": headers, **body_input})

    assert result.success is True
    (request,) = transport.requests
    assert request.method == method
    if "json" in body_input:
        assert json.loads(request.content) == body_input["json"]
    else:
        assert request.content == expected_content
    assert request.headers["authorization"] == headers["Authorization"]
    assert request.headers["accept"] == headers["Accept"]
    assert request.headers["content-type"] == content_type


@pytest.mark.parametrize("json_body", [{"limit": 1}, None])
async def test_conflicting_body_inputs_are_rejected(json_body: object):
    transport = respond(httpx.Response(200))

    result = await HttpGetTool(transport=transport).run({"url": OPENAPI_URL, "json": json_body, "content": "raw"})

    assert result.success is False
    assert "either json or content" in result.error
    assert transport.requests == []


async def test_large_json_is_saved_formatted_and_result_is_bounded(store: ResponseStore):
    document = openapi_document()

    result = await get_tool(store, respond(httpx.Response(200, json=document))).run({"url": OPENAPI_URL})

    assert result.success is True
    assert len(result.data) <= MAX_OUTPUT_CHARS
    payload = json.loads(result.data)
    assert payload["status"] == 200
    assert payload["complete"] is True
    assert payload["summary"]["keys"] == ["openapi", "info", "components"]
    saved = Path(payload["saved_to"])
    assert json.loads(saved.read_text()) == document
    assert saved.read_text().count("\n") > len(document["components"]["schemas"])
    metadata = json.loads(Path(payload["metadata_path"]).read_text())
    assert metadata["method"] == "GET"
    assert metadata["url"] == OPENAPI_URL
    assert metadata["representation"] == "formatted_json"


@pytest.mark.parametrize("body", ['{"ok":true}', "plain text café", ""])
async def test_save_response_preserves_small_response_and_returns_body(store: ResponseStore, body: str):
    response = httpx.Response(200, text=body)
    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL, "save_response": True})

    assert result.success is True
    payload = json.loads(result.data)
    assert payload["body"] == body
    assert Path(payload["saved_to"]).read_text() == body
    assert Path(payload["metadata_path"]).is_file()
    assert len(result.data) <= MAX_OUTPUT_CHARS


async def test_saved_body_that_cannot_fit_with_paths_uses_summary(store: ResponseStore):
    body = "x" * (MAX_OUTPUT_CHARS - 100)
    result = await get_tool(store, respond(httpx.Response(200, text=body))).run(
        {"url": OPENAPI_URL, "save_response": True}
    )

    payload = json.loads(result.data)
    assert payload["summary"]["type"] == "text"
    assert Path(payload["saved_to"]).read_text() == body
    assert len(result.data) <= MAX_OUTPUT_CHARS


async def test_post_metadata_records_request_without_credentials(store: ResponseStore):
    tool = HttpPostTool(store, transport=respond(httpx.Response(200, json=[])))

    result = await tool.run(
        {
            "url": f"{TARGET}/api/task_runs/filter",
            "query": {"api_key": "s3cret", "page": 1},
            "json": {"limit": 1},
            "headers": {
                "Authorization": "Bearer auth-secret",
                "Cookie": "session=cookie-secret",
                "X-API-Key": "header-secret",
                "Accept": "application/json",
            },
            "save_response": True,
        }
    )

    payload = json.loads(result.data)
    assert result.success is True
    assert json.loads(payload["body"]) == []
    assert json.loads(Path(payload["saved_to"]).read_text()) == []
    metadata_text = Path(payload["metadata_path"]).read_text()
    assert all(secret not in metadata_text for secret in ("s3cret", "auth-secret", "cookie-secret", "header-secret"))
    metadata = json.loads(metadata_text)
    assert metadata["method"] == "POST"
    assert metadata["request_body"] == {"limit": 1}
    assert "page=1" in metadata["url"]
    assert metadata["request_headers"] == {
        "Authorization": "REDACTED",
        "Cookie": "REDACTED",
        "X-API-Key": "REDACTED",
        "Accept": "application/json",
    }


async def test_large_error_response_keeps_status_and_excerpt(store: ResponseStore):
    detail = {"detail": [{"loc": ["body", "task_runs", "end_time"], "msg": "Extra inputs"}] * 200}

    result = await get_tool(store, respond(httpx.Response(422, json=detail))).run({"url": OPENAPI_URL})

    payload = json.loads(result.data)
    assert payload["status"] == 422
    assert "end_time" in payload["excerpt"]
    assert json.loads(Path(payload["saved_to"]).read_text()) == detail


async def test_huge_redirect_location_header_does_not_bypass_output_cap(store: ResponseStore):
    huge_location = "http://elsewhere/" + "x" * (MAX_OUTPUT_CHARS * 2)
    response = httpx.Response(302, json={"ok": True}, headers={"location": huge_location})

    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL, "save_response": True})

    assert result.success is True
    assert len(result.data) <= MAX_OUTPUT_CHARS
    payload = json.loads(result.data)
    assert len(payload["redirect_not_followed"]) < len(huge_location)


async def test_invalid_json_is_saved_as_text(store: ResponseStore):
    body = "{not json" + "x" * MAX_OUTPUT_CHARS
    response = httpx.Response(200, content=body.encode(), headers={"content-type": "application/json"})

    payload = json.loads((await get_tool(store, respond(response)).run({"url": OPENAPI_URL})).data)

    assert payload["representation"] == "text"
    assert "not valid JSON" in payload["note"]
    assert Path(payload["saved_to"]).read_text() == body


async def test_unsavable_response_reports_status_and_excerpt(tmp_path: Path):
    (tmp_path / "blocked").write_text("not a directory")
    store = ResponseStore(tmp_path / "blocked" / "exec")

    result = await get_tool(store, respond(httpx.Response(200, json={"ok": True}))).run(
        {"url": OPENAPI_URL, "save_response": True}
    )

    assert result.success is False
    payload = json.loads(result.error)
    assert payload["status"] == 200
    assert "not saved" in payload["error"]
    assert "ok" in payload["excerpt"]


async def test_decompressed_size_limit_discards_response(store: ResponseStore):
    compressed = gzip.compress(b"x" * (MAX_BODY_BYTES + 1))
    response = httpx.Response(
        200, content=compressed, headers={"content-encoding": "gzip", "content-type": "text/plain"}
    )

    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL, "save_response": True})

    assert result.success is False
    assert json.loads(result.error)["complete"] is False
    assert len(compressed) < MAX_BODY_BYTES
    assert saved_files(store.root) == []


async def test_cancellation_during_download_writes_nothing(store: ResponseStore):
    started = asyncio.Event()

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"{"
            started.set()
            await asyncio.Event().wait()

    transport = RecordingTransport(lambda request: httpx.Response(200, stream=SlowStream()))
    task = asyncio.create_task(get_tool(store, transport).run({"url": OPENAPI_URL, "save_response": True}))
    async with asyncio.timeout(5):
        await started.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
    assert saved_files(store.root) == []


async def test_binary_response_is_not_saved(store: ResponseStore):
    response = httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})

    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL, "save_response": True})

    assert "not supported" in json.loads(result.data)["note"]
    assert saved_files(store.root) == []


async def test_saved_response_is_readable_by_another_agents_file_tools(tmp_path: Path):
    store = ResponseStore(tmp_path / ".ddev" / "ai-runs" / "flow" / "http_responses" / "exec")
    result = await get_tool(store, respond(httpx.Response(200, json=openapi_document(50)))).run({"url": OPENAPI_URL})
    saved_to = json.loads(result.data)["saved_to"]
    policy = FileAccessPolicy(write_root=tmp_path, integration_name="prefect")

    grep = await GrepTool(policy).run({"pattern": "Schema7_", "path": saved_to, "recursive": False})
    # grep line numbers are 1-based; read_file offsets are 0-based.
    line = int(grep.data.split(":", 1)[0])
    read = await ReadFileTool(FileRegistry(policy=policy), "goal-reviewer").run(
        {"path": saved_to, "offset": line - 1, "limit": 5}
    )

    assert read.success is True
    assert "Schema7_" in read.data
    assert '"limit"' in read.data
