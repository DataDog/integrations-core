# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.tools.core.types import ToolResult


class FileLogger:
    """Append-only JSONL writer for ReAct events plus subagent start/finish bookkeeping.

    Owns the file handle. Call build_callbacks() to obtain a Callbacks object whose
    handlers route ReAct events through _emit. Call close() in a finally to release
    the handle. Assumes log_path.parent already exists.
    """

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._fh = log_path.open("a", encoding="utf-8")
        self._closed = False

    @property
    def log_path(self) -> Path:
        return self._log_path

    def _emit(self, event: dict[str, Any]) -> None:
        if self._closed:
            return
        record = {"ts": datetime.now(UTC).isoformat(), **event}
        self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()

    def log_start(self, *, system_prompt: str, prompt: str, tools: list[str]) -> None:
        self._emit({"event": "start", "system_prompt": system_prompt, "prompt": prompt, "tools": tools})

    def log_finish(self, *, success: bool, **fields: Any) -> None:
        self._emit({"event": "finish", "success": success, **fields})

    def close(self) -> None:
        if not self._closed:
            self._fh.close()
            self._closed = True

    def build_callbacks(self) -> Callbacks:
        cb_set = CallbackSet()

        @cb_set.on_before_agent_send
        async def _on_before_send(iteration: int) -> None:
            self._emit({"event": "before_agent_send", "iter": iteration})

        @cb_set.on_agent_response
        async def _on_agent_response(response: AgentResponse, iteration: int) -> None:
            self._emit(
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
                    },
                }
            )

        @cb_set.on_tool_call
        async def _on_tool_call(tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
            self._emit(
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
                }
            )

        @cb_set.on_before_compact
        async def _on_before_compact() -> None:
            self._emit({"event": "before_compact"})

        @cb_set.on_after_compact
        async def _on_after_compact() -> None:
            self._emit({"event": "after_compact"})

        @cb_set.on_error
        async def _on_error(error: BaseException) -> None:
            self._emit({"event": "error", "exception": f"{type(error).__name__}: {error}"})

        return Callbacks([cb_set])
