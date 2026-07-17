# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from ddev.ai.agent.exceptions import describe_agent_error
from ddev.ai.callbacks.callbacks import CallbackSet

if TYPE_CHECKING:
    from ddev.ai.agent.scope import AgentScope
    from ddev.ai.agent.types import AgentResponse, ToolCall
    from ddev.ai.react.types import ReActResult
    from ddev.ai.tools.core.types import ToolResult


class AgentLogger:
    """Run-wide observer that writes one append-only JSONL per agent.

    A single instance serves the whole run: every agent-tier callback carries an
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

    def as_callback_set(self) -> CallbackSet:
        cb = CallbackSet()

        @cb.on_agent_start
        async def _on_agent_start(scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
            self._emit(scope, {"event": "start", "system_prompt": system_prompt, "tools": tools})

        @cb.on_before_agent_send
        async def _on_before_agent_send(scope: AgentScope, prompt: str, iteration: int) -> None:
            self._emit(scope, {"event": "before_agent_send", "iter": iteration, "prompt": prompt})

        @cb.on_agent_response
        async def _on_agent_response(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
            self._emit(
                scope,
                {
                    "event": "agent_response",
                    "iter": iteration,
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

        @cb.on_tool_call
        async def _on_tool_call(scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
            self._emit(
                scope,
                {
                    "event": "tool_call",
                    "iter": iteration,
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

        @cb.on_before_compact
        async def _on_before_compact(scope: AgentScope) -> None:
            self._emit(scope, {"event": "before_compact"})

        @cb.on_after_compact
        async def _on_after_compact(scope: AgentScope) -> None:
            self._emit(scope, {"event": "after_compact"})

        @cb.on_context_cleared
        async def _on_context_cleared(scope: AgentScope) -> None:
            self._emit(scope, {"event": "context_cleared"})

        @cb.on_agent_finish
        async def _on_agent_finish(scope: AgentScope, result: ReActResult) -> None:
            self._emit(
                scope,
                {
                    "event": "finish",
                    "success": True,
                    "iterations": result.iterations,
                    "total_input_tokens": result.total_input_tokens,
                    "total_output_tokens": result.total_output_tokens,
                    "stop_reason": str(result.final_response.stop_reason),
                },
            )

        @cb.on_agent_error
        async def _on_agent_error(scope: AgentScope, error: BaseException) -> None:
            detail = describe_agent_error(error)
            self._emit(scope, {"event": "error", "exception": detail})
            self._emit(scope, {"event": "finish", "success": False, "error": detail})

        return cb
