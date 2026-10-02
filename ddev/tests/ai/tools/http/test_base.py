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
from ddev.ai.tools.http.base import MAX_BODY_BYTES, MAX_OUTPUT_CHARS
from ddev.ai.tools.http.http_get import HttpGetTool
from ddev.ai.tools.http.http_post import HttpPostTool
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


async def test_save_response_preserves_small_response(store: ResponseStore):
    result = await get_tool(store, respond(httpx.Response(200, json={"ok": True}))).run(
        {"url": OPENAPI_URL, "save_response": True}
    )

    assert json.loads(Path(json.loads(result.data)["saved_to"]).read_text()) == {"ok": True}


async def test_post_metadata_records_request_without_credentials(store: ResponseStore):
    tool = HttpPostTool(store, transport=respond(httpx.Response(200, json=[])))

    result = await tool.run(
        {
            "url": f"{TARGET}/api/task_runs/filter",
            "query": {"api_key": "s3cret", "page": 1},
            "json": {"limit": 1},
            "save_response": True,
        }
    )

    metadata_text = Path(json.loads(result.data)["metadata_path"]).read_text()
    assert "s3cret" not in metadata_text
    metadata = json.loads(metadata_text)
    assert metadata["method"] == "POST"
    assert metadata["request_body"] == {"limit": 1}
    assert "page=1" in metadata["url"]


async def test_large_error_response_keeps_status_and_excerpt(store: ResponseStore):
    detail = {"detail": [{"loc": ["body", "task_runs", "end_time"], "msg": "Extra inputs"}] * 200}

    result = await get_tool(store, respond(httpx.Response(422, json=detail))).run({"url": OPENAPI_URL})

    payload = json.loads(result.data)
    assert payload["status"] == 422
    assert "end_time" in payload["excerpt"]
    assert json.loads(Path(payload["saved_to"]).read_text()) == detail


async def test_invalid_json_is_saved_as_text(store: ResponseStore):
    body = "{not json" + "x" * MAX_OUTPUT_CHARS
    response = httpx.Response(200, content=body.encode(), headers={"content-type": "application/json"})

    payload = json.loads((await get_tool(store, respond(response)).run({"url": OPENAPI_URL})).data)

    assert payload["representation"] == "text"
    assert "not valid JSON" in payload["note"]
    assert Path(payload["saved_to"]).read_text() == body


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
