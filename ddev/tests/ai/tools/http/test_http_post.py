# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx
import pytest

from ddev.ai.tools.http.http_post import HttpPostTool
from ddev.ai.tools.http.response_store import ResponseStore

from .helpers import TARGET, respond

FILTER_URL = f"{TARGET}/api/task_runs/filter"


async def test_validation_error_is_preserved_and_not_retried(store: ResponseStore):
    detail = {"detail": [{"loc": ["body", "task_runs", "end_time"], "msg": "Extra inputs are not permitted"}]}
    transport = respond(httpx.Response(422, json=detail))
    tool = HttpPostTool(store, transport=transport)

    result = await tool.run({"url": FILTER_URL, "json": {"task_runs": {"end_time": {}}}})

    assert result.success is True
    assert result.data.startswith("Status: 422")
    assert "end_time" in result.data
    assert len(transport.requests) == 1


@pytest.mark.parametrize("url", ["https://example.com/api", "http://192.168.1.10/api"])
async def test_post_rejects_nonlocal_destination(url: str, store: ResponseStore):
    transport = respond(httpx.Response(200))

    result = await HttpPostTool(store, transport=transport).run({"url": url, "json": {}})

    assert result.success is False
    assert "loopback" in result.error
    assert transport.requests == []


@pytest.mark.parametrize("url", [FILTER_URL, "http://127.0.0.1:9999/api/other", "http://[::1]:4200/api/health"])
async def test_post_allows_any_local_endpoint(url: str, store: ResponseStore):
    transport = respond(httpx.Response(200, json={"ok": True}))

    result = await HttpPostTool(store, transport=transport).run({"url": url, "json": {}})

    assert result.success is True
    assert len(transport.requests) == 1
