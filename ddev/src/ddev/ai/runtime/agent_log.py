# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from ddev.ai.agent.exceptions import describe_agent_error
from ddev.ai.react import notices

if TYPE_CHECKING:
    from ddev.ai.agent.scope import AgentScope
    from ddev.ai.run_events import RunEvents


class AgentLogger:
    """Run-wide observer that writes one append-only JSONL per agent.

    A single instance serves the whole run: every agent notice carries an
    ``AgentScope``, and this logger demultiplexes by ``scope`` to
    ``<root>/<role>/<owner_id>.jsonl``. File handles are opened lazily and closed
    once via ``close()`` at the end of the run.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._files: dict[AgentScope, TextIO] = {}
        self._closed = False

    def _sink(self, scope: AgentScope) -> TextIO:
        fh = self._files.get(scope)
        if fh is None:
            path = self._root / scope.role.value / f"{scope.owner_id}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            fh = self._files[scope] = path.open("a", encoding="utf-8")
        return fh

    def _emit(self, scope: AgentScope, record: dict[str, Any]) -> None:
        if self._closed:
            return
        fh = self._sink(scope)
        fh.write(json.dumps({"ts": datetime.now(UTC).isoformat(), **record}, default=str) + "\n")
        fh.flush()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for fh in self._files.values():
            fh.close()
        self._files.clear()

    def subscribe(self, events: RunEvents) -> None:
        events.subscribe(notices.AgentStarted, self._on_agent_start)
        events.subscribe(notices.AgentBeforeSend, self._on_before_agent_send)
        events.subscribe(notices.AgentResponded, self._on_agent_response)
        events.subscribe(notices.ToolCalled, self._on_tool_call)
        events.subscribe(notices.BeforeCompact, self._on_before_compact)
        events.subscribe(notices.AfterCompact, self._on_after_compact)
        events.subscribe(notices.ContextCleared, self._on_context_cleared)
        events.subscribe(notices.AgentFinished, self._on_agent_finish)
        events.subscribe(notices.AgentErrored, self._on_agent_error)

    async def _on_agent_start(self, notice: notices.AgentStarted) -> None:
        self._emit(notice.scope, {"event": "start", "system_prompt": notice.system_prompt, "tools": notice.tools})

    async def _on_before_agent_send(self, notice: notices.AgentBeforeSend) -> None:
        self._emit(notice.scope, {"event": "before_agent_send", "iter": notice.iteration, "prompt": notice.prompt})

    async def _on_agent_response(self, notice: notices.AgentResponded) -> None:
        response = notice.response
        self._emit(
            notice.scope,
            {
                "event": "agent_response",
                "iter": notice.iteration,
                "text": response.text,
                "tool_calls": [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in response.tool_calls],
                "stop_reason": str(response.stop_reason),
                "tokens": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                    "cache_read": response.usage.cache_read_input_tokens,
                    "cache_creation": response.usage.cache_creation_input_tokens,
                    "web_search_requests": response.usage.web_search_requests,
                    "web_fetch_requests": response.usage.web_fetch_requests,
                },
                "web_searches": [
                    {"query": ws.query, "result_count": ws.result_count, "error": ws.error}
                    for ws in response.web_activity.searches
                ],
                "web_fetches": [
                    {"url": wf.url, "retrieved_at": wf.retrieved_at, "error": wf.error}
                    for wf in response.web_activity.fetches
                ],
                "web_citations": [
                    {"url": c.url, "title": c.title, "cited_text": c.cited_text}
                    for c in response.web_activity.citations
                ],
            },
        )

    async def _on_tool_call(self, notice: notices.ToolCalled) -> None:
        result = notice.result
        tool_call = notice.tool_call
        self._emit(
            notice.scope,
            {
                "event": "tool_call",
                "iter": notice.iteration,
                "tool_call_id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.input,
                "result": {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "truncated": result.truncated,
                },
            },
        )

    async def _on_before_compact(self, notice: notices.BeforeCompact) -> None:
        self._emit(notice.scope, {"event": "before_compact"})

    async def _on_after_compact(self, notice: notices.AfterCompact) -> None:
        self._emit(notice.scope, {"event": "after_compact"})

    async def _on_context_cleared(self, notice: notices.ContextCleared) -> None:
        self._emit(notice.scope, {"event": "context_cleared"})

    async def _on_agent_finish(self, notice: notices.AgentFinished) -> None:
        result = notice.result
        self._emit(
            notice.scope,
            {
                "event": "finish",
                "success": True,
                "iterations": result.iterations,
                "total_input_tokens": result.total_input_tokens,
                "total_output_tokens": result.total_output_tokens,
                "stop_reason": str(result.final_response.stop_reason),
            },
        )

    async def _on_agent_error(self, notice: notices.AgentErrored) -> None:
        detail = describe_agent_error(notice.error)
        self._emit(notice.scope, {"event": "error", "exception": detail})
        self._emit(notice.scope, {"event": "finish", "success": False, "error": detail})
