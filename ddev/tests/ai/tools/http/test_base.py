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
from ddev.ai.tools.http.response_format import MAX_BUFFER_BYTES, MAX_INLINE_CHARS, MAX_LOCATION_CHARS
from ddev.ai.tools.http.response_store import ResponseStore
from ddev.ai.tools.shell.grep import GrepTool

from .helpers import TARGET, RecordingTransport, parse_result, respond, saved_files

OPENAPI_URL = f"{TARGET}/api/openapi.json"


def openapi_document(schema_count: int = 1000) -> dict:
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


def get_tool(store: ResponseStore, transport: httpx.AsyncBaseTransport) -> HttpGetTool:
    return HttpGetTool(store, transport=transport)


@pytest.mark.parametrize("url", ["http://user:pass@localhost:4200/api", "http://tok@127.0.0.1:4200/api"])
async def test_embedded_credentials_are_rejected_for_every_method(url: str, store: ResponseStore):
    for tool_cls in (HttpGetTool, HttpPostTool):
        transport = respond(httpx.Response(200))

        result = await tool_cls(store, transport=transport).run({"url": url})

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
    store: ResponseStore,
):
    transport = respond(httpx.Response(200, text="ok"))
    headers = {"Authorization": "Bearer deliberate-token", "Accept": "application/json"}
    if "content" in body_input:
        headers["Content-Type"] = content_type

    result = await tool_cls(store, transport=transport).run({"url": OPENAPI_URL, "headers": headers, **body_input})

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
async def test_conflicting_body_inputs_are_rejected(json_body: object, store: ResponseStore):
    transport = respond(httpx.Response(200))

    result = await HttpGetTool(store, transport=transport).run(
        {"url": OPENAPI_URL, "json": json_body, "content": "raw"}
    )

    assert result.success is False
    assert "either json or content" in result.error
    assert transport.requests == []


async def test_large_json_is_saved_formatted_and_only_metadata_is_returned(store: ResponseStore):
    document = openapi_document()

    result = await get_tool(store, respond(httpx.Response(200, json=document))).run({"url": OPENAPI_URL})

    assert result.success is True
    fields, body = parse_result(result.data)
    assert body is None
    assert fields["status"] == 200
    assert fields["representation"] == "formatted_json"
    saved = Path(fields["saved_to"])
    saved_text = saved.read_text(encoding="utf-8")
    assert json.loads(saved_text) == document
    assert fields["lines"] == saved_text.count("\n") > len(document["components"]["schemas"])
    metadata = json.loads(Path(fields["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["method"] == "GET"
    assert metadata["url"] == OPENAPI_URL
    assert metadata["representation"] == "formatted_json"


@pytest.mark.parametrize("body", ['{"ok":true}', "plain text café", ""])
async def test_small_response_is_saved_and_returned_inline(store: ResponseStore, body: str):
    result = await get_tool(store, respond(httpx.Response(200, text=body))).run({"url": OPENAPI_URL})

    assert result.success is True
    fields, inline = parse_result(result.data)
    assert inline == body
    assert Path(fields["saved_to"]).read_text(encoding="utf-8") == body
    assert Path(fields["metadata_path"]).is_file()


@pytest.mark.parametrize("size,inlined", [(MAX_INLINE_CHARS, True), (MAX_INLINE_CHARS + 1, False)])
async def test_inline_limit_counts_body_characters(store: ResponseStore, size: int, inlined: bool):
    # Multi-byte characters: the limit is on decoded characters, not bytes.
    body = "é" * size

    result = await get_tool(store, respond(httpx.Response(200, text=body))).run({"url": OPENAPI_URL})

    fields, inline = parse_result(result.data)
    assert inline == (body if inlined else None)
    assert Path(fields["saved_to"]).read_text(encoding="utf-8") == body


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
        }
    )

    fields, body = parse_result(result.data)
    assert result.success is True
    assert json.loads(body) == []
    assert json.loads(Path(fields["saved_to"]).read_text(encoding="utf-8")) == []
    metadata_text = Path(fields["metadata_path"]).read_text(encoding="utf-8")
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


async def test_huge_redirect_location_header_is_bounded(store: ResponseStore):
    huge_location = "http://elsewhere/" + "x" * (MAX_LOCATION_CHARS * 2)
    response = httpx.Response(302, json={"ok": True}, headers={"location": huge_location})

    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL})

    assert result.success is True
    fields, _ = parse_result(result.data)
    assert fields["redirect_not_followed"].startswith(huge_location[:MAX_LOCATION_CHARS])
    assert len(fields["redirect_not_followed"]) < len(huge_location)


async def test_invalid_json_is_saved_as_text(store: ResponseStore):
    body = "{not json"
    response = httpx.Response(200, content=body.encode(), headers={"content-type": "application/json"})

    fields, _ = parse_result((await get_tool(store, respond(response)).run({"url": OPENAPI_URL})).data)

    assert fields["representation"] == "text"
    assert "not valid JSON" in fields["note"]
    assert Path(fields["saved_to"]).read_text(encoding="utf-8") == body


@pytest.mark.parametrize("fits", [True, False])
async def test_unsavable_response_returns_body_only_when_it_fits(tmp_path: Path, fits: bool):
    (tmp_path / "blocked").write_text("not a directory")
    store = ResponseStore(tmp_path / "blocked" / "exec")
    body = "x" * (MAX_INLINE_CHARS if fits else MAX_INLINE_CHARS + 1)

    result = await get_tool(store, respond(httpx.Response(200, text=body))).run({"url": OPENAPI_URL})

    if fits:
        assert result.success is True
        fields, inline = parse_result(result.data)
        assert inline == body
        assert "saved_to" not in fields
        assert "Cannot create response directory" in fields["save_error"]
    else:
        assert result.success is False
        fields = json.loads(result.error)
        assert fields["status"] == 200
        assert "not saved" in fields["error"]


async def test_decompressed_response_spills_to_disk(store: ResponseStore):
    compressed = gzip.compress(b"x" * (MAX_BUFFER_BYTES + 1))
    response = httpx.Response(
        200, content=compressed, headers={"content-encoding": "gzip", "content-type": "text/plain"}
    )

    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL})

    assert result.success is True
    fields, _ = parse_result(result.data)
    assert fields["received_bytes"] == MAX_BUFFER_BYTES + 1
    assert Path(fields["saved_to"]).read_bytes() == b"x" * (MAX_BUFFER_BYTES + 1)
    assert len(compressed) < MAX_BUFFER_BYTES


async def test_cancellation_during_download_writes_nothing(store: ResponseStore):
    started = asyncio.Event()

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"{"
            started.set()
            await asyncio.Event().wait()

    transport = RecordingTransport(lambda request: httpx.Response(200, stream=SlowStream()))
    task = asyncio.create_task(get_tool(store, transport).run({"url": OPENAPI_URL}))
    async with asyncio.timeout(5):
        await started.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
    assert saved_files(store.root) == []


async def test_binary_response_body_is_never_read(store: ResponseStore):
    class UnreadableStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            raise AssertionError("binary body was read")
            yield b""

    response = httpx.Response(
        200, stream=UnreadableStream(), headers={"content-type": "image/png", "content-length": "123456"}
    )

    result = await get_tool(store, respond(response)).run({"url": OPENAPI_URL})

    assert result.success is True
    fields = json.loads(result.data)
    assert fields["status"] == 200
    assert fields["content_type"] == "image/png"
    assert fields["content_length"] == "123456"
    assert "not downloaded" in fields["note"]
    assert saved_files(store.root) == []


async def test_saved_response_is_readable_by_another_agents_file_tools(tmp_path: Path):
    store = ResponseStore(tmp_path / ".ddev" / "ai-runs" / "flow" / "http_responses" / "exec")
    result = await get_tool(store, respond(httpx.Response(200, json=openapi_document(50)))).run({"url": OPENAPI_URL})
    saved_to = parse_result(result.data)[0]["saved_to"]
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
