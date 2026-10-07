# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import json
from collections.abc import AsyncIterator
from io import BufferedWriter
from pathlib import Path
from typing import IO

import httpx
import pytest
from pytest import MonkeyPatch

from ddev.ai.tools.http import base
from ddev.ai.tools.http.http_get import HttpGetTool
from ddev.ai.tools.http.response_store import ResponseStore

from .helpers import TARGET, parse_result, respond, saved_files


@pytest.fixture
def small_limits(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(base, "MAX_BUFFER_BYTES", 8)
    monkeypatch.setattr(base, "MAX_DOWNLOAD_BYTES", 64)
    monkeypatch.setattr(base, "STREAM_CHUNK_BYTES", 3)


@pytest.mark.usefixtures("small_limits")
@pytest.mark.parametrize("size", [7, 8, 9])
async def test_buffer_threshold_preserves_complete_body(tmp_path: Path, size: int):
    body = "x" * size
    transport = respond(httpx.Response(200, text=body))

    result = await HttpGetTool(ResponseStore(tmp_path / "responses"), transport=transport).run({"url": TARGET})

    assert result.success is True
    fields, _ = parse_result(result.data)
    assert Path(fields["saved_to"]).read_text(encoding="utf-8") == body
    assert fields["received_bytes"] == size
    assert len(transport.requests) == 1


@pytest.mark.usefixtures("small_limits")
@pytest.mark.parametrize(
    "body,charset,expected",
    [
        ("12345é\nsecond 🙂".encode(), "utf-8", "12345é\nsecond 🙂"),
        ("12345é\nsecond".encode("latin-1"), "iso-8859-1", "12345é\nsecond"),
        ("12345é\nsecond".encode(), "unknown-charset", "12345é\nsecond"),
        (b"123456789\xc3", "utf-8", "123456789�"),
    ],
)
async def test_spill_retains_prefix_and_decodes_split_characters(
    tmp_path: Path, body: bytes, charset: str, expected: str
):
    transport = respond(httpx.Response(422, content=body, headers={"content-type": f"text/plain; charset={charset}"}))
    result = await HttpGetTool(ResponseStore(tmp_path / "responses"), transport=transport).run({"url": TARGET})

    assert result.success is True
    fields, inline = parse_result(result.data)
    assert inline is None
    assert Path(fields["saved_to"]).read_text(encoding="utf-8") == expected
    assert fields["status"] == 422
    assert fields["lines"] == expected.count("\n") + 1
    metadata = json.loads(Path(fields["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["received_bytes"] == len(body)
    assert metadata["complete"] is True
    assert len(transport.requests) == 1


@pytest.mark.usefixtures("small_limits")
async def test_spilled_json_is_saved_without_parsing_or_formatting(tmp_path: Path):
    body = '{"a":123,"b":456}'
    result = await HttpGetTool(
        ResponseStore(tmp_path / "responses"),
        transport=respond(httpx.Response(200, content=body, headers={"content-type": "application/json"})),
    ).run({"url": TARGET})

    fields, _ = parse_result(result.data)
    assert Path(fields["saved_to"]).read_text(encoding="utf-8") == body
    assert fields["representation"] == "json"
    assert fields["lines"] == 1


@pytest.mark.usefixtures("small_limits")
async def test_download_limit_discards_partial_evidence(tmp_path: Path):
    limit = 64
    store = ResponseStore(tmp_path / "responses")
    transport = respond(httpx.Response(200, text="x" * (limit + 1)))

    result = await HttpGetTool(store, transport=transport).run({"url": TARGET})

    assert result.success is False
    assert f"{limit}-byte download limit" in result.error
    assert saved_files(store.root) == []
    assert len(transport.requests) == 1


@pytest.mark.usefixtures("small_limits")
@pytest.mark.parametrize("interruption", ["cancel", "timeout", "transport"])
async def test_interrupted_spill_removes_partial_files(tmp_path: Path, interruption: str):
    started = asyncio.Event()
    store = ResponseStore(tmp_path / "responses")

    class InterruptedStream(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"prefix-and-tail"
            started.set()
            if interruption == "transport":
                raise httpx.ReadError("stream interrupted")
            await asyncio.Event().wait()

    transport = respond(httpx.Response(200, stream=InterruptedStream(), headers={"content-type": "text/plain"}))
    task = asyncio.create_task(
        HttpGetTool(store, transport=transport).run(
            {"url": TARGET, "timeout": 0.1 if interruption == "timeout" else 10}
        )
    )
    async with asyncio.timeout(5):
        await started.wait()
        if interruption == "cancel":
            assert any(p.suffix == ".txt" for p in saved_files(store.root))
            assert not any(p.name.endswith(".meta.json") for p in saved_files(store.root))
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            result = await task
            assert result.success is False
            assert "timed out" in result.error if interruption == "timeout" else "stream interrupted" in result.error

    assert saved_files(store.root) == []
    assert len(transport.requests) == 1


@pytest.mark.usefixtures("small_limits")
@pytest.mark.parametrize("failure", ["append", "metadata"])
async def test_storage_failure_cleans_spilled_body(tmp_path: Path, monkeypatch: MonkeyPatch, failure: str):
    store = ResponseStore(tmp_path / "responses")
    original_open = Path.open

    class FailingWrite(BufferedWriter):
        def write(self, data: bytes) -> int:
            super().write(data)
            raise OSError("disk full")

    def fail_storage(path: Path, *args: object, **kwargs: object) -> IO[str] | IO[bytes]:
        if failure == "metadata" and path.name.endswith(".meta.json"):
            raise OSError("metadata write failed")
        file = original_open(path, *args, **kwargs)
        if failure == "append" and path.suffix == ".txt":
            return FailingWrite(file.detach())
        return file

    monkeypatch.setattr(Path, "open", fail_storage)
    transport = respond(httpx.Response(200, text="prefix-and-tail"))

    result = await HttpGetTool(store, transport=transport).run({"url": TARGET})

    assert result.success is False
    assert "disk full" in result.error if failure == "append" else "metadata" in result.error
    assert saved_files(store.root) == []
    assert len(transport.requests) == 1
